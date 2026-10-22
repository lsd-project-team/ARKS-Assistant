"""Task 的源代码时间线：发起与等待分开，已并行经过的时间不重复相加。"""

import math
from dataclasses import dataclass

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost
from app.modules.action_timing.source_index import children, text, walk

CLOCK = "<simulation-clock>"


@dataclass(frozen=True)
class TaskPlan:
    start: Cost
    duration: Cost

    def remaining(self, clock):
        end = self.start.plus(self.duration)
        return Cost(
            max(0, end.lower - clock.upper) if clock.upper is not None else 0,
            None if end.upper is None else max(0, end.upper - clock.lower),
        )


def task_key(node, method):
    return f"<task:{method.unit.path}:{node.start_byte}>"


def consumed(node):
    parent = node.parent
    while parent and parent.type not in {
        "argument",
        "expression_statement",
        "variable_declarator",
        "return_statement",
    }:
        if parent.type == "await_expression":
            return True
        if parent.type == "invocation_expression":
            name = text(parent.child_by_field_name("function")).split(".")[-1]
            if name in {"Wait", "GetResult"}:
                return True
            if name not in {"GetAwaiter", "ConfigureAwait"}:
                return False
        parent = parent.parent
    return False


def remember(node, method, bindings, duration):
    plan = TaskPlan(bindings.get(CLOCK, ZERO), duration)
    bindings[task_key(node, method)] = plan
    parent = node.parent
    # ConfigureAwait 等调用不改变任务归属；不跨过其他函数实参去误认外层变量。
    while parent and parent.type not in {
        "argument",
        "expression_statement",
        "return_statement",
        "variable_declarator",
        "assignment_expression",
    }:
        parent = parent.parent
    if parent and parent.type in {"variable_declarator", "assignment_expression"}:
        name = text(parent.child_by_field_name("name") or parent.child_by_field_name("left"))
        bindings[f"<task-variable:{name}>"] = plan
    return plan


def lookup(node, method, bindings):
    if node is None:
        return None
    if node.type == "argument":
        return lookup(children(node)[-1], method, bindings)
    if node.type in {"identifier", "member_access_expression"}:
        return bindings.get(f"<task-variable:{text(node)}>")
    return bindings.get(task_key(node, method))


def handle_tasks(estimator, node, method, bindings, stack, conditions, background):
    function = node.child_by_field_name("function")
    full_name = text(function).removeprefix("System.Threading.Tasks.")
    name = full_name.split(".")[-1]
    args = children(node.child_by_field_name("arguments"), "argument")
    waiting = consumed(node)
    if full_name == "Task.Delay":
        value = estimator.index.value(args[0], method, bindings) if args else None
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value >= 0
        )
        duration = Cost(value, value) if valid else UNKNOWN
        remember(node, method, bindings, duration)
        bindings[task_key(node, method) + ":charged"] = waiting
        estimator.record(
            "delay",
            "异步延时" if waiting else "后台延时",
            node,
            method,
            conditions,
            background or not waiting,
            milliseconds=value if valid else None,
        )
        return duration if waiting else ZERO
    if full_name in {"Task.Run", "Task.Factory.StartNew"}:
        start = len(estimator.stages)
        duration = UNKNOWN
        for argument in args:
            delegate = next(
                (
                    part
                    for part in children(argument)
                    if part.type in {"lambda_expression", "anonymous_method_expression"}
                ),
                None,
            )
            if delegate:
                task_bindings = dict(bindings)
                body = delegate.child_by_field_name("body")
                if body and body.type != "block":
                    duration = estimator.expression(
                        body, method, task_bindings, stack, conditions, background or not waiting
                    )
                else:
                    flow = estimator.block(
                        body, method, task_bindings, stack, conditions, background or not waiting
                    )
                    duration = flow.cost()
                    if flow.live is None and flow.returned is None:
                        duration = UNKNOWN
                state.transfer(bindings, task_bindings, uncertain=not waiting, locals=True)
                break
        if any(
            row["kind"] in {"motion", "wait", "call", "unresolved"} and not row.get("resolved")
            for row in estimator.stages[start:]
        ):
            duration = Cost(duration.lower, None)
        remember(node, method, bindings, duration)
        bindings[task_key(node, method) + ":charged"] = waiting
        estimator.record(
            "wait" if waiting else "background",
            "等待委托完成" if waiting else "后台分支，等待时按完成边界计算",
            node,
            method,
            conditions,
            background or not waiting,
            resolved=duration.upper is not None,
            milliseconds=duration.lower if duration.lower == duration.upper else None,
        )
        return duration if waiting else ZERO
    receiver = function.child_by_field_name("expression")
    receiver_plan = lookup(receiver, method, bindings)
    if name in {"ConfigureAwait", "GetAwaiter"} and receiver_plan:
        bindings[task_key(node, method)] = receiver_plan
        charged = bindings.get(task_key(receiver, method) + ":charged", False)
        bindings[task_key(node, method) + ":charged"] = charged or waiting
        if not waiting:
            return ZERO
        return ZERO if charged else receiver_plan.remaining(bindings.get(CLOCK, ZERO))
    if name in {"Wait", "GetResult"} and receiver_plan:
        # 内联 Delay/Run 已在接收者求值时计入；变量任务只等待尚未完成的部分。
        cost = (
            ZERO
            if bindings.get(task_key(receiver, method) + ":charged", False)
            else (receiver_plan.remaining(bindings.get(CLOCK, ZERO)))
        )
    elif full_name in {"Task.WaitAll", "Task.WaitAny", "Task.WhenAll", "Task.WhenAny"}:
        plans = []
        for argument in args:
            direct = lookup(argument, method, bindings)
            if direct:
                plans.append(direct)
            else:
                plans.extend(
                    plan
                    for item in walk(argument)
                    if item.type == "identifier" and (plan := lookup(item, method, bindings))
                )
        # 数组变量、取消、带 timeout 的重载未绑定时不猜等待边界。
        costs = [plan.remaining(bindings.get(CLOCK, ZERO)) for plan in plans]
        if not costs or (len(args) != len(plans) and not any("new" in text(arg) for arg in args)):
            cost = UNKNOWN
        elif name in {"WaitAny", "WhenAny"}:
            uppers = [cost.upper for cost in costs if cost.upper is not None]
            cost = Cost(min(cost.lower for cost in costs), min(uppers) if uppers else None)
        else:
            cost = Cost(
                max(cost.lower for cost in costs),
                None
                if any(cost.upper is None for cost in costs)
                else max(cost.upper for cost in costs),
            )
        if name.startswith("When") and not waiting:
            remember(node, method, bindings, cost)
            return ZERO
    else:
        return None
    estimator.record(
        "wait",
        "等待并行任务的完成边界",
        node,
        method,
        conditions,
        background,
        resolved=cost.upper is not None,
        milliseconds=cost.lower if cost.lower == cost.upper else None,
        note="按任务发起时刻及已经过的时间计算，不把并行任务依次相加",
    )
    return cost
