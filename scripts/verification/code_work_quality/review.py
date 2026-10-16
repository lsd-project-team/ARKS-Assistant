"""人工语义评审单独保存，固定报告字节身份；AI复核事件不能代替此步骤。"""

import json
from datetime import UTC, datetime
from uuid import uuid4

from .safety import checked_path, file_hash, write_json

IDENTITY = (
    "report_id",
    "suite_id",
    "source_fingerprint",
    "model_fingerprint",
    "application_sha256",
)


def reviewed_outcome(case, ratings, require_sandbox):
    if set(ratings) != set(case["rubric"]):
        raise ValueError("必须逐项评审同一份rubric，不得省略或新增评审项")
    for rating in ratings.values():
        if (
            set(rating) != {"outcome", "rationale", "evidence"}
            or rating["outcome"] not in {"pass", "failed", "unknown"}
            or not isinstance(rating["rationale"], str)
            or not rating["rationale"].strip()
            or not isinstance(rating["evidence"], list)
            or not rating["evidence"]
            or any(not isinstance(item, str) or not item.strip() for item in rating["evidence"])
        ):
            raise ValueError("每项必须填写结论、理由和本报告内的依据位置")
    statuses = [
        row["status"]
        for row in case["checks"]
        if require_sandbox or row["name"] != "sandbox_verification"
    ]
    if "failed" in statuses or any(row["outcome"] == "failed" for row in ratings.values()):
        return "failed"
    if "unknown" in statuses or any(row["outcome"] == "unknown" for row in ratings.values()):
        return "unknown"
    return "pass"


def save_review(report_path, expected_hash, case_id, reviewer, ratings):
    report_path = checked_path(report_path)
    if file_hash(report_path) != expected_hash:
        raise ValueError("报告已改变，不能沿用先前审阅的报告哈希")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    case = next((row for row in report["cases"] if row["case_id"] == case_id), None)
    if case is None or not reviewer.strip():
        raise ValueError("评审场景或人工评审者身份无效")
    result = {
        **{key: report[key] for key in IDENTITY},
        "report_sha256": expected_hash,
        "case_id": case_id,
        "run_id": case["run_id"],
        "reviewer": reviewer,
        "reviewed_at": datetime.now(UTC).isoformat(),
        "ratings": ratings,
        "outcome": reviewed_outcome(
            case, ratings, bool(report["configuration"].get("verification_profile"))
        ),
        "scope": "人工自报的语义评审；非签名认证、设备验证或全项目理解证明",
    }
    destination = report_path.parent / f"review-{case_id}-{uuid4().hex}.json"
    write_json(destination, result)
    return destination


def verify_review(report_path, review_path):
    report_path, review_path = checked_path(report_path), checked_path(review_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if file_hash(report_path) != review["report_sha256"] or any(
        report[key] != review[key] for key in IDENTITY
    ):
        raise ValueError("报告字节或源码/模型/应用身份变化，旧评审失效")
    case = next(row for row in report["cases"] if row["case_id"] == review["case_id"])
    if case["run_id"] != review["run_id"]:
        raise ValueError("评审运行身份不符")
    outcome = reviewed_outcome(
        case, review["ratings"], bool(report["configuration"].get("verification_profile"))
    )
    if outcome != review["outcome"]:
        raise ValueError("评审结论与证据状态不一致")
    return outcome
