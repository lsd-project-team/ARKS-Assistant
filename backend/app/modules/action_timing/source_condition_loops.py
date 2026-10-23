"""while先测条件，do先执行正文；break和return都不再执行尾部条件。"""

from dataclasses import replace

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_delay_reachability import possible as delay_possible
from app.modules.action_timing.source_loops import (
    MAX_ITERATIONS,
    ForExecution,
)
from app.modules.action_timing.source_scopes import inline_names, local_scope, restore


class ConditionExecution(ForExecution):
    def execute(self):
        post_test = self.node.type == "do_statement"
        previous = None
        while True:
            if not post_test or self.count:
                self.test_cost = self.expression(self.condition)
                value = self.estimator.index.value(self.condition, self.method, self.bindings)
                if value is False:
                    self.exit(self.elapsed, self.bindings)
                    self.bounded = True
                    break
                if value is not True:
                    self.summarize("条件或信号由运行状态决定")
                    break
                current = {
                    name: value
                    for name, value in self.bindings.items()
                    if not name.startswith("<")
                    or name.startswith((state.PREFIX, state.LOCAL_PREFIX, state.COLLECTION_PREFIX))
                }
                if current == previous:
                    # 状态不变的条件退出循环可能反复等待信号。合并剩余次数，
                    # 不把相同未知状态展开128次，也不据此证明一定无限循环。
                    self.summarize("循环状态重复，后续退出次数未定")
                    break
                previous = current
            if self.count >= MAX_ITERATIONS or self.estimator.loop_limit_reached():
                self.estimator.truncated = True
                self.summarize("达到迭代展开边界")
                break
            if not self.run_body():
                break
            if self.reject_constant_true_loop():
                break
            if self.last_flow.broken is not None and not delay_possible(
                self.estimator.index, replace(self.method, body_override=self.node)
            ):
                # 未定父链/列表退出可能改变数据，但没有可识别的停留路径。
                # 合并数据状态即可；不任意展开128个父节点耗尽动作调用预算。
                self.summarize("无可识别停留的条件退出循环，次数未定")
                break
            self.check_integer_range([self.body])
        return self.finish()


def execute_condition_loop(estimator, node, method, bindings, stack, conditions, background):
    with local_scope(estimator, inline_names(node, estimator.index), bindings) as before:
        flow = ConditionExecution(
            estimator, node, method, bindings, stack, conditions, background
        ).execute()
        for snapshot in flow.states.values():
            restore(snapshot, before)
        return flow
