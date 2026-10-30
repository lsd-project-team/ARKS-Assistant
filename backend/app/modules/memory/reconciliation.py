"""后台写入前对相关候选进行关系核对，结果缓存到同账号/项目的固定版本快照。"""

import asyncio

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.context.tokens import estimate_tokens, input_budget
from app.core.config import dump_json
from app.modules.knowledge.search import catalog
from app.modules.memory.conflicts import (
    RECONCILE_PROMPT,
    ReconciliationResponse,
    checked_decisions,
    live_relations,
    pair_id,
)
from app.modules.memory.generation_protocol import parse_response
from app.modules.memory.retrieval import relevant_facts


def comparison_pairs(facts, reviews, retrieval):
    existing = {row["pair_id"] for row in reviews}
    indexed = {}
    for fact in facts:
        others = [row for row in facts if row["id"] != fact["id"]]
        matches = relevant_facts(
            fact["title"] + "\n" + fact["content"],
            [{"title": "待比较记忆", "memories": others}],
            retrieval,
            limit=12,
        )
        for _, other in matches:
            key = pair_id(fact["id"], other["id"])
            if key not in existing:
                indexed[key] = {
                    "id": key,
                    "facts": sorted([fact, other], key=lambda row: row["id"]),
                }
    return list(indexed.values())


def pair_batches(pairs, config):
    # 每次最多16对，且按真实提示词预算分片；不能截断事实条件或依据。
    budget = input_budget(config.model.context_tokens, min(config.model.output_tokens, 4096))
    pair_limit = max(1, min(16, min(config.model.output_tokens, 4096) // 192))
    batches, current = [], []
    for pair in pairs:
        candidate = [*current, pair]
        messages = [
            SystemMessage(content=RECONCILE_PROMPT),
            HumanMessage(content=dump_json(candidate)),
        ]
        if len(candidate) > pair_limit or estimate_tokens(messages) > budget:
            if not current:
                raise ValueError("memory_relation_input_too_large")
            batches.append(current)
            current = []
        current.append(pair)
        if (
            estimate_tokens(
                [SystemMessage(content=RECONCILE_PROMPT), HumanMessage(content=dump_json(current))]
            )
            > budget
        ):
            raise ValueError("memory_relation_input_too_large")
    return [*batches, *([current] if current else [])]


async def reconcile(worker, facts, previous, config, ledger):
    reviews = live_relations((previous or {}).get("document", {}).get("relations", []), facts)
    pairs = await asyncio.to_thread(
        comparison_pairs, facts, reviews, catalog(worker.services.database).retrieval
    )
    for batch in pair_batches(pairs, config):
        response = parse_response(
            await worker.invoke(config, ledger, RECONCILE_PROMPT, batch, consolidate=True),
            ReconciliationResponse,
        )
        reviews.extend(checked_decisions(response, batch))
    return reviews
