"""显式真实模型验收：开阀反例、修改、桌面仿真、候选验证、隔离合并和回退。"""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.config import Paths, SettingsStore  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.code_work.environment import CodeEnvironment  # noqa: E402
from app.modules.code_work.files import code_manifest, snapshot  # noqa: E402
from tests.helpers.accounts import sign_in  # noqa: E402

FILE = "AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs"
QUESTION = """/修改代码
请在当前对话的独立工程副本中，修改点胶系统 DispenseController.OpenDispensingElectric：
点胶阀已经开启时直接返回；只有关闭时才调用底层开阀方法。保留方法签名、关闭操作和状态读取功能。
请实际完成以下流程：
1. 先添加需求断言，用 CountCalls 统计真实 DispenseModule.OpenDispensingElectric 的调用次数，
确认原实现连续打开两次会下发两次。
2. 修改业务代码后重新验证：先关闭，再连续打开两次，底层只调用一次，最终状态为开启；
随后关闭，状态应恢复为关闭。
3. 启用原桌面界面流程，运行编译、虚拟驱动检查、原工程自检、需求断言及七步界面验证，
保存日志和截图。
4. 展示实际修改、当前版本验证结果和副本路径，将修改保留在副本中，等待我审核合并。"""


def save(folder, name, data):
    (folder / name).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def poll(client, endpoint, folder, *, phase, prefix=None):
    deadline, previous = time.monotonic() + 1200, None
    while time.monotonic() < deadline:
        response = client.get(endpoint)
        response.raise_for_status()
        value = response.json()
        job = value.get("verification") if phase == "merge" else None
        current = (job or {}).get("status") if phase == "merge" else value["status"]
        if current != previous:
            print(f"{phase}: {current}", flush=True)
            previous = current
        if prefix and phase == "chat":
            status = client.get(prefix).json()
            active = status.get("verification") or {}
            save(
                folder,
                "progress.json",
                {
                    "run_status": current,
                    "revision": status.get("revision"),
                    "verification": active.get("status"),
                    "step": active.get("steps", [])[-1:],
                },
            )
        if current in {"completed", "failed", "cancelled", "interrupted", "passed"}:
            return value
        time.sleep(1)
    raise TimeoutError("验收未在1200秒内结束，不启动重复运行")


def events(client, base, run_id):
    response = client.get(f"{base}/runs/{run_id}/trace")
    response.raise_for_status()
    return response.json()


def verify(args):
    if not args.live:
        raise ValueError("此脚本调用真实供应商，必须显式使用 --live")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "data/app.sqlite3").exists() and not args.resume:
        raise ValueError("已有验收数据库，保留证据，请为新运行选择新目录")
    if (output / "result.json").exists():
        raise ValueError("验收已完成，保留已有证据")
    configuration = SettingsStore(Paths()).load()
    profile = next(item for item in configuration.model_profiles if item.id == args.profile_id)
    configuration = configuration.model_copy(
        update={
            "active_profile_id": profile.id,
            "model": profile.config,
            "mcp_servers": [],
            "deepwiki_repo": "",
        },
        deep=True,
    )
    source = args.source_root.resolve()
    original_code = code_manifest(source)
    environment = CodeEnvironment(ROOT / "data").load()
    target = output / "test-origin"
    if not args.resume:
        target.mkdir()
        print("snapshot: preparing isolated merge target", flush=True)
        snapshot(source, target)
    assert code_manifest(target) == original_code
    paths = Paths(output / "data", ROOT / "trunk")
    app = create_app(paths)
    # 正式供应商凭据仅在内存装配，不写隔离配置、报告或调用日志。
    app.state.projects.base.settings.load = lambda: configuration.model_copy(deep=True)
    report = {"real_model": True, "profile_name": profile.name, "model": profile.config.model}
    with TestClient(app) as client:
        sign_in(client)
        current = client.get("/api/settings/code-work").json()
        client.put(
            "/api/settings/code-work",
            json={
                "source_root": str(target),
                "msbuild": environment.msbuild,
                "timeout_seconds": 600,
                "version": current["version"],
            },
        ).raise_for_status()
        sign_in(client, "user")
        project = client.get("/api/projects").json()["default_project_id"]
        # 只调整隔离测试项目的有限额度，不改正式配置、不清零已有用量。
        ledger = app.state.projects.services(project).runtime.model_ledger
        ledger.save({"token_limit": args.token_budget})
        base = f"/api/p/{project}"
        if args.resume:
            previous = json.loads((output / "identity.json").read_text(encoding="utf-8"))
            assert previous["project_id"] == project
            run = client.get(base + f"/runs/{previous['run_id']}").json()
        else:
            response = client.post(
                base + "/threads/start",
                json={
                    "content": QUESTION,
                    "profile_id": profile.id,
                    "source_options": {
                        "use_knowledge": False,
                        "use_memory": False,
                        "use_deepwiki": False,
                    },
                },
            )
            response.raise_for_status()
            run = response.json()
        prefix = base + f"/threads/{run['thread_id']}/code-work"
        report.update(project_id=project, thread_id=run["thread_id"], run_id=run["id"])
        save(output, "identity.json", report)
        result = poll(client, base + f"/runs/{run['id']}", output, phase="chat", prefix=prefix)
        state = client.get(prefix).json()
        history = events(client, base, run["id"])
        save(output, "run.json", result)
        save(output, "events.json", history)
        save(output, "status.json", state)
        assert result["status"] == "completed", result.get("error")
        assert state["verification_current"] and state["verification"]["status"] == "passed"
        assert [item["path"] for item in state["files"]] == [FILE]
        job = state["verification"]
        assert sum(item["assertions"] for item in job["requirements_results"]) >= 3
        assert len(job["desktop_results"]) == 7
        assert all(item["status"] == "passed" for item in job["desktop_results"])
        assert any("CountCalls" in item["code"] for item in state["requirements"])
        failed = [item for item in state["verification_history"] if item["status"] == "failed"]
        assert failed, "没有先检出原实现的需求反例"
        negative = client.get(prefix + "/report", params={"job_id": failed[0]["id"]}).json()
        save(output, "negative.json", negative)
        assert negative["steps"][-1]["name"] == "本次需求断言验证"
        starts = [item["payload"] for item in history if item["kind"] == "tool_start"]
        report["tools"] = dict(Counter(item["name"] for item in starts))
        report["model_calls"] = sum(item["kind"] == "provider_usage" for item in history)
        assert report["tools"].get("edit_work_file", 0) + report["tools"].get("write_work_file", 0)
        difference = client.get(prefix + "/diff", params={"path": FILE}).json()
        save(output, "diff.json", difference)
        turn = client.get(prefix + "/summary", params={"run_id": run["id"]}).json()
        original = (target / FILE).read_bytes()
        assert code_manifest(source) == original_code
        plan_response = client.post(prefix + "/merge/preview", json={"paths": [FILE]})
        plan_response.raise_for_status()
        plan = plan_response.json()
        merge = prefix + f"/merge/{plan['id']}"
        assert (
            client.post(merge + "/apply", json={"confirm_target": plan["target"]}).status_code
            == 403
        )
        client.post(merge + "/verify").raise_for_status()
        verified = poll(client, merge, output, phase="merge")
        save(output, "merge.json", verified)
        assert verified["can_apply"], verified
        sign_in(client)
        wrong = client.post(merge + "/apply", json={"confirm_target": "wrong-target"})
        assert wrong.status_code == 409
        client.post(merge + "/apply", json={"confirm_target": plan["target"]}).raise_for_status()
        assert not client.get(prefix).json()["files"]
        assert (target / FILE).read_bytes() != original
        assert client.get(prefix + "/summary", params={"run_id": run["id"]}).json() == turn
        client.post(merge + "/rollback", json={"confirm_target": plan["target"]}).raise_for_status()
        assert (target / FILE).read_bytes() == original
        image = client.get(
            prefix + "/report",
            params={
                "job_id": job["id"],
                "name": job["desktop_results"][5]["screenshot"],
            },
        )
        image.raise_for_status()
        (output / "actual-desktop.png").write_bytes(image.content)
        assert code_manifest(source) == original_code
        report.update(
            passed=True,
            verification=job,
            merge_verification=verified["verification"],
            original_unchanged=True,
            apply_rollback=True,
            immutable_history=True,
            target=str(target),
            diff_version=difference["version"],
        )
        save(output, "result.json", report)
        print(
            "PASS: real provider, negative test, edit, desktop, verified merge and rollback",
            flush=True,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--resume", action="store_true", help="只收集已有运行并继续验收，不创建模型重跑"
    )
    parser.add_argument("--profile-id", default="default")
    parser.add_argument("--token-budget", type=int, default=2_000_000)
    parser.add_argument(
        "--source-root", type=Path, default=Path("C:/Users/w/Desktop/AKRS.ZX2200/trunk")
    )
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args())
