"""在独立数据目录启动真实服务，验证 Windows 启动器与监听进程的生命周期。"""

import json
import os
import shutil
import socket
import subprocess

import httpx
import pytest

from app.config import PROJECT_ROOT

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows 服务脚本")


def test_windows_start_identity_stop_and_legacy_launcher(tmp_path):
    powershell = shutil.which("powershell.exe")
    if not powershell or not (PROJECT_ROOT / "frontend/dist/index.html").exists():
        pytest.skip("需要 Windows PowerShell 和已构建的前端")
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        port = reserved.getsockname()[1]
    root = tmp_path / "trunk"
    root.mkdir()
    environment = {
        **os.environ,
        "TRUNK_AGENT_DATA_DIR": str(tmp_path / "data"),
        "TRUNK_AGENT_WORKSPACE": str(root),
    }
    record_path = tmp_path / "data/server.process.json"
    address = f"http://127.0.0.1:{port}/api/health"
    record = None

    def script(name, *arguments, check=True):
        # Windows 后台子进程可能继承捕获管道，脚本退出后 communicate 仍等不到 EOF。
        with (tmp_path / "script-output.log").open("ab") as output:
            return subprocess.run(
                [
                    powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(PROJECT_ROOT / name),
                    *arguments,
                ],
                env=environment,
                stdout=output,
                stderr=subprocess.STDOUT,
                check=check,
                timeout=60,
            )

    def stopped():
        listening = subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-Command",
                f"@(Get-NetTCPConnection -LocalPort {port} -State Listen "
                "-ErrorAction SilentlyContinue).Count",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=20,
        )
        assert listening.stdout.strip() == "0"
        # 本机网络过滤可能将拒绝连接表现为连接超时，监听表必须首先证明端口已释放。
        with pytest.raises((httpx.ConnectError, httpx.ConnectTimeout)):
            httpx.get(address, timeout=2, trust_env=False)
        assert not record_path.exists()

    try:
        script("Start.ps1", "-Port", str(port), "-NoBrowser")
        health = httpx.get(address, trust_env=False).json()
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        assert record["process_id"] == health["process_id"]
        assert health["data_directory"] == str(tmp_path / "data")
        # 重复启动沿用同一个实际服务，PID 创建时间错误时拒绝关闭它。
        script("Start.ps1", "-Port", str(port), "-NoBrowser")
        assert httpx.get(address, trust_env=False).json()["process_id"] == record["process_id"]
        environment["TRUNK_AGENT_DATA_DIR"] = str(tmp_path / "other-data")
        assert script("Start.ps1", "-Port", str(port), "-NoBrowser", check=False).returncode != 0
        environment["TRUNK_AGENT_DATA_DIR"] = str(tmp_path / "data")
        assert httpx.get(address, trust_env=False).json()["process_id"] == record["process_id"]
        record_path.write_text(json.dumps({**record, "created_ticks": "0"}), encoding="utf-8")
        assert script("Stop.ps1", check=False).returncode != 0
        assert httpx.get(address, trust_env=False).json()["ok"]
        record_path.write_text(json.dumps(record), encoding="utf-8")
        script("Stop.ps1")
        stopped()

        script("Start.ps1", "-Port", str(port), "-NoBrowser")
        record = json.loads(record_path.read_text(encoding="utf-8-sig"))
        # 用旧版格式记录启动器，Stop 必须同时关闭它的 Python 子进程。
        parent_query = (
            f'(Get-CimInstance Win32_Process -Filter "ProcessId={record["process_id"]}")'
            ".ParentProcessId"
        )
        query = subprocess.run(
            [powershell, "-NoProfile", "-Command", parent_query],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        launcher_id = int(query.stdout.strip())
        (record_path.parent / "server.pid").write_text(str(launcher_id), encoding="ascii")
        record_path.unlink()
        script("Stop.ps1")
        stopped()
    finally:
        environment["TRUNK_AGENT_DATA_DIR"] = str(tmp_path / "data")
        if record_path.exists() and record:
            record_path.write_text(json.dumps(record), encoding="utf-8")
        if record_path.exists() or (record_path.parent / "server.pid").exists():
            # 验证失败也只清理本测试独立目录的已记录服务。
            script("Stop.ps1", check=False)
