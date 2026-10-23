"""Task 的源代码时间线：发起与等待分开，已并行经过的时间不重复相加。"""

import math
from dataclasses import dataclass, field, replace

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost, choice
from app.modules.action_timing.source_index import children, text, walk

CLOCK = "<simulation-clock>"
CREATION_ONLY = "<task-creation-only>"


@dataclass(frozen=True)
class TaskPlan:
    start: Cost
    duration: Cost
    result: object = None
    effects: tuple = ()
    stage_ids: tuple = field(default=(), compare=False, repr=False)
    origin_ids: tuple = field(default=(), compare=False, repr=False)
    result_is_fresh: bool = field(default=False, compare=False, repr=False)

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
    # 后缀链的起点相同：outer、outer.Result和outer.Result.Wait不能共用已计时标记。
    return f"<task:{method.unit.path}:{node.type}:{node.start_byte}:{node.end_byte}>"


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


def remember_plan(node, method, bindings, plan, fresh=False):
    bindings[task_key(node, method)] = plan
    bindings[task_key(node, method) + ":fresh"] = fresh
    bindings[call_args.return_key(node, method, bindings)] = plan
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


def remember(node, method, bindings, duration, result=None, effects=(), stage_ids=()):
    return remember_plan(
        node,
        method,
        bindings,
        TaskPlan(bindings.get(CLOCK, ZERO), duration, result, effects, stage_ids),
        fresh=True,
    )


def known_task(value):
    return isinstance(value, (TaskPlan, DeferredTask, TaskGroup))


def join_stages(estimator, plan, background):
    """完成边界所等待的阶段归入当前动作；未join的子任务仍留在后台。"""
    if background or not isinstance(plan, TaskPlan):
        return
    covered = set(plan.stage_ids)
    for stage in estimator.stages:
        if id(stage) in covered:
            stage["background"] = False


def task_ids(values, depth=0):
    """返回前已存在的任务不算新发起，join时不能重放它的历史写入。"""
    if depth > 16:
        return set()
    found = set()
    for value in values:
        if known_task(value):
            found.add(id(value))
            found.update(getattr(value, "origin_ids", ()))
        if isinstance(value, dict):
            found.update(task_ids(value.values(), depth + 1))
        elif isinstance(value, (tuple, list)):
            found.update(task_ids(value, depth + 1))
        elif isinstance(value, TaskGroup):
            found.update(task_ids(value.tasks, depth + 1))
    return found


def is_fresh(value, previous):
    return (
        known_task(value)
        and id(value) not in previous
        and not (set(getattr(value, "origin_ids", ())) & previous)
    )


def public_value(value, depth=0):
    from app.modules.action_timing.source_apm import AsyncInvocation

    if (
        known_task(value)
        or isinstance(value, AsyncInvocation)
        or isinstance(value, delegates.BoundDelegate)
        or value is delegates.NULL_DELEGATE
        or depth > 16
    ):
        return None
    if isinstance(value, dict):
        return {key: public_value(part, depth + 1) for key, part in value.items()}
    if isinstance(value, (list, tuple)):
        return [public_value(part, depth + 1) for part in value]
    return value


def merge_plans(values):
    if not all(isinstance(value, TaskPlan) for value in values):
        return None
    if all(value is values[0] for value in values):
        return values[0]
    stages = tuple(dict.fromkeys(stage for value in values for stage in value.stage_ids))
    origins = tuple(
        dict.fromkeys(origin for value in values for origin in (id(value), *value.origin_ids))
    )
    if all(value == values[0] for value in values):
        return replace(
            values[0],
            stage_ids=stages,
            origin_ids=origins,
            result_is_fresh=all(value.result_is_fresh for value in values),
        )
    end = None
    for value in values:
        end = choice(end, value.start.plus(value.duration))
    first = values[0].result
    result = (
        first
        if all(type(value.result) is type(first) and value.result == first for value in values)
        else None
    )
    return TaskPlan(
        ZERO,
        end or UNKNOWN,
        result,
        stage_ids=stages,
        origin_ids=origins,
    )


def lookup(node, method, bindings, index=None):
    if node is None:
        return None
    if node.type == "argument":
        parts = children(node)
        return lookup(parts[-1], method, bindings, index) if parts else None
    if node.type in {"parenthesized_expression", "cast_expression"}:
        operand = node.child_by_field_name("value") or next(iter(children(node)), None)
        return lookup(operand, method, bindings, index)
    if index is not None:
        if state.is_unstable(index, node, method, bindings):
            return None
        value = index.value(node, method, bindings)
        if known_task(value):
            return value
    if node.type in {"identifier", "member_access_expression"}:
        value = bindings.get(text(node))
        return (
            value
            if known_task(value)
            else bindings.get(f"<task-variable:{text(node)}>")
            or bindings.get(task_key(node, method))
        )
    return bindings.get(task_key(node, method))


def task_group(node, method, bindings, index=None):
    if node is None:
        return None
    direct = lookup(node, method, bindings, index)
    if isinstance(direct, TaskGroup):
        return direct
    if isinstance(direct, (TaskPlan, DeferredTask)):
        return TaskGroup((direct,))
    if node.type == "argument":
        parts = children(node)
        return task_group(parts[-1], method, bindings, index) if parts else None
    if index is not None:
        from app.modules.action_timing import source_collections as collections

        value = index.value(node, method, bindings)
        size = collections.length(value, bindings)
        if size is not None and size <= 256:
            return TaskGroup(tuple(collections.item(value, i, bindings) for i in range(size)))
    if node.type not in {"array_creation_expression", "implicit_array_creation_expression"}:
        return None
    initializer = next(iter(children(node, "initializer_expression")), None)
    if initializer is None:
        return None
    # 每个元素都必须有去向；不能扫描到一个已知任务就忽略其他未知成员。
    return TaskGroup(tuple(lookup(item, method, bindings, index) for item in children(initializer)))


def track_binding(index, left, right, method, bindings):
    if left is None:
        return
    if left.type in {"tuple_pattern", "tuple_expression"}:
        # 解构没有单一变量名；返回任务尚未绑定时，逐个使旧任务/委托失效。
        for part in walk(left):
            if part.type == "identifier":
                state.write(index, part, method, bindings, None)
                track_binding(index, part, None, method, bindings)
        return
    if left.type == "element_access_expression":
        # 数组别名及索引改写尚未完整建模，不能继续沿用改写前的任务组。
        for key, value in list(bindings.items()):
            if isinstance(value, TaskGroup):
                bindings[key] = None
        return
    name = text(left)
    task = lookup(right, method, bindings, index) or task_group(right, method, bindings, index)
    key = f"<task-variable:{name}>"
    if task is not None or key in bindings:
        bindings[key] = task
    from app.modules.action_timing.source_collections import raw_type

    kind = raw_type(index, left, method)
    arity = delegates.signature_arity(kind)
    delegate = delegates.capture(
        index,
        right,
        method,
        bindings,
        arity or 0,
        returns_task=None
        if arity is None
        else "Task" in kind and kind.replace("System.", "").startswith("Func<"),
        discards_result=kind.replace("System.", "").split("<", 1)[0] == "Action",
        signature_kind=kind,
    )
    key = f"{delegates.DELEGATE_PREFIX}{name}>"
    if delegate is not None or key in bindings:
        bindings[key] = (method.key, delegate) if delegate is not None else None
    if isinstance(delegate, delegates.BoundDelegate) or delegate is delegates.NULL_DELEGATE:
        state.write(index, left, method, bindings, delegate)


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
        delegates.capture(
            estimator.index, args[0], method, bindings, returns_task=False, discards_result=True
        )
        if args
        else None,
        method.key,
        bindings.get(state.FRAME),
        len(args) == 1,
    )
    remember_plan(node, method, bindings, definition, fresh=True)
    return True


def run_delegate(
    estimator, delegate, method, bindings, stack, conditions, background, waiting, join_result=True
):
    from app.modules.action_timing.source_private_state import activate, remember

    if not waiting:
        delegate = delegates.capture(estimator.index, delegate, method, bindings)
        activity = remember(bindings, delegate)
    task_bindings = dict(bindings)
    if not waiting:
        activate(estimator.index, task_bindings, activity)
    previous_tasks = task_ids(task_bindings.values())
    stage_start = len(estimator.stages)
    duration = delegates.execute(
        estimator,
        delegate,
        method,
        task_bindings,
        stack,
        conditions,
        False,
        join_result=join_result,
    )
    stage_ids = tuple(
        id(stage) for stage in estimator.stages[stage_start:] if not stage["background"]
    )
    if background or not waiting:
        for stage in estimator.stages[stage_start:]:
            stage["background"] = True
    effects = tuple(
        (key, value)
        for key, value in state.context(task_bindings).items()
        if key not in {state.PRIVATE_PENDING, state.PRIVATE_ACTIVE, state.LOCAL_FUNCTIONS}
        and (key not in bindings or value != bindings[key])
    )
    state.transfer(
        bindings,
        task_bindings,
        uncertain=not waiting or (not join_result and duration.upper is None),
        locals=True,
    )
    return TaskPlan(
        bindings.get(CLOCK, ZERO),
        duration,
        task_bindings.get(delegates.RESULT),
        effects,
        stage_ids,
        result_is_fresh=is_fresh(task_bindings.get(delegates.RESULT), previous_tasks),
    )


def handle_tasks(estimator, node, method, bindings, stack, conditions, background):
    function = node.child_by_field_name("function")
    full_name = text(function).removeprefix("System.Threading.Tasks.")
    name = full_name.split(".")[-1]
    args = children(node.child_by_field_name("arguments"), "argument")
    waiting = consumed(node) and not bindings.get(CREATION_ONLY)
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
        estimator.record(
            "delay",
            "异步延时" if waiting else "后台延时",
            node,
            method,
            conditions,
            background or not waiting,
            milliseconds=value if valid else None,
        )
        remember(node, method, bindings, duration, stage_ids=(id(estimator.stages[-1]),))
        bindings[task_key(node, method) + ":charged"] = waiting
        return duration if waiting else ZERO
    if full_name.split("<", 1)[0] == "Task.FromResult" and len(args) == 1:
        remember(node, method, bindings, ZERO, estimator.index.value(args[0], method, bindings))
        return ZERO
    if full_name in {"Task.Run", "Task.Factory.StartNew"}:
        supported = len(args) == 1 or (
            full_name == "Task.Factory.StartNew"
            and len(args) == 2
            and text(args[1]).startswith("TaskCreationOptions.")
        )
        plan = run_delegate(
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
            plan = TaskPlan(plan.start, UNKNOWN, stage_ids=plan.stage_ids)
        duration = plan.duration
        remember_plan(node, method, bindings, plan, fresh=True)
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
    receiver_plan = lookup(receiver, method, bindings, estimator.index)
    if (
        name == "Unwrap"
        and isinstance(receiver_plan, TaskPlan)
        and isinstance(receiver_plan.result, TaskPlan)
        and not args
    ):
        inner = receiver_plan.result
        outer_end, inner_end = (
            receiver_plan.start.plus(receiver_plan.duration),
            inner.start.plus(inner.duration),
        )
        end = Cost(
            max(outer_end.lower, inner_end.lower),
            None
            if outer_end.upper is None or inner_end.upper is None
            else max(outer_end.upper, inner_end.upper),
        )
        effects = (
            {**dict(receiver_plan.effects), **dict(inner.effects)}
            if receiver_plan.result_is_fresh
            else dict(receiver_plan.effects)
        )
        plan = TaskPlan(
            ZERO,
            end,
            inner.result,
            tuple(effects.items()),
            tuple(dict.fromkeys((*receiver_plan.stage_ids, *inner.stage_ids))),
            result_is_fresh=inner.result_is_fresh,
        )
        remember_plan(
            node,
            method,
            bindings,
            plan,
            fresh=bool(bindings.get(task_key(receiver, method) + ":fresh")),
        )
        return ZERO
    if name in {"Start", "RunSynchronously"} and isinstance(receiver_plan, DeferredTask):
        synchronous = name == "RunSynchronously"
        duration = UNKNOWN
        execution = None
        if (
            receiver_plan.supported
            and isinstance(receiver_plan.delegate, delegates.BoundDelegate)
            and not args
        ):
            execution = run_delegate(
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
            duration = execution.duration
        plan = TaskPlan(
            bindings.get(CLOCK, ZERO),
            duration,
            stage_ids=execution.stage_ids if execution is not None else (),
        )
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
        remember_plan(
            node,
            method,
            bindings,
            receiver_plan,
            fresh=bindings.get(task_key(receiver, method) + ":fresh", False),
        )
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
        if not args:
            join_stages(estimator, receiver_plan, background)
        if (
            not args
            and isinstance(receiver_plan, TaskPlan)
            and bindings.get(task_key(receiver, method) + ":fresh")
        ):
            bindings.update(receiver_plan.effects)
        if name == "GetResult":
            bindings[call_args.return_key(node, method, bindings)] = (
                receiver_plan.result if isinstance(receiver_plan, TaskPlan) else None
            )
            if isinstance(receiver_plan, TaskPlan) and known_task(receiver_plan.result):
                remember_plan(
                    node,
                    method,
                    bindings,
                    receiver_plan.result,
                    fresh=bool(
                        receiver_plan.result_is_fresh
                        and bindings.get(task_key(receiver, method) + ":fresh")
                    ),
                )
    elif full_name in {"Task.WaitAll", "Task.WaitAny", "Task.WhenAll", "Task.WhenAny"}:
        groups = [task_group(argument, method, bindings, estimator.index) for argument in args]
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
            remember(
                node,
                method,
                bindings,
                cost,
                stage_ids=tuple(
                    dict.fromkeys(
                        stage
                        for plan in plans
                        if isinstance(plan, TaskPlan)
                        for stage in plan.stage_ids
                    )
                )
                if name == "WhenAll"
                else (),
            )
            return ZERO
        if name in {"WaitAll", "WhenAll"}:
            for plan in plans:
                join_stages(estimator, plan, background)
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
