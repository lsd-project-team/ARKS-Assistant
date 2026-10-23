"""保护单动作分析资源；复制的并行分支和重置调用栈的异步目标共用额度。"""

from dataclasses import dataclass

MAX_ANALYSIS_CALLS = 4096
MAX_ANALYSIS_ITERATIONS = 4096
MAX_ANALYSIS_JUMPS = 4096
MAX_BODY_ITERATIONS = 512


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
