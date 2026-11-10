"""独立数据中的代码工作端到端验收；显式选择真实模型，凭据只留内存。"""

import argparse
import json
import re
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.storage.files import digest  # noqa: E402
from app.main import create_app  # noqa: E402
from tests.helpers.accounts import sign_in  # noqa: E402
from tests.helpers.models import DeterministicModel  # noqa: E402

FILE = "AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs"
QUESTION = (
    f"/修改代码 在独立副本文件 {FILE} 中，"
    "将类 DispenseController 的 OpenDispensingElectric 改为幂等："
    "只有原点胶阀未开启时才调用开阀。只修改这个方法，保留关闭、读取与其他业务逻辑。"
    "先 prepare_code_workspace，使用副本工具读取820–855行；"
    "完成实际修改后运行 verify_code_workspace 编译和现有仿真验证，并报告结果。"
)


class EditingModel(DeterministicModel):
    """确定性协议验收模型，不作为供应商能力证据。"""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = [message for message in messages if isinstance(message, ToolMessage)]
        last = tools[-1] if tools else None
        arguments = {}
        if last is None:
            name = "prepare_code_workspace"
        elif last.name == "prepare_code_workspace":
            name = "read_work_file"
            arguments = {"path": FILE, "start_line": 820, "end_line": 855}
        elif last.name == "read_work_file":
            data = json.loads(last.content)
            content = "\n".join(re.sub(r"^\d+: ", "", row) for row in data["content"].splitlines())
            match = re.search(
                r"public void OpenDispensingElectric\(\)\s*\{\s*"
                r"this.DispenseModule.OpenDispensingElectric\(\);\s*\}",
                content,
            )
            if not match:
                raise AssertionError("未找到本次验收指定方法，不能假造编辑成功")
            name = "edit_work_file"
            arguments = {
                "path": FILE,
                "version": data["version"],
                "old_text": match[0],
                "new_text": (
                    "public void OpenDispensingElectric()\n        {\n"
                    "            if (!this.DispenseModule.IsDispensingElectricOpen())\n"
                    "            {\n                this.DispenseModule.OpenDispensingElectric();\n"
                    "            }\n        }"
                ),
            }
        elif last.name == "edit_work_file":
            name = "verify_code_workspace"
        else:
            result = json.loads(last.content)
            assert result["verification"]["status"] == "passed", result
            return ChatResult(
                generations=[
                    ChatGeneration(
                        message=AIMessage(
                            content="已在独立副本为开阀方法增加幂等检查，编译与仿真通过。原件未修改。"
                        )
                    )
                ]
            )
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "id": f"verify-work-{len(tools)}",
                                "name": name,
                                "args": arguments,
                            }
                        ],
                    )
                )
            ]
        )


def verify(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = Paths(output / "data", args.source_root.resolve())
    app = create_app(paths)
    configuration = SettingsStore(Paths()).load() if args.real_model else None
    if configuration:
        # 禁止把正式密钥复制到临时设置文件或报告。
        app.state.projects.base.settings.load = lambda: configuration.model_copy(
            update={"mcp_servers": [], "deepwiki_repo": ""}, deep=True
        )
    model = EditingModel()
    context = (
        patch("app.agents.runtime.graph_builder.create_model", lambda *a, **kw: model)
        if not args.real_model
        else nullcontext()
    )
    original = (args.source_root / FILE).read_bytes()
    report = {"real_model": args.real_model, "original_version": digest(original)}
    with context, TestClient(app) as client:
        sign_in(client)
        environment = client.get("/api/settings/code-work").json()
        response = client.put(
            "/api/settings/code-work",
            json={
                "source_root": str(args.source_root.resolve()),
                "msbuild": str(args.msbuild.resolve()),
                "version": environment["version"],
                "timeout_seconds": 600,
            },
        )
        assert response.status_code == 200, response.text
        # 执行真实用户流程；管理员仅配置本机编译环境。
        sign_in(client, "user")
        project = client.get("/api/projects").json()["default_project_id"]
        base = f"/api/p/{project}"
        endpoint = base + "/threads/start"
        if args.resume:
            identity = json.loads((output / "identity.json").read_text(encoding="utf-8"))
            assert identity["project_id"] == project, "只能复用当前独立测试账号的对话"
            prefix = base + f"/threads/{identity['thread_id']}/code-work"
            state = client.get(prefix).json()
            for file in state["files"]:
                reverted = client.post(
                    prefix + "/revert", json={"path": file["path"], "version": file["version"]}
                )
                assert reverted.status_code == 200
            endpoint = base + f"/threads/{identity['thread_id']}/runs"
        run = client.post(
            endpoint,
            json={
                "content": QUESTION,
                "source_options": {
                    "use_knowledge": False,
                    "use_memory": False,
                    "use_deepwiki": False,
                },
            },
        ).json()
        report.update(project_id=project, thread_id=run["thread_id"], run_id=run["id"])
        (output / "identity.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        deadline = time.monotonic() + 900
        previous = None
        while time.monotonic() < deadline:
            current = client.get(base + f"/runs/{run['id']}").json()
            if current["status"] in {"completed", "failed", "cancelled", "interrupted"}:
                break
            state = client.get(base + f"/threads/{run['thread_id']}/code-work").json()
            phase = (
                state.get("verification", {}).get("status")
                if state.get("verification")
                else "editing"
            )
            if phase != previous:
                print(f"代码工作阶段：{phase}", flush=True)
                previous = phase
            time.sleep(1)
        else:
            raise TimeoutError("代码工作完整链路超过 900 秒")
        report["run"] = current
        status = client.get(base + f"/threads/{run['thread_id']}/code-work").json()
        report["status"] = status
        (output / "result.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert current["status"] == "completed", current.get("error", current["status"])
        assert status["verification_current"] and status["verification"]["status"] == "passed", (
            "当前修订未通过完整验证，请查看 result.json"
        )
        assert len(status["files"]) == 1 and status["files"][0]["path"] == FILE, (
            "修改文件与请求范围不符：" + str([file["path"] for file in status["files"]])
        )
        difference = client.get(
            base + f"/threads/{run['thread_id']}/code-work/diff", params={"path": FILE}
        ).json()
        assert "IsDispensingElectricOpen()" in difference["diff"], difference
        package = client.get(
            base + f"/threads/{run['thread_id']}/code-work/export",
            params={"revision": status["revision"]},
        )
        assert package.status_code == 200, package.text
        (output / "changes.zip").write_bytes(package.content)
        (output / "diff.json").write_text(
            json.dumps(difference, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert (args.source_root / FILE).read_bytes() == original
        print(
            "端到端通过：聊天编辑、版本差异、编译、Simulation 和下载；原文件哈希不变。",
            flush=True,
        )
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--msbuild", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real-model", action="store_true")
    parser.add_argument(
        "--resume", action="store_true", help="在同一测试对话中撤销旧修改并重新验收"
    )
    verify(parser.parse_args())
