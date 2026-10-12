"""可解释的本地记忆检索与相似性检查，不把词面相似冒充语义矛盾判断。"""

import re
import unicodedata


def normalized(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).casefold())


def terms(text: str) -> set[str]:
    text = unicodedata.normalize("NFKC", text).casefold()
    # S1、S2、K9 等短标识符也需要精确匹配，避免完全依赖向量相似度。
    result = set(re.findall(r"[a-z_][a-z0-9_]+", text))
    ignored = {"源码", "代码", "项目", "函数", "解释", "什么", "如何", "一下", "请问", "问题"}
    ignored |= {
        "cs",
        "md",
        "ts",
        "js",
        "py",
        "json",
        "the",
        "and",
        "is",
        "to",
        "of",
        "in",
        "on",
        "an",
        "as",
        "by",
        "or",
    }
    for fragment in re.findall(r"[\u4e00-\u9fff]+", text):
        result.update(fragment[index : index + 2] for index in range(len(fragment) - 1))
    return result - ignored


def facts(text: str) -> dict[str, str]:
    result = {}
    for line in text.splitlines():
        stripped = line.strip().lstrip("-•* ")
        if re.match(r"https?://", stripped):
            continue
        parts = re.split(r"[:：=]", stripped, maxsplit=1)
        if len(parts) == 2 and 1 <= len(parts[0]) <= 60:
            result[normalized(parts[0])] = normalized(parts[1])
    return result


def related_memories(rows, request) -> list[dict]:
    content = normalized(request.content)
    query_terms = terms(request.content)
    query_facts = facts(request.content)
    matches = []
    for row in rows:
        if row["scope"] != request.scope or row["name"] == request.name:
            continue
        other = terms(row["content"])
        overlap = len(query_terms & other) / max(1, len(query_terms | other))
        disagreements = [
            key
            for key, value in facts(row["content"]).items()
            if key in query_facts and query_facts[key] != value
        ]
        if content == normalized(row["content"]):
            kind, reason = "duplicate", "内容相同，仅空白或大小写不同"
        elif disagreements:
            kind, reason = "conflict", "相同字段出现不同值，请核对后保存"
        elif overlap >= 0.55 and len(query_terms & other) >= 2:
            kind, reason = "similar", "词面内容相似，建议合并或核对"
        else:
            continue
        matches.append(
            {
                "name": row["name"],
                "scope": row["scope"],
                "version": row["version"],
                "kind": kind,
                "reason": reason,
                "content": row["content"],
            }
        )
    order = {"duplicate": 0, "conflict": 1, "similar": 2}
    return sorted(matches, key=lambda row: (order[row["kind"]], row["name"]))


def rank_memories(rows, query: str | None, semantic_scores=None):
    query_terms = terms(query or "")
    ranked = []
    seen = set()
    for row in rows:
        source_text = " ".join(source["path"] for source in row["sources"])
        title_score = 3 * len(query_terms & terms(row["name"] + " " + source_text))
        score = title_score + len(query_terms & terms(row["content"]))
        semantic = (semantic_scores or {}).get(f"{row['scope']}/{row['name']}", 0)
        if row["scope"] != "user" and query is not None and score == 0 and semantic < 0.5:
            continue
        ranked.append(
            {
                **row,
                "relevance": score,
                "semantic_relevance": round(semantic, 4),
                "inclusion_reason": "稳定用户偏好"
                if row["scope"] == "user"
                else ("与问题或选区路径匹配" if score else "与问题含义相近（本机语义检索）")
                if query is not None
                else "全部记忆预览",
            }
        )
    ranked.sort(
        key=lambda row: (
            row["scope"] != "user",
            -row["relevance"],
            -row["semantic_relevance"],
            -row["updated_at"],
            row["name"],
        )
    )
    indexed = [(row, facts(row["content"])) for row in ranked]
    for row, current in indexed:
        key = normalized(row["content"])
        if key not in seen:
            seen.add(key)
            conflicts = [
                f"{other['scope']}/{other['name']}"
                for other, other_facts in indexed
                if other is not row
                and any(
                    key in current and current[key] != value for key, value in other_facts.items()
                )
            ]
            yield {**row, "conflicts": conflicts}
