"""合成资料下验证普通问答与历史查询边界；显式 --live 才调用当前供应商。"""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from langchain_core.callbacks import BaseCallbackHandler

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.agents.runtime import graph_builder  # noqa: E402
from app.bootstrap import create_services  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.modules.auth.context import request_identity  # noqa: E402
from app.modules.handover.application.commands import DebugWrite  # noqa: E402
from app.modules.handover.application.debug_issues import DebugIssues  # noqa: E402
from app.modules.handover.infrastructure.persistence.repository import HandoverStore  # noqa: E402
from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus  # noqa: E402
from app.modules.knowledge.semantic import SemanticRetrieval  # noqa: E402


async def verify():
    configuration = (
        SettingsStore(Paths())
        .load()
        .model_copy(
            update={"auto_memory": False, "mcp_servers": [], "deepwiki_repo": ""}, deep=True
        )
    )
    options = {"use_memory": False, "use_knowledge": True, "use_deepwiki": False}
    with tempfile.TemporaryDirectory(prefix="arks-general-question-") as temporary:
        root = Path(temporary)
        source = root / "source"
        source.mkdir()
        services = create_services(Paths(root / "data", source))
        token = request_identity.set({"user": {"id": "synthetic-account", "role": "admin"}})
        original_scores = SemanticRetrieval.scores
        original_init = DebugIssueCorpus.__init__
        original_create = graph_builder.create_model
        opened, searches, model_calls = [], [], []
        try:
            Base.metadata.create_all(services.database.engine)
            services.settings.load = lambda: configuration.model_copy(deep=True)
            services.runs.project_snapshot = lambda: {"name": "合成阀门项目"}
            DebugIssues(HandoverStore(database=services.database)).save(
                DebugWrite(
                    title="合成阀门试验",
                    payload={"problem": "2026年10月1日合成阀门试验，读数为42。仅记录了该日。"},
                ),
                {},
            )

            # 如实际检索就固定召回合成资料，并计数；普通问题须连快照与检索都不触发。
            def scores(_self, query, documents):
                searches.append(query)
                return dict.fromkeys(documents, 0.9)

            def opened_corpus(corpus, *args):
                opened.append(True)
                original_init(corpus, *args)

            SemanticRetrieval.scores = scores
            DebugIssueCorpus.__init__ = opened_corpus

            class CountCalls(BaseCallbackHandler):
                def on_chat_model_start(self, _serialized, _messages, *, metadata=None, **_kwargs):
                    model_calls.append((metadata or {}).get("lc_source", "answer"))

            def counted_model(*args, **kwargs):
                model = original_create(*args, **kwargs)
                model.callbacks = [*(model.callbacks or []), CountCalls()]
                return model

            graph_builder.create_model = counted_model
            prior = services.repository.create_run(None, "你好", [], options)
            services.repository.finish(
                prior["id"], "本轮返回的资料中，没有选到符合所问事项的内容。"
            )
            checks = []
            for question, expected_scope in (
                ("你好", "general"),
                ("给我介绍一下vue框架", "general"),
                ("查询2026年10月9日的合成阀门试验结果", "records"),
                ("查询2026年10月1日的合成阀门试验结果", "records"),
            ):
                previous_opened, previous_searches = len(opened), len(searches)
                previous_calls = len(model_calls)
                run = services.repository.create_run(prior["thread_id"], question, [], options)
                services.runs.start(run)
                await asyncio.gather(*services.runs.tasks.values())
                result = services.repository.run(run["id"])
                assert result["status"] == "completed", "真实问答未完成"
                selection = services.repository.run_event(run["id"], "knowledge_selection")
                review = services.repository.run_event(run["id"], "knowledge_answer_review")
                answer = services.repository.thread(run["thread_id"])["messages"][-1]["content"]
                events = services.repository.events(run["id"])
                tool_names = [
                    row["payload"]["name"] for row in events if row["kind"] == "tool_start"
                ]
                requests = model_calls[previous_calls:]
                if expected_scope == "general":
                    assert len(opened) == previous_opened and len(searches) == previous_searches
                    assert not tool_names and selection is None and review is None
                    assert requests == ["answer"], {
                        "question": question,
                        "requests": requests,
                        "answer": answer,
                    }
                    assert (
                        answer.strip()
                        and "没有选到" not in answer
                        and "资料筛选暂未完成" not in answer
                    )
                    assert "42" not in answer and "debug-issue:" not in answer, {
                        "question": question,
                        "answer": answer,
                    }
                    if "vue" in question:
                        assert "vue" in answer.casefold() and "框架" in answer
                elif "10月9日" in question:
                    assert "search_debug_issues" in tool_names, {
                        "question": question,
                        "tools": tool_names,
                        "answer": answer,
                    }
                    assert len(opened) == previous_opened + 1 and len(searches) > previous_searches
                    assert not selection["references"] and "没有选到" in answer
                    assert "42" not in answer and "debug-issue:" not in answer
                else:
                    assert len(opened) == previous_opened + 1
                    assert selection["references"] and "42" in answer
                    assert review["verdict"] in ("passed", "revised")
                checks.append(
                    {
                        "question": question,
                        "scope": expected_scope,
                        "answer": answer,
                        "tools": tool_names,
                        "model_requests": len(requests),
                        "corpus_loads": len(opened) - previous_opened,
                        "searches": len(searches) - previous_searches,
                    }
                )
            print(
                json.dumps(
                    {
                        "passed": True,
                        "routing_prompt": graph_builder.RETRIEVAL_GUIDANCE,
                        "checks": checks,
                    },
                    ensure_ascii=False,
                )
            )
        finally:
            SemanticRetrieval.scores = original_scores
            DebugIssueCorpus.__init__ = original_init
            graph_builder.create_model = original_create
            request_identity.reset(token)
            await services.runs.shutdown()
            services.runtime.semantic.close()
            services.database.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(verify())
