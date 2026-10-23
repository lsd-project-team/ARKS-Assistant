"""async调用的同步前段与任务完成时间分开求值，不提前发布续体写入。"""

from collections import defaultdict, deque

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost, Flow, choice
from app.modules.action_timing.source_tasks import CLOCK, TaskPlan

SUSPENDED = "<async-suspended>"


class Suspension(Exception):
    def __init__(self, frame, clock, bindings, uncertain):
        self.frame = frame
        self.clock = clock
        self.bindings = dict(bindings)
        self.uncertain = uncertain


def prefix_estimator(source, frame):
    # 延迟导入避免Estimator与控制流模块互相初始化。
    from app.modules.action_timing.source_estimator import Estimator

    class PrefixEstimator(Estimator):
        def suspend_await(self, bindings, cost, clock):
            if bindings.get(state.FRAME) == self.suspend_frame and cost.upper != 0:
                raise Suspension(self.suspend_frame, clock, bindings, cost.lower == 0)

        def block(self, node, method, bindings, stack, conditions, background):
            started = bindings.get(CLOCK, ZERO)
            try:
                return super().block(node, method, bindings, stack, conditions, background)
            except Suspension as suspended:
                if bindings.get(state.FRAME) != suspended.frame:
                    raise
                upper = (
                    None
                    if suspended.uncertain or suspended.clock.upper is None
                    else max(0, suspended.clock.upper - started.lower)
                )
                lower = (
                    max(0, suspended.clock.lower - started.upper)
                    if started.upper is not None
                    else 0
                )
                return Flow(None, jumps={SUSPENDED: Cost(lower, upper)}).with_state(
                    SUSPENDED, suspended.bindings
                )

    result = PrefixEstimator(source.index)
    result.__dict__.update(
        {
            key: value
            for key, value in source.__dict__.items()
            if key not in {"stages", "parameters", "skip_conditions", "failure_reasons"}
        }
    )
    result.suspend_frame = frame
    return result


def completed_scope(flow, scope, *, suspended=False):
    paths = [dict(scope)] if flow.live is not None else []
    paths.extend(
        flow.states[key]
        for key in ("returned", SUSPENDED)
        if key in flow.states and (key != SUSPENDED or suspended)
    )
    result = dict(scope)
    if paths:
        state.merge(result, paths)
    return result


def unresolved(stage):
    return not stage["background"] and (
        stage["kind"] in {"motion", "wait", "call", "unresolved"}
        and not stage.get("resolved")
        or stage["kind"] == "loop"
        and stage.get("iterations") is None
        and not stage.get("bounded")
    )


def event_key(stage):
    return (
        stage["path"],
        stage["line"],
        stage["kind"],
        stage["code"],
        stage["method"],
        tuple(stage["conditions"]),
    )


def execute(estimator, method, values, stack, conditions, background):
    started = values.get(CLOCK, ZERO)
    prefix = prefix_estimator(estimator, values.get(state.FRAME))
    immediate = dict(values)
    initial = dict(values)
    head = prefix.execute_body(method, immediate, stack, conditions, background)
    immediate = completed_scope(head, immediate, suspended=True)
    prefix_cost = (
        choice(
            head.cost() if head.live is not None or head.returned is not None else None,
            head.jumps.get(SUSPENDED),
        )
        or ZERO
    )
    if SUSPENDED not in head.jumps:
        # 已完成的await不切线程，也不需要再展开一次正文。
        estimator.stages.extend(prefix.stages)
        estimator.parameters.update(prefix.parameters)
        for name in (
            "calls",
            "frames",
            "scope_frames",
            "allocations",
            "loop_steps",
            "numeric_loop_steps",
            "jump_steps",
            "truncated",
        ):
            setattr(estimator, name, getattr(prefix, name))
        estimator.skip_conditions.extend(prefix.skip_conditions)
        estimator.failure_reasons.extend(prefix.failure_reasons)
        values.update(immediate)
        duration = prefix_cost if head.live is not None or head.returned is not None else UNKNOWN
        return prefix_cost, TaskPlan(started, duration, immediate.get("<return-value>"))

    begin = len(estimator.stages)
    from app.modules.action_timing.source_private_state import activate, remember

    activity = remember(values, method, method_target=True)
    activate(estimator.index, values, activity, method=method, stack=stack)
    previous = [(stage, stage["background"]) for stage in estimator.stages]
    full = estimator.execute_body(method, values, stack, conditions, False)
    completion = completed_scope(full, values)
    tail = estimator.stages[begin:]
    duration = full.cost() if full.live is not None or full.returned is not None else UNKNOWN
    if any(unresolved(stage) for stage in tail):
        duration = Cost(duration.lower, None)
    # 续体中等待外部旧任务，不代表发起async的调用者已经等待它。
    dependencies = []
    for stage, was_background in previous:
        if was_background and not stage["background"]:
            dependencies.append(id(stage))
        stage["background"] = was_background

    # 同步前段只显示一次，其余阶段是未来续体。保留循环中相同源码的重复次数。
    retained = defaultdict(deque)
    for stage in prefix.stages:
        retained[event_key(stage)].append(stage)
    future = []
    stage_ids = list(dependencies)
    for stage in tail:
        key = event_key(stage)
        if retained[key]:
            existing = retained[key].popleft()
            # 首个未完成await已经创建其任务；完成后仍是同一阶段，不能复制一次。
            # 仅在完整路径确实等待它时，交给外层任务完成边界恢复前台归属。
            if existing["background"] and not stage["background"]:
                stage_ids.append(id(existing))
        else:
            pending = {**stage, "background": True}
            future.append(pending)
            if not stage["background"]:
                stage_ids.append(id(pending))
    estimator.stages[begin:] = [*prefix.stages, *future]
    estimator.parameters.update(prefix.parameters)
    estimator.truncated |= prefix.truncated

    final_context = state.context(completion)
    effects = tuple(
        (key, value)
        for key, value in final_context.items()
        if key not in {state.PRIVATE_PENDING, state.PRIVATE_ACTIVE}
        and (key not in initial or value != initial[key])
    )
    # 未join时共享写入可能和调用者交错，只传播失效，不能当作已发生的常量。
    concurrent = dict(immediate)
    state.transfer(concurrent, completion, uncertain=True)
    values.clear()
    values.update(concurrent)
    return prefix_cost, TaskPlan(
        started, duration, completion.get("<return-value>"), effects, tuple(stage_ids)
    )
