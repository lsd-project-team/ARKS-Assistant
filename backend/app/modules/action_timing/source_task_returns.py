"""源码方法返回任务时保留其创建时刻；await只补上尚未完成的时间。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO
from app.modules.action_timing.source_index import children, simple_type, text


def task_method(index, method):
    kind = method.return_type
    if method.callable_kind == "property_get":
        info = index.classes.get(method.owner)
        kind = info.types.get(method.name.removeprefix("get_"), "") if info else ""
    if kind.endswith("[]"):
        return False
    base = kind.split("<", 1)[0].rstrip("?")
    return (
        simple_type(base) == "Task"
        and base in {"Task", "System.Threading.Tasks.Task"}
        and index.lookup_type(base, method) not in index.classes
    )


def async_method(method):
    return any(text(node) == "async" for node in children(method.node, "modifier"))


def result_type(index, node, method):
    """保留Task<T>的T，用于await结果参与后续重载与数值计算。"""
    from app.modules.action_timing.source_collections import raw_type

    while node is not None and node.type in {"parenthesized_expression", "argument"}:
        node = children(node)[-1] if children(node) else None
    if node is None:
        return ""
    if node.type == "invocation_expression":
        function = node.child_by_field_name("function")
        source = text(function).removeprefix("System.Threading.Tasks.")
        if source.split("<", 1)[0] == "Task.FromResult" and framework_result(
            index, function, method
        ):
            kind = text(function.child_by_field_name("name"))
            if "<" in kind:
                return index.lookup_type(kind.split("<", 1)[1][:-1], method)
            args = children(node.child_by_field_name("arguments"), "argument")
            return index.infer(args[0], method) if len(args) == 1 else ""
        if text(function.child_by_field_name("name")) in {"ConfigureAwait", "GetAwaiter"}:
            return result_type(index, function.child_by_field_name("expression"), method)
    kind = raw_type(index, node, method)
    base, separator, generic = kind.partition("<")
    if (
        separator
        and generic.endswith(">")
        and simple_type(base) == "Task"
        and base in {"Task", "System.Threading.Tasks.Task"}
        and index.lookup_type(base, method) not in index.classes
    ):
        return index.lookup_type(generic[:-1], method)
    return ""


def framework_result(index, function, method):
    from app.modules.action_timing.source_tasks import framework_task

    return framework_task(index, text(function.child_by_field_name("expression")), method)


def completed_property(estimator, node, method, bindings):
    from app.modules.action_timing.source_tasks import framework_task, remember

    if (
        node.type != "member_access_expression"
        or text(node.child_by_field_name("name")) != "CompletedTask"
    ):
        return False
    if not framework_task(estimator.index, text(node.child_by_field_name("expression")), method):
        return False
    remember(node, method, bindings, ZERO)
    return True


def await_task(estimator, node, method, bindings, stack, conditions, background):
    from app.modules.action_timing.source_tasks import (
        CLOCK,
        CREATION_ONLY,
        TaskPlan,
        join_stages,
        lookup,
        task_key,
    )

    operand = children(node)[-1]
    started = bindings.get(CLOCK, ZERO)
    old = bindings.get(CREATION_ONLY, state.MISSING)
    bindings[CREATION_ONLY] = True
    try:
        before = estimator.expression(operand, method, bindings, stack, conditions, background)
    finally:
        if old is state.MISSING:
            bindings.pop(CREATION_ONLY, None)
        else:
            bindings[CREATION_ONLY] = old
    plan = lookup(operand, method, bindings, estimator.index)
    cost = plan.remaining(started.plus(before)) if plan is not None else UNKNOWN
    suspend = getattr(estimator, "suspend_await", None)
    if suspend is not None:
        suspend(bindings, cost, started.plus(before))
    join_stages(estimator, plan, background)
    estimator.record(
        "wait",
        "等待返回任务完成",
        node,
        method,
        conditions,
        background,
        resolved=cost.upper is not None,
        milliseconds=cost.lower if cost.lower == cost.upper else None,
    )
    if isinstance(plan, TaskPlan):
        bindings[call_args.return_key(node, method, bindings)] = plan.result
        if bindings.get(task_key(operand, method) + ":fresh"):
            for key, value in plan.effects:
                bindings[key] = value
    return before.plus(cost)


def result_property(estimator, node, method, bindings, stack, conditions, background):
    """Task<T>.Result先求值接收者，再等待；不能当成普通无成本属性。"""
    from app.modules.action_timing.source_tasks import (
        CLOCK,
        TaskPlan,
        framework_task,
        join_stages,
        known_task,
        lookup,
        remember_plan,
        task_key,
    )

    if (
        node.type != "member_access_expression"
        or text(node.child_by_field_name("name")) != "Result"
    ):
        return None
    receiver = node.child_by_field_name("expression")
    # 只接管框架任务，其他同名属性由原访问器执行，避免接收者求值两次。
    receiver_type = estimator.index.infer(receiver, method)
    function = receiver.child_by_field_name("function")
    framework_call = (
        receiver.type == "invocation_expression"
        and function is not None
        and text(function.child_by_field_name("name")).split("<", 1)[0]
        in {"Run", "StartNew", "FromResult"}
        and framework_task(
            estimator.index,
            text(function.child_by_field_name("expression")).removesuffix(".Factory"),
            method,
        )
    )
    if receiver_type in estimator.index.classes or not (
        simple_type(receiver_type) == "Task"
        or lookup(receiver, method, bindings, estimator.index)
        or framework_call
    ):
        return None
    before = estimator.expression(receiver, method, bindings, stack, conditions, background)
    plan = lookup(receiver, method, bindings, estimator.index)
    cost = plan.remaining(bindings.get(CLOCK, ZERO).plus(before)) if plan else UNKNOWN
    join_stages(estimator, plan, background)
    bindings[call_args.return_key(node, method, bindings)] = (
        plan.result if isinstance(plan, TaskPlan) else None
    )
    if isinstance(plan, TaskPlan) and bindings.get(task_key(receiver, method) + ":fresh"):
        bindings.update(plan.effects)
    if isinstance(plan, TaskPlan) and known_task(plan.result):
        remember_plan(
            node,
            method,
            bindings,
            plan.result,
            fresh=bool(
                plan.result_is_fresh and bindings.get(task_key(receiver, method) + ":fresh")
            ),
        )
    estimator.record(
        "wait",
        "读取任务结果前等待完成",
        node,
        method,
        conditions,
        background,
        resolved=cost.upper is not None,
        milliseconds=cost.lower if cost.lower == cost.upper else None,
    )
    return before.plus(cost)
