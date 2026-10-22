"""Task 的源代码时间线：发起与等待分开，已并行经过的时间不重复相加。"""

import math
from dataclasses import dataclass

from app.modules.action_timing import source_delegates as delegates
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


@dataclass(frozen=True)
class DeferredTask:
    delegate: object
    method_key: str
    frame: str | None
    supported: bool

    def remaining(self, clock):
        return UNKNOWN


@dataclass(frozen=True)
class TaskGroup:
    tasks: tuple

    def remaining(self, clock):
        return UNKNOWN


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
                return not children(parent.child_by_field_name("arguments"), "argument")
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
        parts = children(node)
        return lookup(parts[-1], method, bindings) if parts else None
    if node.type in {"parenthesized_expression", "cast_expression"}:
        operand = node.child_by_field_name("value") or next(iter(children(node)), None)
        return lookup(operand, method, bindings)
    if node.type in {"identifier", "member_access_expression"}:
        return bindings.get(f"<task-variable:{text(node)}>")
    return bindings.get(task_key(node, method))


def task_group(node, method, bindings):
    if node is None:
        return None
    direct = lookup(node, method, bindings)
    if isinstance(direct, TaskGroup):
        return direct
    if isinstance(direct, (TaskPlan, DeferredTask)):
        return TaskGroup((direct,))
    if node.type == "argument":
        parts = children(node)
        return task_group(parts[-1], method, bindings) if parts else None
    if node.type not in {"array_creation_expression", "implicit_array_creation_expression"}:
        return None
    initializer = next(iter(children(node, "initializer_expression")), None)
    if initializer is None:
        return None
    # 每个元素都必须有去向；不能扫描到一个已知任务就忽略其他未知成员。
    return TaskGroup(tuple(lookup(item, method, bindings) for item in children(initializer)))


def track_binding(index, left, right, method, bindings):
    if left is None:
        return
    if left.type in {"tuple_pattern", "tuple_expression"}:
        # 解构没有单一变量名；返回任务尚未绑定时，逐个使旧任务/委托失效。
        for part in walk(left):
            if part.type == "identifier":
                track_binding(index, part, None, method, bindings)
        return
    if left.type == "element_access_expression":
        # 数组别名及索引改写尚未完整建模，不能继续沿用改写前的任务组。
        for key, value in list(bindings.items()):
            if isinstance(value, TaskGroup):
                bindings[key] = None
        return
    name = text(left)
    task = lookup(right, method, bindings) or task_group(right, method, bindings)
    key = f"<task-variable:{name}>"
    if task is not None or key in bindings:
        bindings[key] = task
    delegate = delegates.capture(index, right, method, bindings)
    key = f"{delegates.DELEGATE_PREFIX}{name}>"
    if delegate is not None or key in bindings:
        bindings[key] = (method.key, delegate) if delegate is not None else None


def framework_task(index, owner, method):
    if owner == "Task" and (owner in method.types or index.member_type(method.owner, owner)):
        return False
    kind = index.lookup_type(owner, method)
    return kind not in index.classes and kind in {"Task", "System.Threading.Tasks.Task"}


def create_task(estimator, node, method, bindings):
    if not framework_task(estimator.index, text(node.child_by_field_name("type")), method):
        return False
    args = children(node.child_by_field_name("arguments"), "argument")
    definition = DeferredTask(
        delegates.capture(estimator.index, args[0], method, bindings) if args else None,
        method.key,
        bindings.get(state.FRAME),
        len(args) == 1,
    )
    bindings[task_key(node, method)] = definition
    return True


def run_delegate(
    estimator, delegate, method, bindings, stack, conditions, background, waiting, join_result=True
):
    task_bindings = dict(bindings)
    duration = delegates.execute(
        estimator,
        delegate,
        method,
        task_bindings,
        stack,
        conditions,
        background or not waiting,
        join_result=join_result,
    )
    state.transfer(
        bindings,
        task_bindings,
        uncertain=not waiting or (not join_result and duration.upper is None),
        locals=True,
    )
    return duration


def handle_tasks(estimator, node, method, bindings, stack, conditions, background):
    function = node.child_by_field_name("function")
    full_name = text(function).removeprefix("System.Threading.Tasks.")
    name = full_name.split(".")[-1]
    args = children(node.child_by_field_name("arguments"), "argument")
    waiting = consumed(node)
    task_owner = full_name.rsplit(".", 1)[0].removesuffix(".Factory")
    original_owner = text(function).rsplit(".", 1)[0].removesuffix(".Factory")
    if task_owner == "Task" and not framework_task(estimator.index, original_owner, method):
        return None
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
        supported = len(args) == 1 or (
            full_name == "Task.Factory.StartNew"
            and len(args) == 2
            and text(args[1]).startswith("TaskCreationOptions.")
        )
        duration = run_delegate(
            estimator,
            args[0] if args else None,
            method,
            bindings,
            stack,
            conditions,
            background,
            waiting and supported,
            join_result=full_name == "Task.Run",
        )
        if not supported:
            duration = UNKNOWN
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
    if name in {"Start", "RunSynchronously"} and isinstance(receiver_plan, DeferredTask):
        synchronous = name == "RunSynchronously"
        duration = UNKNOWN
        if (
            receiver_plan.supported
            and receiver_plan.method_key == method.key
            and receiver_plan.frame == bindings.get(state.FRAME)
            and not args
        ):
            duration = run_delegate(
                estimator,
                receiver_plan.delegate,
                method,
                bindings,
                stack,
                conditions,
                background,
                synchronous,
                join_result=False,
            )
        plan = TaskPlan(bindings.get(CLOCK, ZERO), duration)
        for key, value in list(bindings.items()):
            if value is receiver_plan:
                bindings[key] = plan
            elif isinstance(value, TaskGroup) and any(
                item is receiver_plan for item in value.tasks
            ):
                bindings[key] = TaskGroup(
                    tuple(plan if item is receiver_plan else item for item in value.tasks)
                )
        estimator.record(
            "wait" if synchronous else "background",
            "同步执行已创建任务" if synchronous else "启动已创建任务",
            node,
            method,
            conditions,
            background or not synchronous,
            resolved=duration.upper is not None,
            milliseconds=duration.lower if duration.lower == duration.upper else None,
        )
        return duration if synchronous else ZERO
    if name in {"ConfigureAwait", "GetAwaiter"} and receiver_plan:
        bindings[task_key(node, method)] = receiver_plan
        charged = bindings.get(task_key(receiver, method) + ":charged", False)
        bindings[task_key(node, method) + ":charged"] = charged or waiting
        if not waiting:
            return ZERO
        return ZERO if charged else receiver_plan.remaining(bindings.get(CLOCK, ZERO))
    if name in {"Wait", "GetResult"} and (
        receiver_plan or f"<task-variable:{text(receiver)}>" in bindings
    ):
        # 内联 Delay/Run 已在接收者求值时计入；变量任务只等待尚未完成的部分。
        cost = (
            UNKNOWN
            if args
            else (
                ZERO
                if bindings.get(task_key(receiver, method) + ":charged", False)
                else receiver_plan.remaining(bindings.get(CLOCK, ZERO))
                if receiver_plan
                else UNKNOWN
            )
        )
    elif full_name in {"Task.WaitAll", "Task.WaitAny", "Task.WhenAll", "Task.WhenAny"}:
        groups = [task_group(argument, method, bindings) for argument in args]
        plans = [plan for group in groups if group for plan in group.tasks]
        costs = [plan.remaining(bindings.get(CLOCK, ZERO)) for plan in plans if plan]
        if (
            not groups
            or any(group is None for group in groups)
            or any(plan is None for plan in plans)
        ):
            cost = UNKNOWN
        elif not plans:
            cost = UNKNOWN if name in {"WaitAny", "WhenAny"} else ZERO
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
