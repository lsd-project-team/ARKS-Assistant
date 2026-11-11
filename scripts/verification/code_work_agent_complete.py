"""隔离数据中执行真实Agent工具循环、需求反例修复、原界面流程和合并回退。"""

import json
import re
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage  # noqa: E402
from langchain_core.outputs import ChatGeneration, ChatResult  # noqa: E402

from app.core.config import Paths  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.code_work.files import code_manifest  # noqa: E402
from tests.helpers.accounts import sign_in  # noqa: E402
from tests.helpers.models import DeterministicModel  # noqa: E402

FILE = "AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs"
OUT = ROOT / "output/code-work-complete-20261104"


class RepairModel(DeterministicModel):
    """只替代供应商边界，编译、需求断言、桌面按钮和源文件均真实执行。"""

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        tools = [item for item in messages if isinstance(item, ToolMessage)]
        last = tools[-1] if tools else None
        arguments = {}
        if last is None:
            name = "prepare_code_workspace"
        elif last.name == "prepare_code_workspace":
            status = json.loads(last.content)
            case = status["requirements"][0]
            name = "set_work_requirement"
            arguments = {
                "test_id": case["id"],
                "version": case["version"],
                "name": case["name"],
                "expectation": case["expectation"],
                "code": case["code"],
            }
        elif last.name in {"set_work_requirement", "edit_work_file"}:
            name = "verify_code_workspace"
        elif last.name == "verify_code_workspace":
            status = json.loads(last.content)
            job = status["verification"]
            if job["status"] == "passed":
                text = (
                    "已在独立副本修复开阀幂等：连续两次打开只下发一次开阀，关闭和读取保持有效。"
                    "编译、16项虚拟驱动、69项原工程集成检查、3项需求断言及原界面7步流程通过，"
                    "步骤截图可在验证面板查看。"
                )
                return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
            assert "实际次数=2" in job["steps"][-1]["log"], job
            if not isinstance(messages[-1], HumanMessage):
                return ChatResult(
                    generations=[
                        ChatGeneration(message=AIMessage(content="需求测试失败，需要继续修复。"))
                    ]
                )
            name = "read_work_file"
            arguments = {"path": FILE, "start_line": 820, "end_line": 855}
        elif last.name == "read_work_file":
            status = json.loads(last.content)
            content = "\n".join(
                re.sub(r"^\d+: ", "", line) for line in status["content"].splitlines()
            )
            target = re.search(
                r"public void OpenDispensingElectric\(\)\s*\{\s*"
                r"this\.DispenseModule\.OpenDispensingElectric\(\);\s*\}",
                content,
            )
            assert target, "目标控制器方法必须确实存在"
            name = "edit_work_file"
            arguments = {
                "path": FILE,
                "version": status["version"],
                "old_text": target[0],
                "new_text": (
                    "public void OpenDispensingElectric()\n        {\n"
                    "            if (!this.DispenseModule.IsDispensingElectricOpen())\n"
                    "                this.DispenseModule.OpenDispensingElectric();\n        }"
                ),
            }
        else:
            raise AssertionError("unexpected tool " + last.name)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content="",
                        tool_calls=[
                            {"id": "complete-" + str(len(tools)), "name": name, "args": arguments}
                        ],
                    )
                )
            ]
        )


def poll(client, path, field, terminal, timeout=1000):
    deadline = time.monotonic() + timeout
    previous = ""
    while time.monotonic() < deadline:
        response = client.get(path)
        response.raise_for_status()
        value = response.json()
        current = value.get(field)
        if current != previous:
            print(json.dumps({"path": path, "status": current}, ensure_ascii=False), flush=True)
            previous = current
        if current in terminal:
            return value
        time.sleep(0.3)
    raise TimeoutError("本次Agent/验证未在限定时间结束")


def main():
    if (OUT / "agent-complete.json").exists():
        raise RuntimeError("此验收已完成，保留原始证据；重新执行请准备新的独立验收目录和对话")
    identity = json.loads((OUT / "identity.json").read_text(encoding="utf-8"))
    origin = Path(identity["test_origin"])
    original = Path("C:/Users/w/Desktop/AKRS.ZX2200/trunk")
    assert code_manifest(original) == identity["original_code"]
    app = create_app(Paths(OUT / "data", origin))
    with (
        patch(
            "app.agents.runtime.graph_builder.create_model", lambda *args, **kwargs: RepairModel()
        ),
        TestClient(app) as client,
    ):
        sign_in(client)
        project = client.get("/api/projects").json()["default_project_id"]
        base = f"/api/p/{project}"
        prefix = base + f"/threads/{identity['thread_id']}/code-work"
        status = client.get(prefix).json()
        assert "files" in status, status
        for item in status["files"]:
            response = client.post(
                prefix + "/revert", json={"path": item["path"], "version": item["version"]}
            )
            response.raise_for_status()
        run = client.post(
            base + f"/threads/{identity['thread_id']}/runs",
            json={
                "content": (
                    f"/修改代码 在 {FILE} 的 DispenseController.OpenDispensingElectric "
                    "修复重复开阀幂等。先运行已有需求测试确认反例，再按失败结果修复并重验，"
                    "保留关闭与读取方法，验证原桌面按钮和生产流程。"
                ),
                "source_options": {
                    "use_knowledge": False,
                    "use_memory": False,
                    "use_deepwiki": False,
                },
            },
        ).json()
        result = poll(
            client,
            base + f"/runs/{run['id']}",
            "status",
            {"completed", "failed", "cancelled", "interrupted"},
        )
        (OUT / "agent-run.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        assert result["status"] == "completed", result
        status = client.get(prefix).json()
        job = status["verification"]
        assert job["status"] == "passed" and job["attempt"] == 2 and job["run_id"] == run["id"], job
        assert status["verification_current"] and len(job["desktop_results"]) == 7
        summary = client.get(prefix + "/summary", params={"run_id": run["id"]}).json()
        assert [item["path"] for item in summary["files"]] == [FILE], summary
        plan_response = client.post(prefix + "/merge/preview", json={})
        plan_response.raise_for_status()
        plan = plan_response.json()
        endpoint = prefix + "/merge/" + plan["id"]
        client.post(endpoint + "/verify").raise_for_status()
        deadline = time.monotonic() + 1000
        while time.monotonic() < deadline:
            verified = client.get(endpoint).json()
            if verified.get("verification", {}).get("status") not in {
                "queued",
                "building",
                "testing",
            }:
                break
            time.sleep(0.3)
        assert verified["can_apply"], verified
        before = (origin / FILE).read_bytes()
        applied = client.post(endpoint + "/apply", json={"confirm_target": plan["target"]})
        applied.raise_for_status()
        assert not applied.json()["files"]
        assert client.get(prefix + "/summary", params={"run_id": run["id"]}).json() == summary
        client.post(
            endpoint + "/rollback", json={"confirm_target": plan["target"]}
        ).raise_for_status()
        assert (origin / FILE).read_bytes() == before
        image = client.get(
            prefix + "/report",
            params={
                "job_id": job["id"],
                "name": next(
                    item["screenshot"]
                    for item in job["desktop_results"]
                    if item["id"] == "production"
                ),
            },
        )
        image.raise_for_status()
        (OUT / "actual-desktop.png").write_bytes(image.content)
        (OUT / "agent-complete.json").write_text(
            json.dumps(
                {
                    "passed": True,
                    "real_provider": False,
                    "project_id": project,
                    "thread_id": identity["thread_id"],
                    "run_id": run["id"],
                    "plan_id": plan["id"],
                    "verification": job,
                    "merged_verification": verified["verification"],
                    "summary": summary,
                    "original_unchanged": code_manifest(original) == identity["original_code"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            "PASS: real tool/compiler/desktop/merge flow with deterministic provider boundary",
            flush=True,
        )


if __name__ == "__main__":
    main()
