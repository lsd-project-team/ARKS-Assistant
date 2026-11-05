"""显式真实供应商验收：Excel/Word 文档驱动副本改码、编译和仿真。"""

import argparse
import json
import sys
import time
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from fastapi.testclient import TestClient  # noqa: E402
from openpyxl import Workbook  # noqa: E402

from app.core.config import Paths, SettingsStore  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.code_work.environment import CodeEnvironment  # noqa: E402
from app.modules.code_work.files import code_manifest  # noqa: E402
from tests.helpers.accounts import sign_in  # noqa: E402

FILE = "AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs"


def save(output, name, value):
    (output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def documents(output):
    book = Workbook()
    sheet = book.active
    sheet.title = "变更需求"
    for row in [
        ["项目", "要求"],
        ["文件", FILE],
        ["方法", "DispenseController.OpenDispensingElectric"],
        [
            "新规则",
            "点胶阀已打开时直接返回；关闭时才调用底层开阀。用本类 IsDispensingElectricOpen 判断。",
        ],
        ["修改范围", "只修改该方法，保留签名、关闭及状态读取逻辑。"],
    ]:
        sheet.append(row)
    book.save(output / "点胶阀新需求.xlsx")
    book.close()
    paragraphs = [
        "验收补充：先关闭阀，再连续调用两次 OpenDispensingElectric，"
        "底层 DispenseModule 的开阀方法只调用一次，最终阀开启。",
        "随后调用 CloseDispensingElectric，最终阀关闭。应使用 CountCalls 对真实业务方法计数，"
        "并用 Check 断言调用次数和最终状态。",
        "需编译业务副本、运行原工程 Simulation 自检及上述需求断言。修改只保存于独立副本。",
    ]
    with zipfile.ZipFile(output / "验收补充.docx", "w") as archive:
        body = "".join(f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>" for text in paragraphs)
        archive.writestr(
            "word/document.xml",
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            + body
            + "</w:body></w:document>",
        )
    return [output / "点胶阀新需求.xlsx", output / "验收补充.docx"]


def verify(args):
    if not args.live:
        raise ValueError("必须显式传入 --live，才会调用真实供应商")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "data/app.sqlite3").exists():
        raise ValueError("保留已有验收状态，请勿重复启动同一验收")
    configuration = SettingsStore(Paths()).load()
    configuration = configuration.model_copy(
        update={"mcp_servers": [], "deepwiki_repo": ""}, deep=True
    )
    environment = CodeEnvironment(Paths().data).load()
    source = Path(environment.source_root)
    original = code_manifest(source)
    paths = Paths(output / "data", ROOT / "trunk")
    app = create_app(paths)
    app.state.projects.base.settings.load = lambda: configuration.model_copy(deep=True)
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
        base = f"/api/p/{project}"
        app.state.projects.services(project).runtime.model_ledger.save({"token_limit": 2_000_000})
        attachments = []
        for file in documents(output):
            response = client.post(
                base + "/attachments",
                params={"filename": file.name},
                content=file.read_bytes(),
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()
            attachments.append(response.json())
        run_response = client.post(
            base + "/threads/start",
            json={
                "content": "请结合上传的 Excel 新需求和 Word 验收补充，"
                "实际修改现有代码并完成文档要求的验证。请先读取两份文档，"
                "完成后说明改动及实际验证结果。",
                "attachment_ids": [row["id"] for row in attachments],
                "source_options": {
                    "use_knowledge": False,
                    "use_memory": False,
                    "use_deepwiki": False,
                },
            },
        )
        run_response.raise_for_status()
        run = run_response.json()
        save(
            output,
            "identity.json",
            {"run_id": run["id"], "thread_id": run["thread_id"], "project_id": project},
        )
        prefix = base + f"/threads/{run['thread_id']}/code-work"
        print("real provider: " + configuration.model.model, flush=True)
        deadline = time.monotonic() + 1200
        previous = None
        while time.monotonic() < deadline:
            result = client.get(base + f"/runs/{run['id']}").json()
            work = client.get(prefix).json()
            state = (
                result["status"],
                work.get("revision"),
                (work.get("verification") or {}).get("status"),
            )
            if state != previous:
                print(str(state), flush=True)
                previous = state
                save(output, "progress.json", {"run": result, "work": work})
            if result["status"] in {"completed", "failed", "cancelled", "interrupted"}:
                break
            time.sleep(1)
        else:
            raise TimeoutError("运行仍在执行，不启动重复任务；请检查 identity 和 progress")
        trace = client.get(base + f"/runs/{run['id']}/trace").json()
        save(output, "events.json", trace)
        save(output, "run.json", result)
        save(output, "status.json", work)
        assert result["status"] == "completed", result.get("error")
        assert work.get("verification_current") and work["verification"]["status"] == "passed"
        assert [row["path"] for row in work["files"]] == [FILE]
        assert sum(row["assertions"] for row in work["verification"]["requirements_results"]) >= 3
        reads = {event["payload"]["id"] for event in trace if event["kind"] == "attachment_read"}
        assert reads == {row["id"] for row in attachments}
        difference = client.get(prefix + "/diff", params={"path": FILE}).json()
        save(output, "diff.json", difference)
        conversation = client.get(base + f"/threads/{run['thread_id']}").json()
        assert conversation["messages"][0]["attachments"] == attachments
        assert code_manifest(source) == original
        report = {
            "passed": True,
            "real_model": configuration.model.model,
            "both_documents_read": True,
            "attachments_restored": True,
            "original_unchanged": True,
            "verification": work["verification"],
        }
        save(output, "result.json", report)
        print(
            "PASS: uploaded Excel and Word drove verified copy edit; original unchanged", flush=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    verify(parser.parse_args())
