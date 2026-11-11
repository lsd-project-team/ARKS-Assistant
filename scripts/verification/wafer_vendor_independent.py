"""对文档驱动生成的 Simulation 结果运行独立 C# 反例，不改模型测试和业务源码。"""

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify(directory, allow_failed, output_name):
    directory = directory.resolve()
    if not directory.is_relative_to(ROOT / "output"):
        raise ValueError("只验收 output 下的隔离结果")
    identity = json.loads((directory / "identity.json").read_text(encoding="utf-8"))
    phase = next(
        name
        for name, run in identity.items()
        if name.startswith("adapt") and run == identity["latest_run_id"]
    )
    status = json.loads((directory / phase / "status.json").read_text(encoding="utf-8"))
    job = status.get("verification") or {}
    if not status.get("verification_current") or (
        job.get("status") != "passed" and not allow_failed
    ):
        raise ValueError("先完成当前副本编译验证，再运行独立反例")
    work = Path(status["workspace_path"]).parent.resolve()
    assert work.is_relative_to(directory)
    binary = work / "checks" / job["id"][:10] / "Simulation" / "AKRS.ZX2200.exe"
    original = (
        Path(status["source_path"])
        / "AKRS.ZX2200/WaferSubSystem/WaferMapFiles/Updates/2024-03-12/test1Map.AKRS"
    )
    assert binary.is_file() and original.is_file()
    config = json.loads((directory / "data/code-work.local.json").read_text(encoding="utf-8"))
    compiler = Path(config["msbuild"]).parent / "Roslyn/csc.exe"
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", output_name):
        raise ValueError("独立结果目录名称不合法")
    out = directory / output_name
    if out.exists():
        raise ValueError("已有独立验收结果，保留证据，不覆盖")
    out.mkdir()
    executable = out / "WaferVendorChecks.exe"
    compiled = subprocess.run(
        [
            str(compiler),
            "/nologo",
            "/target:exe",
            f"/reference:{binary.parent / '0Harmony.dll'}",
            f"/out:{executable}",
            str(ROOT / "backend/tests/fixtures/wafer_vendor_checks.cs"),
        ],
        capture_output=True,
        timeout=60,
    )
    (out / "compile.log").write_bytes(compiled.stdout + compiled.stderr)
    if compiled.returncode:
        raise ValueError("独立验收程序编译失败，见 compile.log")
    shutil.copyfile(binary.with_suffix(".exe.config"), executable.with_suffix(".exe.config"))
    result = subprocess.run(
        [str(executable), str(binary), str(out / "samples"), str(original)],
        capture_output=True,
        cwd=binary.parent,
        timeout=120,
    )
    log = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    (out / "run.log").write_text(log, encoding="utf-8")
    count = re.search(r"RESULT: assertions=(\d+); passed=(true|false)", log)
    report = {
        "passed": result.returncode == 0,
        "exit_code": result.returncode,
        "assertions": int(count[1]) if count else 0,
        "simulation": str(binary),
        "test_source": "backend/tests/fixtures/wafer_vendor_checks.cs",
    }
    (out / "result.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(log)
    print(json.dumps(report, ensure_ascii=False))
    assert report["passed"], "独立反例未通过，不能将模型自报通过作为最终结论"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--allow-failed-checks", action="store_true")
    parser.add_argument("--output-name", default="independent")
    args = parser.parse_args()
    verify(args.directory, args.allow_failed_checks, args.output_name)
