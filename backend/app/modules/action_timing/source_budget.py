"""保护单动作分析资源；复制的并行分支和重置调用栈的异步目标共用额度。"""

from dataclasses import dataclass

MAX_ANALYSIS_CALLS = 4096
MAX_ANALYSIS_ITERATIONS = 4096
MAX_ANALYSIS_JUMPS = 4096
MAX_BODY_ITERATIONS = 512
# 7层会截断控制器→坐标/包内实现的正常调用链；资源保护不是源码缺参。
MAX_CALL_DEPTH = 32


def call_limit(estimator, stack, marker, *, metadata=False, callback=False, budget=True):
    if marker in stack:
        return {"kind": "recursion", "target": marker}
    depth = estimator.depth(stack)
    if not metadata and depth >= MAX_CALL_DEPTH:
        return {"kind": "call_depth", "limit": MAX_CALL_DEPTH, "used": depth, "target": marker}
    if (
        not metadata
        and budget
        and estimator.budget.exhausted(None if callback else estimator.calls)
    ):
        return {
            "kind": "call_budget",
            "limit": estimator.budget.limit,
            "used": estimator.budget.used,
            "target": marker,
        }
    return None


@dataclass
class CallBudget:
    limit: int = MAX_ANALYSIS_CALLS
    used: int = 0

    def exhausted(self, ordinary_calls=None):
        return self.used >= self.limit or (
            ordinary_calls is not None and ordinary_calls >= self.limit
        )

    def consume(self):
        self.used += 1


@dataclass
class IterationBudget(CallBudget):
    limit: int = MAX_ANALYSIS_ITERATIONS


@dataclass
class JumpBudget(CallBudget):
    limit: int = MAX_ANALYSIS_JUMPS
