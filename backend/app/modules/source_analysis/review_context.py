"""复核的当前源码资料：引用优先，补齐本轮实际读过的调用及测试文件。"""

import hashlib
from pathlib import PurePosixPath

from app.agents.context.tokens import text_tokens
from app.core.config import dump_json
from app.modules.source_analysis.evidence import enclosing_excerpt, source_excerpt


def source_review_context(evidence, answer):
    blocks, omitted = [], []

    def include(block, *, required=False):
        start = block["lines"][0]["line"] if block["lines"] else 0
        end = block["lines"][-1]["line"] if block["lines"] else 0
        same = [
            row
            for row in blocks
            if row["path"] == block["path"] and row["version"] == block["version"]
        ]

        def contains(row, first, last):
            return (row["lines"][0]["line"] if row["lines"] else 0) <= first and (
                row["lines"][-1]["line"] if row["lines"] else 0
            ) >= last

        if any(contains(row, start, end) for row in same):
            return
        candidate = [
            row
            for row in blocks
            if row not in same
            or not contains(
                block,
                row["lines"][0]["line"] if row["lines"] else 0,
                row["lines"][-1]["line"] if row["lines"] else 0,
            )
        ]
        candidate.append(block)
        if text_tokens(dump_json(candidate)) > 8000:
            if required:
                raise ValueError("本轮引用源码超出复核预算，未宣称全部结论已验证")
            omitted.append({"path": block["path"], "reason": "budget"})
            return
        blocks[:] = candidate

    for row in evidence.check(answer)["citations"]:
        if not row["valid"]:
            continue
        block = enclosing_excerpt(evidence.workspace, row["path"], row["start_line"], 200)
        if block["version"] != row["version"]:
            raise ValueError("源码在复核过程中发生变化")
        include(block, required=True)
        if not (
            block["lines"][0]["line"]
            <= row["start_line"]
            <= row["end_line"]
            <= block["lines"][-1]["line"]
        ):
            include(
                source_excerpt(evidence.workspace, row["path"], row["start_line"], row["end_line"]),
                required=True,
            )

    # 不把复核自动扩展过的片段当成回答模型已经读取的资料。优先保留回答提到的文件。
    reads = [row for row in evidence.reads if not row.get("review_only")]
    reads.sort(
        key=lambda row: not (row["path"] in answer or PurePosixPath(row["path"]).stem in answer)
    )
    for row in reads:
        try:
            block = source_excerpt(
                evidence.workspace, row["path"], max(1, row["start_line"]), row["end_line"]
            )
            if block["version"] != row["version"]:
                omitted.append({"path": row["path"], "reason": "version_changed"})
                continue
            include(block)
        except (OSError, ValueError):
            omitted.append({"path": row["path"], "reason": "unavailable"})
    return {"source": blocks, "source_omissions": omitted}


def review_context_manifest(messages, payload, estimated_tokens):
    """只保存实际外发资料的身份和范围，不在事件里重复源码、日志或敏感值。"""
    return {
        "input_sha256": hashlib.sha256(
            dump_json([message.text for message in messages]).encode("utf-8")
        ).hexdigest(),
        "input_tokens_estimate": estimated_tokens,
        "sources": [
            {
                "path": row["path"],
                "version": row["version"],
                "start_line": row["lines"][0]["line"] if row["lines"] else 0,
                "end_line": row["lines"][-1]["line"] if row["lines"] else 0,
            }
            for row in payload["source"]
        ],
        "source_omissions": payload["source_omissions"],
        "changes": [
            {
                "id": row["id"],
                "available": row["available"],
                "change_version": row.get("change_version"),
                "requirements_version": row.get("requirements_version"),
                "verifications": [
                    {
                        key: proof[key]
                        for key in (
                            "id",
                            "current",
                            "successful_current",
                            "sandbox_verified",
                            "output_truncated",
                        )
                    }
                    for proof in row.get("verifications", [])
                ],
                "omitted_verifications": row.get("omitted_verifications", 0),
            }
            for row in payload["code_work"]["changes"]
        ],
        "omitted_changes": payload["code_work"]["omitted_changes"],
    }
