"""显式 --live 使用合成聊天验证历史筛选；不写入正式对话或配置。"""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime import graph_builder  # noqa: E402
from app.bootstrap import create_services  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.modules.auth.context import request_identity  # noqa: E402
from app.modules.chat.context import ConversationContext  # noqa: E402


async def verify():
    configuration = (
        SettingsStore(Paths())
        .load()
        .model_copy(
            update={"auto_memory": False, "mcp_servers": [], "deepwiki_repo": ""}, deep=True
        )
    )
    options = {"use_memory": False, "use_knowledge": False, "use_deepwiki": False}
    with tempfile.TemporaryDirectory(prefix="arks-history-selection-") as temporary:
        folder = Path(temporary)
        source = folder / "source"
        source.mkdir()
        services = create_services(Paths(folder / "data", source))
        Base.metadata.create_all(services.database.engine)
        services.settings.load = lambda: configuration.model_copy(deep=True)
        original_create = graph_builder.create_model
        identity = request_identity.set({"user": {"id": "synthetic-account", "role": "admin"}})
        calls, contexts = [], []

        class Capture(BaseCallbackHandler):
            def on_chat_model_start(self, _serialized, messages, *, metadata=None, **_kwargs):
                purpose = (metadata or {}).get("lc_source", "answer")
                calls.append(purpose)
                if purpose == "answer":
                    contexts.append("\n".join(row.text for batch in messages for row in batch))

        def model(*args, **kwargs):
            value = original_create(*args, **kwargs)
            value.callbacks = [*(value.callbacks or []), Capture()]
            return value

        graph_builder.create_model = model
        checks = []

        async def ask(thread, question, *, forbidden=(), required=()):
            before_calls, before_contexts = len(calls), len(contexts)
            run = services.repository.create_run(thread, question, [], options)
            services.runs.start(run)
            await asyncio.gather(*services.runs.tasks.values())
            result = services.repository.run(run["id"])
            assert result["status"] == "completed", {
                "error": result.get("error"),
                "checks": [
                    row
                    for row in services.repository.events(run["id"])
                    if row["kind"] in {"history_selection", "knowledge_stage_error"}
                ],
            }
            context = "\n".join(contexts[before_contexts:])
            assert all(marker not in context for marker in forbidden), {
                "forbidden": forbidden,
                "question": question,
            }
            assert all(marker in context for marker in required), required
            events = services.repository.events(run["id"])
            assert not any(
                '"carry_ids"' in row["payload"].get("text", "")
                for row in events
                if row["kind"] == "token"
            )
            phases = calls[before_calls:]
            answer = result["answer"]
            checks.append(
                {
                    "question": question,
                    "answer": answer,
                    "model_calls": phases,
                    "history_selection": services.repository.run_event(
                        run["id"], "history_selection"
                    ),
                    "unrelated_history_in_answer_context": False,
                }
            )
            return answer, phases

        try:
            answer, phases = await ask(None, "你好")
            assert answer.strip() and phases == ["answer"]

            thread = services.repository.create_thread("合成旧历史")
            past = [
                ("聊聊星座，不是任务要求。", "旧话题：星座的HISTORY_NOISE_777。"),
                (
                    "请记住本次任务约束：只读，默认中文。方案A的影响尚未核查。",
                    "任务状态：方案A说明已完成，影响尚未核查。",
                ),
                ("方案A在这段聊天里指什么？", "方案A指合成消息路由的说明方案。"),
                *[(f"继续讨论方案A，第{n}轮。", "我们仍在讨论方案A，保持只读。") for n in range(5)],
            ]
            for question, response in past:
                run = services.repository.create_run(thread["id"], question, [], options)
                services.repository.finish(run["id"], response)
            original = services.repository.thread(thread["id"])["messages"]
            answer, phases = await ask(
                thread["id"],
                "只核对我们这段聊天：现在讨论哪个方案，还有什么没有完成？请直接回答，不查项目资料。",
                forbidden=("HISTORY_NOISE_777",),
                required=("只读", "影响尚未核查", "方案A"),
            )
            assert "history_selection" in phases and "方案A" in answer and "影响" in answer
            assert services.repository.thread(thread["id"])["messages"][: len(original)] == original

            summary_thread = services.repository.create_thread("合成摘要")
            raw = services.repository.create_run(
                summary_thread["id"], "只读、默认中文，方案B的依赖还没核查。", [], options
            )
            services.repository.finish(raw["id"], "方案B说明已做，依赖尚未核查。")
            messages = services.repository.thread(summary_thread["id"])["messages"]
            summary = (
                "Here is a summary of the conversation to date:\n\n"
                "## 目标\n继续核对方案B的依赖。\n"
                "## 用户要求与约束\n只读，默认中文，不能声称已验证。\n"
                "## 已确认结论\n旧娱乐话题：HISTORY_NOISE_888。\n方案B说明已做，依赖尚未核查。\n"
                "## 源码依据\n无\n## 待办\n核查方案B的依赖，尚未完成。\n"
                "## 待确认项\n依赖的实际状态未知。"
            )
            async with AsyncSqliteSaver.from_conn_string(
                str(services.paths.data / "checkpoints.sqlite3")
            ) as saver:
                graph = await services.runtime.graph(
                    summary_thread["id"], saver, lambda *_: None, inspection=True
                )
                await graph.aupdate_state(
                    {
                        "configurable": {
                            "thread_id": services.runtime.checkpoint_id(summary_thread["id"])
                        }
                    },
                    {
                        "messages": [
                            HumanMessage(content=messages[0]["content"], id=messages[0]["id"]),
                            AIMessage(content=messages[1]["content"], id=messages[1]["id"]),
                        ],
                        "_summarization_event": {
                            "cutoff_index": 2,
                            "summary_message": HumanMessage(content=summary),
                            "file_path": None,
                        },
                    },
                    as_node="model",
                )
            answer, phases = await ask(
                summary_thread["id"],
                "只核对聊天：方案B的约束和还没完成的事情是什么？直接回答，不查项目资料。",
                forbidden=("HISTORY_NOISE_888",),
                required=("只读", "尚未完成", "不能声称已验证"),
            )
            assert "history_selection" in phases and "方案B" in answer and "依赖" in answer
            restored = await ConversationContext(services.runtime).read(summary_thread["id"])
            assert "HISTORY_NOISE_888" in restored["summary"]
            checks[-1]["original_summary_preserved"] = True
            print(json.dumps({"passed": True, "checks": checks}, ensure_ascii=False))
        finally:
            graph_builder.create_model = original_create
            request_identity.reset(identity)
            await services.runs.shutdown()
            services.runtime.semantic.close()
            services.database.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(verify())
