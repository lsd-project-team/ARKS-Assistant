"""运行结束、输出完整度、源码核查覆盖分别记录，不能互相替代。"""


def completion_report(output, progress, counts, validation=None, review=None):
    partial = bool(progress["pending"] or counts["skipped"] or counts["failed"])
    coverage = "partial" if partial else "read" if progress["checks"] else "unassessed"
    if output["output"] == "incomplete":
        stage, label = "answer_incomplete", "运行已结束 · 回答未完整"
    elif output["output"] == "suspected_truncated":
        stage, label = "answer_suspected_truncated", "运行已结束 · 回答可能被截断"
    elif partial:
        stage, label = "partial_review", "运行已结束 · 部分核查完成"
    else:
        stage, label = "completed", "运行已结束"
    return {
        **output,
        "coverage": coverage,
        "stage": stage,
        "label": label,
        "counts": counts,
        "remaining": len(progress["pending"]),
        "reference_check": validation,
        "semantic_review": review,
        "scope": "运行结束不代表项目功能完成或全部源码已核查",
    }
