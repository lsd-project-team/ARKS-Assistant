"""当前模型、真实Agent链路、临时数据库；不读正式对话与业务记录。"""

import asyncio
import base64
import hashlib
import json
import tempfile
import time
from contextvars import ContextVar
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

from app.agents.runtime.configuration import bind_configuration
from app.agents.runtime.engine import AgentRuntime
from app.agents.runtime.privacy import redact
from app.core.config import PROJECT_ROOT, AppSettings, Paths, SettingsStore
from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.modules.chat.repository import Repository
from app.modules.handover.application.commands import DebugWrite
from app.modules.handover.application.debug_issues import DebugIssues
from app.modules.handover.infrastructure.persistence.repository import HandoverStore
from app.modules.memory.service import MemoryService
from app.modules.source_analysis.workspace import Workspace

from .cases import BEFORE, RECORDS, cases

PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aX1sAAAAASUVORK5CYII="
)
GIF = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
EVENTS = {
    "knowledge_stage_error",
    "answer_presentation",
    "answer_draft",
    "review_raw",
    "knowledge_selection",
    "knowledge_answer_check",
    "knowledge_answer_review",
    "knowledge_reference",
    "knowledge_search",
    "provider_usage",
    "source_evidence",
    "source_review",
    "answer_validation",
    "notice",
    "run_completion",
    "tool_start",
}
AUDIT_EVENTS = ContextVar("answer_quality_audit", default=None)


class ReviewObserver(BaseCallbackHandler):
    """显式诊断模式只保留脱敏后的复核输出，不记录连接配置或密钥。"""

    def __init__(self, destination):
        self.destination, self.review_runs = destination, set()

    def on_chat_model_start(self, serialized, messages, *, run_id, metadata=None, **kwargs):
        if (metadata or {}).get("lc_source") in {"knowledge_verification", "knowledge_selection"}:
            self.review_runs.add(run_id)

    def on_llm_end(self, response, *, run_id, **kwargs):
        if run_id in self.review_runs:
            text = response.generations[0][0].message.text
            self.destination.append({"kind": "review_raw", "payload": {"text": redact(text)}})


def observe_reviews():
    from app.agents.runtime import graph_builder

    create = graph_builder.create_model

    def audited_model(*args, **kwargs):
        model = create(*args, **kwargs)
        destination = AUDIT_EVENTS.get()
        if destination is not None:
            model.callbacks = [*(model.callbacks or []), ReviewObserver(destination)]
        return model

    graph_builder.create_model = audited_model


def write(path, value):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def app_version():
    return hashlib.sha256(
        b"".join(
            str(path.relative_to(PROJECT_ROOT)).encode() + path.read_bytes()
            for path in sorted((PROJECT_ROOT / "backend/app").rglob("*.py"))
        )
    ).hexdigest()


def seed_records(database):
    issues = DebugIssues(HandoverStore(database=database))
    result = {}
    for name, data in RECORDS.items():
        row = issues.save(
            DebugWrite(
                title=data["title"],
                payload={
                    "problem": data["text"],
                    "device": data["device"],
                    "resolution_status": "recorded",
                    "record_type": "experience",
                },
            ),
            {"display_name": "隔离测评夹具"},
        )
        for index in range(data["images"]):
            row = issues.add_image(
                row["id"],
                row["version"],
                GIF if index == 2 else PNG,
                "验收测试图片.png",
                "",
                {"display_name": "隔离测评夹具"},
            )
        result[name] = {
            "id": row["id"],
            "version": row["version"],
            "reference": f"debug-issue:{row['id']}/{row['version']}",
            "image_count": len(row["payload"]["images"]),
        }
    return result


async def execute(case, config, directory, case_timeout_seconds=600):
    with tempfile.TemporaryDirectory(
        prefix="arks-quality-20-", ignore_cleanup_errors=True
    ) as temporary:
        target = Path(temporary)
        empty = target / "source"
        empty.mkdir()
        source = PROJECT_ROOT / "trunk" if case["category"] == "flow" else empty
        paths = Paths(target / "data", source)
        database = Database(paths.data / "app.sqlite3")
        Base.metadata.create_all(database.engine)
        workspace = Workspace(source)
        repository = Repository(database, workspace.id)
        settings = SettingsStore(paths)
        settings.save(
            AppSettings(
                model=config.model.model_copy(update={"api_key": ""}),
                mcp_servers=[],
                auto_memory=False,
            )
        )
        try:
            seeded = seed_records(database) if case["category"] == "experience" else {}
        except Exception:
            database.close()
            raise
        runtime = AgentRuntime(
            paths, settings, workspace, repository, MemoryService(paths, database, workspace)
        )
        options = {"use_memory": False, "use_knowledge": bool(seeded), "use_deepwiki": False}
        thread = repository.create_thread("隔离回答质量测评")
        if case["id"] in {"E01", "E07"}:
            old = repository.create_run(thread["id"], "adv-3的7月23日试验", [], options)
            repository.finish(old["id"], BEFORE)
        selections = []
        oracle_sources = []
        if case.get("source"):
            spec = case["source"]
            read = workspace.read(spec["path"])
            excerpt = "\n".join(read["content"].splitlines()[spec["start"] - 1 : spec["end"]])
            selections = [
                {
                    "path": spec["path"],
                    "start_line": spec["start"],
                    "end_line": spec["end"],
                    "content": excerpt,
                    "version": read["version"],
                }
            ]
            oracle_sources = selections
        run = repository.create_run(thread["id"], case["question"], selections, options)
        events, started = [], time.monotonic()
        audit_token = AUDIT_EVENTS.set(events)
        result = {**case, "seeds": seeded, "oracle_sources": oracle_sources}
        try:
            with bind_configuration(config):
                answer = await asyncio.wait_for(
                    runtime.execute(
                        run, lambda kind, payload: events.append({"kind": kind, "payload": payload})
                    ),
                    case_timeout_seconds,
                )
            repository.finish(run["id"], answer)
            result.update(
                answer=answer,
                status="answered",
                persisted=repository.thread(thread["id"])["messages"][-1]["content"] == answer,
            )
        except Exception as error:
            result.update(answer="", status="error", error=type(error).__name__)
        finally:
            result.update(
                seconds=round(time.monotonic() - started, 2),
                events=[row for row in events if row["kind"] in EVENTS],
            )
            result["cited_records"] = [
                key for key, row in seeded.items() if row["reference"] in result["answer"]
            ]
            result["image_positions"] = sum(
                seeded[key]["image_count"] for key in result["cited_records"]
            )
            result["raw_draft_exposed"] = any(row["kind"] == "token" for row in events)
            result["forbidden_hits"] = [
                word for word in case["forbidden"] if word in result["answer"]
            ]
            write(directory / f"{case['id']}.json", result)
            await runtime.project_reading.shutdown()
            await runtime.code_changes.shutdown()
            runtime.semantic.close()
            database.close()
            AUDIT_EVENTS.reset(audit_token)
        return result


async def main(args):
    if args.audit:
        observe_reviews()
    output = await asyncio.to_thread(Path(args.output).resolve)
    if not output.is_relative_to(PROJECT_ROOT / "output"):
        raise ValueError("测评产物只能写入output")
    output.mkdir(parents=True, exist_ok=True)
    results = output / "results"
    results.mkdir(exist_ok=True)
    selected = SettingsStore(Paths()).load()
    config = AppSettings(model=selected.model, mcp_servers=[], auto_memory=False)
    manifest = {
        "seed": args.seed,
        "model": config.model.model,
        "model_parameters": {
            key: getattr(config.model, key)
            for key in (
                "protocol",
                "temperature",
                "context_tokens",
                "output_tokens",
                "timeout_seconds",
            )
        },
        "application_sha256": app_version(),
        "cases": cases(args.seed),
        "timeout_seconds": args.timeout,
        "dataset_sha256": hashlib.sha256(
            json.dumps(
                {"records": RECORDS, "cases": cases(args.seed)}, ensure_ascii=False, sort_keys=True
            ).encode()
        ).hexdigest(),
        "scope": (
            "15条经验、5条设备流程；经验仅使用用户提供的3条记录及2条明确合成干扰；"
            "流程使用当前trunk只读源码和明确选区。图片为隔离测试资产，检查关联，不判读设备原图内容。"
        ),
    }
    manifest_path = output / "manifest.json"
    if manifest_path.exists():
        old = json.loads(manifest_path.read_text(encoding="utf-8"))
        if any(
            old.get(key) != manifest[key]
            for key in ("seed", "model", "application_sha256", "dataset_sha256", "timeout_seconds")
        ):
            raise ValueError("应用版本或题集已改变，请使用新的测评目录，不能覆盖旧结果")
    write(manifest_path, manifest)
    if args.ids and set(args.ids) - {row["id"] for row in manifest["cases"]}:
        raise ValueError("未知测评题号")
    chosen = [row for row in manifest["cases"] if not args.ids or row["id"] in args.ids]
    semaphore = asyncio.Semaphore(args.concurrency)

    async def ask(case):
        async with semaphore:
            if (results / f"{case['id']}.json").exists():
                print(case["id"], "已有结果，跳过", flush=True)
                return
            try:
                result = await execute(case, config, results, args.timeout)
            except Exception as error:
                saved = results / f"{case['id']}.json"
                result = (
                    json.loads(saved.read_text(encoding="utf-8"))
                    if saved.exists()
                    else {
                        **case,
                        "status": "error",
                        "answer": "",
                        "seconds": 0,
                        "error": type(error).__name__,
                    }
                )
                if saved.exists():
                    result["cleanup_error"] = type(error).__name__
                write(saved, result)
            print(case["id"], result["status"], result["seconds"], "seconds", flush=True)

    await asyncio.gather(*(ask(case) for case in chosen))
