"""离开try的每个出口先执行finally，再携带更新后的状态恢复原控制流。"""

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO, Flow
from app.modules.action_timing.source_index import children
from app.modules.action_timing.source_tasks import CLOCK


def execute(estimator, clause, incoming, method, bindings, stack, conditions, background):
    result = Flow(None, None)
    started = bindings.get(CLOCK, ZERO)
    continuing = []
    costs = {
        **{key: getattr(incoming, key) for key in ("live", "returned", "broken", "continued")},
        **incoming.jumps,
    }
    for channel, cost in costs.items():
        if cost is None:
            continue
        scope = dict(incoming.states.get(channel, bindings))
        scope[CLOCK] = started.plus(cost)
        final = estimator.block(
            next(iter(children(clause, "block")), None),
            method,
            scope,
            stack,
            conditions,
            background,
        )
        # finally中的throw或不终止循环不会恢复原来的goto/return出口。
        if final.live is None:
            continue
        duration = cost.plus(final.live)
        scope[CLOCK] = started
        resumed = Flow(None, None)
        if channel in incoming.jumps:
            resumed.jumps[channel] = duration
        else:
            setattr(resumed, channel, duration)
        if channel == "live":
            continuing.append(scope)
        else:
            resumed.with_state(channel, scope)
        result = result.merge(resumed)
    if continuing:
        state.merge(bindings, continuing)
    bindings[CLOCK] = started
    return result
