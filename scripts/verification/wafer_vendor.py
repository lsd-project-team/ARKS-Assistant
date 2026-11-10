"""显式真实模型验收：模拟晶圆厂商文档驱动兼容适配，只写隔离副本。"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from app.core.config import Paths, SettingsStore  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.code_work.environment import CodeEnvironment  # noqa: E402
from app.modules.code_work.files import code_manifest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from tests.helpers.accounts import sign_in  # noqa: E402

from scripts.verification.code_work_loop import events, poll, save  # noqa: E402

QUESTIONS = {
    "clarify": "现在要换一个晶圆厂商，为了适配新的厂商请帮我修改现有代码。",
    "adapt": (
        "这次先适配新厂商的晶圆 Map 文件格式，其他通信和设备流程保持现状。"
        "新厂商规范和样例已经上传，请先读取文档，检查原工程现有导入入口，"
        "实际完成文档要求的代码适配并保留旧格式兼容。"
        "请在独立副本中修改、编写覆盖正常和非法输入的需求断言，运行编译、仿真及需求验证。"
        "不能只新增未接入的转换器；请展示实际改动和验证结果，等待我审核。"
    ),
    "adapt-feedback": (
        "继续在当前独立副本完成适配。已上传修正版模拟规范 v2：原规范输出 Flat_Notch=Down "
        "不符合真实 AKRS 库，库的枚举是 Top/Right/Bottom/Left/Unknown，本版输出应为 Bottom，"
        "输入 NOTCH=DOWN 不变。请读取新文档并实际修正代码及验收。"
        "独立检查发现：1. 合法记录 ' 1 , 1 , 0 ' 因字段未正确去空白而报错；"
        "2. LoadMap 把旧格式 PrepareForLoad 返回的源路径赋给 filePath，"
        "随后 File.Copy(source,source) "
        "导致旧格式导入失败，必须保留正确的目标路径；3. 新复合后缀 <载具名称>.svb.csv "
        "仍未按载具名找到，不能只插入转换调用。请真实覆盖导入入口的查找和复制，"
        "最后的 UI 打开动作可以拦截，避免依赖真实设备。"
        "同时修正你写错的 2x3 测试：输入 3,1,9 / 1,2,0 / 2,1,255，"
        "正确两行是 1.. 和 ..2，你上轮说明中的 .2. 仍然不对。"
        "这不是削弱预期；保留所有旧报告、正常和非法输入检查，新增上述反例，"
        "在新轮次重新编译和验证，不能仅回复方案或自称业务代码正确。"
    ),
    "adapt-test-fix": (
        "当前业务副本已通过独立 C# 程序 69 项检查：实际执行 Block.LoadMap 的文件查找与复制，"
        "仅拦截最后 UI 打开动作，并用真实 WaferMap 库读取新结果；全部通过。"
        "本轮不要再修改业务代码，只修订现有两个错误测试并重新验证。"
        "先 inspect_work_changes 读取原用例 id/version，使用原 id/version 更新，不能新建重复用例。"
        "原 v1 用例：按 v2 将 Down 期望改为 Bottom；"
        "2x3 样例两行应为 1.. 与 ..2，其余有效测试保留。"
        "v2 用例：保留已执行的前 40 项有效断言，"
        "去掉 File.ReadAllLines 依赖错误相对源码路径的部分，改为反射已编译业务方法的检查，"
        "不要再做源文件字符串检查。真实导入行为已由前述独立 69 项覆盖。"
        "这是人工审查后明确纠正测试错误，不能改变业务预期、删除其他有效检查或改历史报告。"
        "修订后实际重跑编译、Simulation 和需求检查，展示准确结果。"
    ),
}


def verify(args):
    if not args.live:
        raise ValueError("本验收调用当前真实模型，必须显式指定 --live")
    output = args.output.resolve()
    if not output.is_relative_to(ROOT / "output"):
        raise ValueError("验收数据必须在项目 output 内")
    output.mkdir(parents=True, exist_ok=True)
    identity_path = output / "identity.json"
    identity = (
        json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.exists() else {}
    )
    if args.case in identity and not args.resume:
        raise ValueError("此阶段已有运行，保留证据，不自动重跑")
    if args.resume and args.case not in identity:
        raise ValueError("没有可继续的阶段")
    if not 10_000 <= args.token_budget <= 20_000_000:
        raise ValueError("隔离项目额度须为 10000～20000000")
    if args.case == "adapt" and (not identity.get("clarify") or not args.spec and not args.resume):
        raise ValueError("需先完成缺资料阶段，并提供本地模拟规范 --spec")
    config = SettingsStore(Paths()).load()
    profile = next(item for item in config.model_profiles if item.id == args.profile_id)
    config = config.model_copy(
        update={
            "active_profile_id": profile.id,
            "model": profile.config,
            "mcp_servers": [],
            "deepwiki_repo": "",
        },
        deep=True,
    )
    environment = CodeEnvironment(ROOT / "data").load()
    source = Path(environment.source_root)
    original = code_manifest(source)
    app = create_app(Paths(output / "data", ROOT / "trunk"))
    # 凭据仅在内存装配，隔离配置与报告不保存正式供应商密钥。
    app.state.projects.base.settings.load = lambda: config.model_copy(deep=True)
    with TestClient(app) as client:
        sign_in(client)
        current = client.get("/api/settings/code-work").json()
        client.put(
            "/api/settings/code-work",
            json={
                "source_root": str(source),
                "msbuild": environment.msbuild,
                "timeout_seconds": 600,
                "version": current["version"],
            },
        ).raise_for_status()
        sign_in(client, "user")
        project = client.get("/api/projects").json()["default_project_id"]
        assert not identity or identity["project_id"] == project
        app.state.projects.services(project).runtime.model_ledger.save(
            {"token_limit": args.token_budget}
        )
        base = f"/api/p/{project}"
        attachments = []
        if args.resume:
            attachments = json.loads(
                (output / args.case / "input.json").read_text(encoding="utf-8")
            )["attachments"]
        elif args.spec:
            response = client.post(
                base + "/attachments",
                params={"filename": args.spec.name},
                content=args.spec.read_bytes(),
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()
            attachments.append(response.json())
        body = {
            "content": QUESTIONS[args.case],
            "profile_id": profile.id,
            "attachment_ids": [item["id"] for item in attachments],
            "source_options": {"use_knowledge": False, "use_memory": False, "use_deepwiki": False},
        }
        if args.case == "adapt-test-fix":
            response = client.get(base + f"/threads/{identity['thread_id']}/code-work")
            response.raise_for_status()
            cases = [
                {key: case[key] for key in ("id", "version", "name")}
                for case in response.json().get("requirements", [])
            ]
            body["content"] += "\n当前用例的实际标识与版本：" + json.dumps(
                cases, ensure_ascii=False
            )
        endpoint = base + (
            f"/threads/{identity['thread_id']}/runs" if identity else "/threads/start"
        )
        if args.resume:
            previous_id = identity.get("latest_run_id", identity[args.case])
            response = client.post(base + f"/runs/{previous_id}/resume")
        else:
            response = client.post(endpoint, json=body)
        response.raise_for_status()
        run = response.json()
        identity.update(project_id=project, thread_id=run["thread_id"], model=profile.config.model)
        phase_name = args.case
        if args.resume:
            attempt = 1 + sum(key.startswith(args.case + "-resume-") for key in identity)
            phase_name = f"{args.case}-resume-{attempt}"
        identity[phase_name] = run["id"]
        identity["latest_run_id"] = run["id"]
        save(output, "identity.json", identity)
        phase = output / phase_name
        phase.mkdir()
        save(phase, "input.json", {"content": body["content"], "attachments": attachments})
        prefix = base + f"/threads/{run['thread_id']}/code-work"
        print(f"{args.case}: {profile.config.model}; run={run['id']}", flush=True)
        result = poll(client, base + f"/runs/{run['id']}", phase, phase="chat", prefix=prefix)
        trace = events(client, base, run["id"])
        chain_trace = list(trace)
        if args.resume:
            for name, previous_id in identity.items():
                if (
                    name == args.case or name.startswith(args.case + "-resume-")
                ) and previous_id != run["id"]:
                    chain_trace.extend(events(client, base, previous_id))
        state = client.get(prefix).json()
        conversation = client.get(base + f"/threads/{run['thread_id']}").json()
        save(phase, "run.json", result)
        save(phase, "events.json", trace)
        save(phase, "status.json", state)
        save(phase, "conversation.json", conversation)
        changes = []
        for file in state.get("files", []):
            response = client.get(prefix + "/diff", params={"path": file["path"]})
            response.raise_for_status()
            changes.append(response.json())
        save(phase, "diffs.json", changes)
        tools = Counter(
            event["payload"]["name"] for event in trace if event["kind"] == "tool_start"
        )
        report = {
            "case": args.case,
            "run_status": result["status"],
            "real_model": profile.config.model,
            "original_unchanged": code_manifest(source) == original,
            "changed_files": [item["path"] for item in state.get("files", [])],
            "tools": dict(tools),
            "model_calls": sum(event["kind"] == "provider_usage" for event in trace),
            "verification": (state.get("verification") or {}).get("status"),
            "verification_current": state.get("verification_current", False),
            "document_ids_read": [
                event["payload"]["id"]
                for event in chain_trace
                if event["kind"] == "attachment_read"
            ],
        }
        save(phase, "result.json", report)
        print(json.dumps(report, ensure_ascii=False), flush=True)
        assert report["original_unchanged"], "原工程发生变化"
        assert result["status"] == "completed", result.get("error")
        if args.case == "clarify":
            assert not changes, "缺少厂商规范时不应擅自改业务代码"
        else:
            assert changes, "提供文档后没有实际改码"
            assert {item["id"] for item in attachments}.issubset(report["document_ids_read"])
            assert report["verification_current"] and report["verification"] == "passed"
            assert state.get("requirements"), "没有为新需求保存断言"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--case", choices=QUESTIONS, required=True)
    parser.add_argument("--profile-id", default="default")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--token-budget", type=int, default=2_000_000)
    parser.add_argument("--spec", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args())
