""".NET Framework异步委托；Begin只发起，End等待对应目标的同步返回。"""

from dataclasses import dataclass

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_dispatch, source_dynamic
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_collections import raw_type
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost
from app.modules.action_timing.source_index import text
from app.modules.action_timing.source_tasks import (
    CLOCK,
    TaskPlan,
    is_fresh,
    join_stages,
    known_task,
    remember_plan,
    task_ids,
)


@dataclass(frozen=True)
class AsyncInvocation:
    delegate: object
    plan: TaskPlan
    end_marker: str


def operation(index, node, method):
    receiver, name = source_dispatch.function_parts(node)
    return (
        receiver is not None
        and name in {"BeginInvoke", "EndInvoke"}
        and not index.has_source_call(node, method)
        and source_dynamic.signature(index, raw_type(index, receiver, method), method) is not None
    )


def invalidate(bindings, bound=None, caller=None):
    from app.modules.action_timing.source_parallel import invalidate_unexplored

    captured = (
        {slot for _, slot in bound.closure.cells}
        if isinstance(bound, delegates.BoundDelegate)
        else None
    )
    # 已知目标没有捕获的调用者局部变量不能被它直接改写；成员和集合内容
    # 仍失效。保留局部委托/结果身份，才能等待一个正文尚未完全展开的目标。
    protected = {
        key: value
        for key, value in bindings.items()
        if captured is not None
        and key.startswith(state.LOCAL_PREFIX)
        and "apm-end:" not in key
        and key not in captured
    }
    if captured is not None and caller is not None:
        for name in caller.types:
            slot = bindings.get(
                f"{state.LOCAL_ALIAS}{name}>",
                f"{state.LOCAL_PREFIX}{bindings.get(state.FRAME)}|{name}>",
            )
            if slot not in captured and name in bindings:
                protected[name] = bindings[name]
    invalidate_unexplored(bindings)
    bindings.update(protected)


def propagate_writes(estimator, scope, bindings, start, bound=None, caller=None):
    unresolved = any(
        stage["kind"] == "unresolved"
        and stage["label"]
        in {
            "委托目标为空或尚未绑定",
            "委托方法或实际实例类型未绑定",
            "反射委托目标或参数签名未绑定",
            "回调达到展开边界",
        }
        for stage in estimator.stages[start:]
    )
    if estimator.truncated or unresolved:
        invalidate(bindings, bound, caller)
        return
    for key in scope.get(state.WRITES, ()):
        if key.startswith((state.PREFIX, state.LOCAL_PREFIX, state.COLLECTION_PREFIX)):
            bindings[key] = None
            state.mark_write(bindings, key)


def begin(estimator, node, method, bindings, stack, conditions, background, bound):
    nodes = call_args.arguments(node)
    values = call_args.values(estimator.index, node, method, bindings)
    shape = (
        source_dynamic.signature(estimator.index, bound.signature, bound.closure.method)
        if isinstance(bound, delegates.BoundDelegate)
        else None
    )
    valid = (
        shape is not None
        and len(nodes) == bound.arity + 2
        and not any(call_args.argument_name(part) for part in nodes)
        and (
            text(source_dynamic.unwrapped(nodes[-2])) == "null"
            or values[-2] is delegates.NULL_DELEGATE
        )
        and all(
            source_dynamic.compatible(
                expected, source_dynamic.argument_type(estimator.index, argument, method)
            )
            for expected, argument in zip(shape[0], nodes[:-2], strict=True)
        )
    )
    if not valid:
        invalidate(bindings)
        estimator.record(
            "unresolved",
            "异步委托签名、参数或完成回调未绑定",
            node,
            method,
            conditions,
            background,
            apm=True,
        )
        return UNKNOWN
    scope = source_dispatch.queued_scope(bound, bindings)
    # 共享值沿用排队后的保守快照，时钟沿用Task的立即调度假设。
    scope[CLOCK] = bindings.get(CLOCK, ZERO)
    start = len(estimator.stages)
    previous_tasks = task_ids(bindings.values())
    previous_calls, previous_truncated = estimator.calls, estimator.truncated
    estimator.calls, estimator.truncated = 0, False
    try:
        # 异步目标有自己的调用预算；保留委托祖先以防无限自调度，
        # 不继承发起线程的普通调用深度。帧和对象编号继续共用，避免别名碰撞。
        async_stack = tuple(key for key in stack if key.startswith("<delegate:"))
        duration = delegates.execute(
            estimator,
            bound,
            method,
            scope,
            async_stack,
            (*conditions, "异步委托已调度"),
            False,
            argument_values=values[:-2],
            argument_types=tuple(
                source_dynamic.argument_type(estimator.index, arg, method) for arg in nodes[:-2]
            ),
            join_result=False,
        )
        propagate_writes(estimator, scope, bindings, start, bound, method)
    finally:
        estimator.calls = previous_calls
        estimator.truncated |= previous_truncated
    stage_ids = tuple(id(stage) for stage in estimator.stages[start:] if not stage["background"])
    for stage in estimator.stages[start:]:
        stage["background"] = True
    plan = TaskPlan(
        bindings.get(CLOCK, ZERO),
        duration,
        scope.get(delegates.RESULT),
        stage_ids=stage_ids,
        result_is_fresh=is_fresh(scope.get(delegates.RESULT), previous_tasks),
    )
    estimator.apm_calls += 1
    marker = f"{state.LOCAL_PREFIX}apm-end:{estimator.apm_calls}>"
    bindings[marker] = False
    bindings[call_args.return_key(node, method, bindings)] = AsyncInvocation(bound, plan, marker)
    estimator.record(
        "background",
        "异步委托已发起，EndInvoke时等待完成",
        node,
        method,
        conditions,
        True,
        apm=True,
        operation="begin",
        note="沿用Task的立即调度假设；不估计线程池排队或CPU开销",
    )
    return ZERO


def end(estimator, node, method, bindings, conditions, background, bound):
    nodes = call_args.arguments(node)
    values = call_args.values(estimator.index, node, method, bindings)
    pending = values[0] if len(values) == 1 else None
    if (
        len(nodes) != 1
        or call_args.argument_name(nodes[0])
        or not isinstance(pending, AsyncInvocation)
        or not isinstance(bound, delegates.BoundDelegate)
        or pending.delegate is not bound
        or bindings.get(pending.end_marker) is not False
    ):
        estimator.record(
            "unresolved",
            "异步结果与委托未匹配或已结束",
            node,
            method,
            conditions,
            background,
            apm=True,
        )
        return UNKNOWN
    bindings[pending.end_marker] = True
    state.mark_write(bindings, pending.end_marker)
    join_stages(estimator, pending.plan, background)
    result = pending.plan.result
    if known_task(result):
        remember_plan(node, method, bindings, result, fresh=pending.plan.result_is_fresh)
    else:
        bindings[call_args.return_key(node, method, bindings)] = result
    clock = bindings.get(CLOCK, ZERO)
    remaining = pending.plan.remaining(clock)
    # 未知的中间耗时会使“实际还需阻塞多久”的下界为0，但已join目标的
    # 完成点仍约束累计经过时间；该差值不是再次累加整个异步正文。
    completed_lower = pending.plan.start.lower + pending.plan.duration.lower
    elapsed = Cost(max(remaining.lower, completed_lower - clock.lower, 0), remaining.upper)
    estimator.record(
        "wait",
        "等待对应异步委托返回",
        node,
        method,
        conditions,
        background,
        apm=True,
        operation="end",
        resolved=remaining.upper is not None,
        elapsed_lower_bound_ms=clock.lower + elapsed.lower,
        note="仅等待该委托的同步返回；它返回的Task和未join子任务仍需源码另行等待",
    )
    return elapsed


def handle(estimator, node, method, bindings, stack, conditions, background):
    if not operation(estimator.index, node, method):
        return None
    receiver, name = source_dispatch.function_parts(node)
    saved = call_args.snapshot(node, method, bindings)
    bound = saved.receiver_value if saved is not None else state.MISSING
    if bound is state.MISSING:
        bound = delegates.capture(estimator.index, receiver, method, bindings)
    if name == "BeginInvoke":
        return begin(estimator, node, method, bindings, stack, conditions, background, bound)
    return end(estimator, node, method, bindings, conditions, background, bound)
