"""合成资料下验证普通问答与历史查询边界；显式 --live 才调用当前供应商。"""

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.bootstrap import create_services  # noqa: E402
from app.core.config import Paths, SettingsStore  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.modules.auth.context import request_identity  # noqa: E402
from app.modules.handover.application.commands import DebugWrite  # noqa: E402
from app.modules.handover.application.debug_issues import DebugIssues  # noqa: E402
from app.modules.handover.infrastructure.persistence.repository import HandoverStore  # noqa: E402
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
        try:
            Base.metadata.create_all(services.database.engine)
            services.settings.load = lambda: configuration.model_copy(deep=True)
            DebugIssues(HandoverStore(database=services.database)).save(
                DebugWrite(
                    title="合成阀门试验",
                    payload={"problem": "2026年10月1日合成阀门试验，读数为42。仅记录了该日。"},
                ),
                {},
            )
            # 固定为一定召回无关候选，只验证真实模型的意图筛选及回答链路，不评估向量质量。
            SemanticRetrieval.scores = lambda _self, _query, docs: dict.fromkeys(docs, 0.9)
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
                run = services.repository.create_run(prior["thread_id"], question, [], options)
                services.runs.start(run)
                await asyncio.gather(*services.runs.tasks.values())
                result = services.repository.run(run["id"])
                assert result["status"] == "completed", "真实问答未完成"
                selection = services.repository.run_event(run["id"], "knowledge_selection")
                review = services.repository.run_event(run["id"], "knowledge_answer_review")
                answer = services.repository.thread(run["thread_id"])["messages"][-1]["content"]
                assert selection and selection["scope"] == expected_scope, "问题范围判断不符"
                if expected_scope == "general":
                    assert review["verdict"] == "skipped" and not selection["references"]
                    assert (
                        answer.strip()
                        and "没有选到" not in answer
                        and "资料筛选暂未完成" not in answer
                    )
                    assert "合成阀门" not in answer and "debug-issue:" not in answer
                    if "vue" in question:
                        assert "vue" in answer.casefold() and "框架" in answer
                elif "10月9日" in question:
                    assert not selection["references"] and "没有选到" in answer
                    assert "42" not in answer and "debug-issue:" not in answer
                else:
                    assert selection["references"] and "42" in answer
                    assert review["verdict"] in ("passed", "revised")
                checks.append({"question": question, "scope": expected_scope, "answer": answer})
            print(json.dumps({"passed": True, "checks": checks}, ensure_ascii=False))
        finally:
            SemanticRetrieval.scores = original_scores
            request_identity.reset(token)
            await services.runs.shutdown()
            services.runtime.semantic.close()
            services.database.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", required=True)
    parser.parse_args()
    asyncio.run(verify())
