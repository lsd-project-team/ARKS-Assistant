"""枚举表达式只求值一次；数组读取当前元素，List遵守版本失效规则。"""

from contextlib import contextmanager
from dataclasses import replace

from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import text
from app.modules.action_timing.source_loops import (
    MAX_ACTION_ITERATIONS,
    MAX_ITERATIONS,
    ForExecution,
)
from app.modules.action_timing.source_scopes import local_scope, restore


class ForeachExecution(ForExecution):
    @contextmanager
    def iteration(self, variable):
        with local_scope(self.estimator, [text(variable)], self.bindings) as before:
            try:
                yield
            finally:
                for snapshot in [*self.result.states.values(), *self.exits]:
                    restore(snapshot, before)

    def execute(self):
        self.kind = "foreach"
        right = self.node.child_by_field_name("right")
        variable = self.node.child_by_field_name("left")
        self.condition = right  # 仅用于逐项依据标签，foreach本身没有条件表达式。
        self.expression(right)
        data = self.estimator.index.value(right, self.method, self.bindings)
        size = collections.length(data, self.bindings)
        kind = text(self.node.child_by_field_name("type"))
        if kind == "var":
            kind = (
                data.get("<element_type>", "var")
                if collections.known(data)
                else collections.element_type(self.estimator.index, right, self.method)
            )
        # 临时类型使用独立缓存上下文，不修改原方法，也不反复扫描/清空整仓缓存。
        self.method = replace(
            self.method,
            types={**self.method.types, text(variable): kind},
            type_scope=(*self.method.type_scope, (self.node.start_byte, kind)),
        )
        if variable is None or variable.type != "identifier" or size is None:
            with self.iteration(variable):
                state.write(self.estimator.index, variable, self.method, self.bindings, None)
                self.summarize("集合内容或长度未定")
            return self.finish()
        version = collections.version(data, self.bindings)
        for position in range(size):
            current = collections.version(data, self.bindings)
            if data["<collection>"] == "list" and current != version:
                self.estimator.failure_reasons.append("枚举期间集合被修改，不能正常完成")
                break
            if (
                current is None
                or self.count >= MAX_ITERATIONS
                or self.estimator.loop_steps >= MAX_ACTION_ITERATIONS
            ):
                self.estimator.truncated = True
                with self.iteration(variable):
                    state.write(self.estimator.index, variable, self.method, self.bindings, None)
                    self.summarize("集合状态变化或达到枚举展开边界")
                break
            with self.iteration(variable):
                value = collections.item(data, position, self.bindings)
                state.write(self.estimator.index, variable, self.method, self.bindings, value)
                if not self.run_body():
                    break
        else:
            # List最后一次MoveNext也检查版本；只有一个元素时修改仍会失效。
            if (
                data["<collection>"] == "list"
                and collections.version(data, self.bindings) != version
            ):
                self.estimator.failure_reasons.append("枚举期间集合被修改，不能正常完成")
            else:
                self.exit(self.elapsed, self.bindings)
                self.bounded = True
        return self.finish()


def execute_foreach(estimator, node, method, bindings, stack, conditions, background):
    return ForeachExecution(
        estimator, node, method, bindings, stack, conditions, background
    ).execute()
