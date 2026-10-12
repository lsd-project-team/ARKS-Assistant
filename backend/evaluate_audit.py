"""复现真实问答中发现的顺序错误，验证新复核流程而不覆盖先前验收报告。"""

import asyncio
import json

from app.config import PROJECT_ROOT, Paths, SettingsStore
from app.models import Base
from app.services import create_services

PATH = "AKRS.ZX2200/Main/Machine/MachineSupport/Machine.Operate.cs"


async def main():
    services = create_services(
        Paths(PROJECT_ROOT / "output/quality-audit/data", PROJECT_ROOT / "trunk")
    )
    Base.metadata.create_all(services.database.engine)
    services.settings.save(SettingsStore(Paths()).load().model_copy(update={"auto_memory": False}))
    source = services.workspace.read(PATH)
    thread = services.repository.create_thread("提前返回顺序复核验收")
    selection = {
        "path": PATH,
        "start_line": 185,
        "end_line": 255,
        "version": source["version"],
        "content": "\n".join(source["content"].splitlines()[184:255]),
    }
    run = services.repository.create_run(
        thread["id"],
        "解释 PrepareMachineReadyToStart 的六个提前返回条件。"
        "是否所有 return false 都在 MoveToSafePos/AbsoluteMove 调用之前？"
        "区分发起调用和设备实际运动，给出当前源码引用。",
        [selection],
        source_options={"use_deepwiki": False, "use_memory": False, "use_knowledge": True},
    )
    try:
        answer = await services.runtime.execute(
            run, lambda kind, payload: services.repository.event(run["id"], kind, payload)
        )
        services.repository.finish(run["id"], answer)
        events, cursor = [], 0
        while True:
            page = services.repository.events(run["id"], cursor)
            events.extend(page)
            if len(page) < 500:
                break
            cursor = page[-1]["sequence"]
        report = {
            "answer": answer,
            "events": [
                event
                for event in events
                if event["kind"]
                in {"source_review", "answer_validation", "provider_usage", "source_evidence"}
            ],
        }
        (PROJECT_ROOT / "output/quality-audit/report.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(answer, flush=True)
    finally:
        services.runtime.semantic.close()
        services.database.close()


if __name__ == "__main__":
    asyncio.run(main())
