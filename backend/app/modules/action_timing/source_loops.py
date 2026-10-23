"""按for的实际执行顺序展开；无法确定的剩余迭代保留未知上界。"""

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost, Flow, add, choice
from app.modules.action_timing.source_index import children, initializer, text, walk
from app.modules.action_timing.source_loop_bounds import pure_loop
from app.modules.action_timing.source_numbers import INTEGER_RANGES
from app.modules.action_timing.source_scopes import inline_names, local_scope, restore
from app.modules.action_timing.source_tasks import CLOCK, track_binding

MAX_ITERATIONS = 128


def fields(node, name):
    return [part for i, part in enumerate(node.children) if node.field_name_for_child(i) == name]


class ForExecution:
    def __init__(self, estimator, node, method, bindings, stack, conditions, background):
        self.estimator, self.node, self.method = estimator, node, method
        self.bindings, self.stack = bindings, stack
        self.conditions, self.background = conditions, background
        self.started = bindings.get(CLOCK, ZERO)
        self.elapsed = ZERO
        self.test_cost = ZERO
        self.result = Flow(None, None)
        self.exits = []
        self.count = 0
        self.each = None
        self.bounded = False
        self.exact = True
        self.analytical = False
        self.no_normal_exit = False
        self.body = node.child_by_field_name("body")
        self.condition = node.child_by_field_name("condition")
        self.updates = fields(node, "update")
        self.kind = {"while_statement": "while", "do_statement": "do"}.get(node.type, "for")

    def expression(self, node):
        self.bindings[CLOCK] = self.started.plus(self.elapsed)
        cost = self.estimator.expression(
            node, self.method, self.bindings, self.stack, self.conditions, self.background
        )
        self.elapsed = self.elapsed.plus(cost)
        return cost

    def initialize(self):
        for node in fields(self.node, "initializer"):
            if node.type != "variable_declaration":
                self.expression(node)
                continue
            for declaration in children(node, "variable_declarator"):
                name = declaration.child_by_field_name("name")
                value_node = initializer(declaration)
                self.expression(value_node)
                value = self.estimator.index.value(value_node, self.method, self.bindings)
                if text(node.child_by_field_name("type")) in {"double", "float", "decimal"}:
                    value = float(value) if isinstance(value, (int, float)) else None
                state.write(self.estimator.index, name, self.method, self.bindings, value)
                track_binding(self.estimator.index, name, value_node, self.method, self.bindings)

    def body_flow(self, suffix):
        self.bindings[CLOCK] = self.started.plus(self.elapsed)
        return self.estimator.block(
            self.body,
            self.method,
            self.bindings,
            self.stack,
            (*self.conditions, suffix),
            self.background,
        )

    def exit(self, cost, bindings):
        self.result.live = choice(self.result.live, cost)
        if cost is not None:
            self.exits.append(dict(bindings))

    def returns(self, flow, prefix):
        returned = Flow(
            None,
            add(prefix, flow.returned),
            states={
                name: value
                for name, value in flow.states.items()
                if name == "returned" or name in flow.jumps
            },
            jumps={key: add(prefix, cost) for key, cost in flow.jumps.items()},
        )
        self.result = self.result.merge(returned)

    def summarize(self, reason):
        """剩余循环可能不执行，也可能多次执行；只展开一份条件样本追踪写入。"""
        original = dict(self.bindings)
        self.exact = False
        stage_start = len(self.estimator.stages)
        flow = self.body_flow(f"剩余循环未定：{reason}")
        can_repeat = flow.live is not None or flow.continued is not None
        if can_repeat:
            for stage in self.estimator.stages[stage_start:]:
                stage["repeat"] = True
        possible = [original]
        sample = choice(flow.broken, flow.returned)
        continuing = []
        if flow.live is not None:
            continuing.append(dict(self.bindings))
        if flow.continued is not None:
            continuing.append(flow.states.get("continued", dict(self.bindings)))
        if continuing:
            state.merge(self.bindings, continuing)
            before = self.elapsed
            self.elapsed = before.plus(choice(flow.live, flow.continued))
            for update in self.updates:
                self.expression(update)
            sample = choice(
                sample,
                Cost(
                    max(0, self.elapsed.lower - before.lower),
                    None
                    if self.elapsed.upper is None or before.upper is None
                    else max(0, self.elapsed.upper - before.upper),
                ),
            )
            self.elapsed = before
            possible.append(dict(self.bindings))
        sample = sample or ZERO
        self.each = choice(self.each, sample)
        possible.extend(flow.states.values())
        state.merge(self.bindings, possible)
        # 未知次数后的状态不沿用单轮更新结果。
        state.transfer(self.bindings, possible[-1], uncertain=True, locals=True)
        repeating_time = sample != ZERO or self.test_cost != ZERO
        tail = UNKNOWN if can_repeat and repeating_time else ZERO
        if not can_repeat:
            tail = choice(ZERO, flow.broken) if flow.broken is not None else ZERO
            self.bounded = True
        self.exit(self.elapsed.plus(tail), self.bindings)
        for target, cost in flow.jumps.items():
            duration = Cost(cost.lower, None) if can_repeat and repeating_time else cost
            outgoing = Flow(None, None, jumps={target: self.elapsed.plus(duration)})
            outgoing.with_state(target, flow.states.get(target, self.bindings))
            self.result = self.result.merge(outgoing)
        if flow.returned is not None:
            returned = Cost(flow.returned.lower, None) if can_repeat else flow.returned
            self.result.returned = choice(self.result.returned, self.elapsed.plus(returned))
            self.result.states = self.result.merge_states(flow)

    def check_integer_range(self, nodes=None):
        for update in self.updates if nodes is None else nodes:
            for part in walk(update):
                left = (
                    part.child_by_field_name("left")
                    if part.type == "assignment_expression"
                    else (
                        children(part)[-1]
                        if part.type in {"prefix_unary_expression", "postfix_unary_expression"}
                        and children(part)
                        else None
                    )
                )
                if left is None:
                    continue
                limits = INTEGER_RANGES.get(self.estimator.index.infer(left, self.method))
                value = self.estimator.index.value(left, self.method, self.bindings)
                if limits and isinstance(value, int) and not limits[0] <= value <= limits[1]:
                    state.write(self.estimator.index, left, self.method, self.bindings, None)
                    self.estimator.record(
                        "unresolved",
                        "循环变量整数溢出，未按Python整数证明终止",
                        update,
                        self.method,
                        self.conditions,
                        self.background,
                    )

    def execute(self):
        self.initialize()
        plan = pure_loop(self.estimator, self.node, self.method, self.bindings, MAX_ITERATIONS)
        if plan is not None:
            start = len(self.estimator.stages)
            self.body_flow(f"固定整数循环{plan.count}轮，延时正文已逐值求和")
            delays = [row for row in self.estimator.stages[start:] if row["kind"] == "delay"]
            for row, stats in zip(delays, plan.sleeps, strict=True):
                row.update(
                    repeat=True,
                    repetitions=plan.count,
                    total_delay_ms=stats["sum"],
                    milliseconds=stats["min"] if stats["min"] == stats["max"] else None,
                    per_iteration_min_ms=stats["min"],
                    per_iteration_max_ms=stats["max"],
                )
            state.write(
                self.estimator.index, plan.variable, self.method, self.bindings, plan.final_value
            )
            self.count, self.each, self.bounded = plan.count, plan.each, True
            self.analytical = True
            self.exit(self.elapsed.plus(plan.cost), self.bindings)
            return self.finish()
        while True:
            self.test_cost = self.expression(self.condition)
            value = (
                True
                if self.condition is None
                else self.estimator.index.value(self.condition, self.method, self.bindings)
            )
            if value is False:
                self.exit(self.elapsed, self.bindings)
                self.bounded = True
                break
            if value is not True:
                self.summarize("条件或次数由运行数据决定")
                break
            if self.count >= MAX_ITERATIONS or self.estimator.loop_limit_reached():
                self.estimator.truncated = True
                self.summarize("达到迭代展开边界")
                break
            if not self.run_body():
                break
            if self.reject_constant_true_loop():
                break
            for update in self.updates:
                self.expression(update)
            self.check_integer_range()
        return self.finish()

    def run_body(self):
        self.estimator.consume_loop_step()
        flow = self.body_flow(f"{self.kind}第{self.count + 1}轮：{text(self.condition) or 'true'}")
        self.last_flow = flow
        self.count += 1
        self.each = choice(self.each, flow.cost())
        self.returns(flow, self.elapsed)
        if flow.broken is not None:
            self.exit(add(self.elapsed, flow.broken), flow.states.get("broken", self.bindings))
        continuing = choice(flow.live, flow.continued)
        if continuing is None:
            self.bounded = True
            return False
        contexts = []
        if flow.live is not None:
            contexts.append(dict(self.bindings))
        if flow.continued is not None:
            contexts.append(flow.states.get("continued", dict(self.bindings)))
        state.merge(self.bindings, contexts)
        self.elapsed = self.elapsed.plus(continuing)
        return True

    def reject_constant_true_loop(self):
        always = self.condition is None or text(self.condition).strip() == "true"
        exits = {"break_statement", "return_statement", "goto_statement", "yield_statement"}
        if not always or any(part.type in exits for part in walk(self.body)):
            return False
        # 真常量条件没有正常退出语句，正常完成路径为空；异常/终止线程不作正常耗时。
        self.no_normal_exit = True
        self.exact = False
        self.result = Flow(None, None)
        self.exits.clear()
        self.estimator.failure_reasons.append("循环条件恒真且没有正常退出语句")
        return True

    def finish(self):
        if self.exits:
            state.merge(self.bindings, self.exits)
        self.bindings[CLOCK] = self.started
        self.estimator.record(
            "loop",
            "循环没有正常退出路径"
            if self.no_normal_exit
            else (
                f"{self.kind}已展开{self.count}轮" if self.bounded else f"{self.kind}剩余次数未定"
            ),
            self.node,
            self.method,
            self.conditions,
            self.background,
            iterations=self.count if self.bounded and self.exact else None,
            expanded_iterations=1 if self.analytical else self.count,
            analytical=self.analytical,
            bounded=self.bounded,
            no_normal_exit=self.no_normal_exit,
            per_iteration_min_ms=self.each.lower if self.each else 0,
            per_iteration_max_ms=self.each.upper if self.each else 0,
        )
        self.estimator._timeouts(self.node, self.method, self.conditions, self.background)
        self.result.states = {
            channel: context
            for channel, context in self.result.states.items()
            if channel == "returned" or channel in self.result.jumps
        }
        return self.result


def execute_for(estimator, node, method, bindings, stack, conditions, background):
    names = [
        text(part.child_by_field_name("name"))
        for declaration in fields(node, "initializer")
        if declaration.type == "variable_declaration"
        for part in children(declaration, "variable_declarator")
        if part.child_by_field_name("name") is not None
    ]
    with local_scope(estimator, names + inline_names(node, estimator.index), bindings) as before:
        flow = ForExecution(
            estimator, node, method, bindings, stack, conditions, background
        ).execute()
        for snapshot in flow.states.values():
            restore(snapshot, before)
        return flow
