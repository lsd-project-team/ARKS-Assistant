"""记住已发起的后台目标，防止后续赋值掩盖仍可能发生的私有控制字段写入。"""

from dataclasses import dataclass
from weakref import WeakKeyDictionary

from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_dispatch
from app.modules.action_timing import source_state as state


@dataclass(frozen=True, eq=False)
class Activity:
    target: object
    environment: tuple
    method_target: bool = False


UNKNOWN_ACTIVITY = Activity(None, ())


def remember(bindings, target, *, method_target=False):
    from app.modules.action_timing.source_multicast import targets

    environment = {}
    if isinstance(target, delegates.BoundDelegate):
        for callback in targets(target):
            method = callback.closure.method
            for name, slot in callback.closure.cells:
                value = bindings.get(slot)
                value = value if not source_dispatch.reassigned(method, name) else None
                environment[name] = (
                    value if name not in environment or environment[name] is value else None
                )
    elif method_target:
        for name, _, _ in target.parameters:
            environment[name] = (
                bindings.get(name) if not source_dispatch.reassigned(target, name) else None
            )
    activities = bindings.get(state.PRIVATE_PENDING) or frozenset()
    # 不把达到分析边界后的更多后台调用视为无写入。
    if len(activities) >= 64:
        target = None
    activity = (
        UNKNOWN_ACTIVITY
        if target is None
        else Activity(target, tuple(environment.items()), method_target)
    )
    # 当前阶段不在join后撤销潜在写入：嵌套/逃逸子任务仍可能运行。
    # 因而某些本可重新赋值恢复的控制字段会继续未定，不会反向变成固定耗时。
    bindings[state.PRIVATE_PENDING] = activities | {activity}
    return activity


def activate(index, bindings, activity, *, method=None, stack=()):
    from app.modules.action_timing.source_multicast import targets

    active = set() if activity is UNKNOWN_ACTIVITY else {activity}
    if method is not None and stack.count(method.key) <= 1:
        for previous in bindings.get(state.PRIVATE_ACTIVE) or ():
            bound = previous.target
            if not isinstance(bound, delegates.BoundDelegate):
                continue
            for callback in targets(bound):
                same_lambda = callback.node == method.node
                target = delegates.method_group(
                    index, callback.node, callback.closure.method, callback.arity
                )
                if same_lambda or (target is not None and target.key == method.key):
                    active.add(previous)
    # 同步子调用沿用此集合；新后台目标重新建集合，重新看到发起者的潜在写入。
    bindings[state.PRIVATE_ACTIVE] = frozenset(active)


def summary(index, activity, owner):
    from app.modules.action_timing.source_private_effects import Effects, private_controls

    cache = index.__dict__.setdefault("private_activity_effects", WeakKeyDictionary())
    summaries = cache.setdefault(activity, {})
    if owner not in summaries:
        names = private_controls(index, owner)
        effects = Effects(index, names, {owner}).run(
            activity.target,
            dict(activity.environment),
            method_target=activity.method_target,
        )
        summaries[owner] = (frozenset(effects.writes), bool(effects.opaque), effects.ends)
    return summaries[owner]


def unsafe(index, place, bindings):
    from app.modules.action_timing.source_private_effects import private_controls

    activities = bindings.get(state.PRIVATE_PENDING)
    if not activities or place is None or place[2] not in private_controls(index, place[1]):
        return False
    for activity in activities:
        if activity in (bindings.get(state.PRIVATE_ACTIVE) or ()):
            continue
        writes, opaque, _ = summary(index, activity, place[1])
        if opaque or place[2] in writes:
            return True
    return False


def may_end(index, owner, bindings):
    return any(
        summary(index, activity, owner)[2]
        for activity in bindings.get(state.PRIVATE_PENDING) or ()
        if activity not in (bindings.get(state.PRIVATE_ACTIVE) or ())
    )
