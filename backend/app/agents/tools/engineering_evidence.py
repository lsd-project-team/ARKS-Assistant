"""只从当前项目服务读取已观察的修改，不信任对话里的工具结果或模型自述。"""

from app.agents.context.tokens import fit_text
from app.agents.runtime.privacy import redact
from app.infrastructure.execution import sandbox_evidence_valid


def verification_evidence(proof, current, diff):
    executor = proof["executor"]
    raw = proof["output"]
    # 先脱敏再裁剪，避免裁掉password=之类的前缀后让敏感值失去识别条件。
    masked = redact(raw)
    output = fit_text(masked[::-1], 1000)[::-1]
    matches = (
        not proof["stale"]
        and diff["source_unchanged"]
        and not diff["scope_conflicts"]
        and executor.get("requirements_version") == current["requirements_version"]
    )
    return {
        **{
            key: proof[key]
            for key in (
                "id",
                "purpose",
                "profile_id",
                "status",
                "exit_code",
                "stale",
                "change_version",
                "source_version",
                "profile_version",
                "started_at",
                "ended_at",
                "error_category",
            )
        },
        "requirements_version": executor.get("requirements_version"),
        "current": matches,
        "successful_current": matches and proof["status"] == "passed" and proof["exit_code"] == 0,
        "executor": {key: executor.get(key) for key in ("kind", "platform", "image", "context")},
        "sandbox_verified": sandbox_evidence_valid(executor.get("evidence"), executor),
        "output": output,
        "output_truncated": proof["truncated"] or output != masked,
        "output_available": bool(raw),
    }


def code_work_evidence(changes, identifiers):
    unique = list(dict.fromkeys(identifiers))
    result = {"changes": [], "omitted_changes": max(0, len(unique) - 3)}
    for identifier in unique[-3:]:
        try:
            # 同一服务锁内取得差异与版本；每次复核重新读取，不能沿用编辑前的成功快照。
            with changes.lock:
                diff = changes.diff(identifier)
                current = changes.get(identifier)
                proofs = changes.verification_history(identifier)["verifications"]
            masked = redact(diff["diff"])
            patch = fit_text(masked, 1500)
            result["changes"].append(
                {
                    **{
                        key: current[key]
                        for key in (
                            "id",
                            "change_version",
                            "requirements_version",
                            "acceptance_criteria",
                            "constraints",
                            "allowed_paths",
                            "review",
                            "delivered_at",
                        )
                    },
                    "available": True,
                    "source_unchanged": diff["source_unchanged"],
                    "source_conflicts": diff["conflicts"],
                    "scope_conflicts": diff["scope_conflicts"],
                    "files": diff["files"],
                    "diff": patch,
                    "diff_truncated": patch != masked,
                    "verifications": [
                        verification_evidence(row, current, diff) for row in proofs[:4]
                    ],
                    "omitted_verifications": max(0, len(proofs) - 4),
                }
            )
        except (OSError, ValueError):
            # 不外发跨项目或已清理对象的异常正文，也不拿历史工具消息补造当前证据。
            result["changes"].append({"id": identifier, "available": False})
    return result
