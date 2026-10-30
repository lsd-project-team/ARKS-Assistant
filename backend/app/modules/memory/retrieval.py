"""按单条记忆匹配当前问题；没有相关命中时不回退到整份文档。"""

import re

from app.modules.knowledge.search import expanded_terms
from app.modules.knowledge.terms import terms

# 通用问句和文档说明不承担主题匹配，避免“问题怎么处理”命中所有经验。
GENERIC_TERMS = {
    "怎么",
    "怎样",
    "这个",
    "那个",
    "这些",
    "哪些",
    "我们",
    "你们",
    "当前",
    "之前",
    "回答",
    "说明",
    "处理",
    "方法",
    "情况",
    "需要",
    "可以",
    "是否",
    "进行",
    "使用",
    "相关",
    "一下",
    "告诉",
    "看看",
    "记忆",
    "长期",
    "设备",
    "流程",
    "软件",
    "报警",
    "异常",
    "故障",
    "报错",
    "错误",
    "原因",
    "error",
    "alarm",
    "please",
    "what",
    "how",
    "does",
    "this",
    "that",
    "answer",
    "explain",
}


def query_terms(query):
    # 先隔开中文问句套语，避免“怎么处理”之间的跨词二元组成为主题命中。
    fillers = GENERIC_TERMS | {"请问", "解释", "如何", "什么", "问题", "源码", "代码", "项目"}
    cleaned = re.sub("|".join(sorted(word for word in fillers if not word.isascii())), " ", query)
    return terms(cleaned) - GENERIC_TERMS


def relevant_facts(query, groups, retrieval, *, limit=6):
    query = (query or "").strip()[:6000]
    original = query_terms(query)
    if not original or limit <= 0:
        return []
    expanded = expanded_terms(" ".join(sorted(original))) - GENERIC_TERMS
    records, documents = {}, {}
    for group in groups:
        for fact in group["memories"]:
            key = str(len(records))
            records[key] = (group["title"], fact)
            # 原文依据可能包含整段聊天的其他主题，不作为检索正文扩大命中。
            documents[key] = "\n".join(
                [fact["title"], fact["content"], *(row["path"] for row in fact["sources"])]
            )
    semantic = retrieval.scores(query, documents)
    ranked = []
    for key, (title, fact) in records.items():
        document_terms = terms(documents[key]) - GENERIC_TERMS
        exact = len(original & document_terms)
        aliases = len((expanded - original) & document_terms)
        meaning = semantic.get(key, 0)
        if not exact and not aliases and meaning < 0.58:
            continue
        score = exact + 0.25 * aliases + 2 * len(original & terms(fact["title"]))
        score += max(0, meaning) * 3
        ranked.append((score, int(key), title, fact))
    ranked.sort(key=lambda row: (-row[0], row[1]))
    return [(title, fact) for _, _, title, fact in ranked[:limit]]


def grouped_facts(facts):
    grouped = {}
    for title, fact in facts:
        grouped.setdefault(title, []).append(fact)
    return [{"title": title, "memories": rows} for title, rows in grouped.items()]
