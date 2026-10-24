"""正文未展开时使可能写入失效；只保留源码证明未改写的私有任务。"""

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import simple_type
from app.modules.action_timing.source_private_effects import Effects, private_controls
from app.modules.action_timing.source_private_state import unsafe
from app.modules.action_timing.source_references import ancestors, invalidate_values


def readonly_tasks(index, target, receiver, bindings):
    marker = state.object_marker(receiver)
    unstable = bindings.get(state.UNSTABLE) or frozenset()
    if marker in unstable or bindings.get(state.UNKNOWN_MEMBERS):
        return frozenset()
    preserved = set()
    owners = set(ancestors(index, target.owner))
    cache = index.__dict__.setdefault("budget_private_task_effects", {})
    for owner in owners:
        names = private_controls(index, owner)
        candidates = {
            name
            for name in names
            if simple_type(index.member_type(owner, name)) == "Task"
            and not unsafe(index, (receiver, owner, name), bindings)
            and state.key((receiver, owner, name)) not in unstable
            and state.key((None, owner, name)) not in unstable
        }
        if not candidates:
            continue
        identity = (target.key, target.type_scope, owner)
        if identity not in cache:
            effects = Effects(index, names, owners).run(target, method_target=True)
            cache[identity] = (frozenset(effects.writes), bool(effects.opaque))
        writes, opaque = cache[identity]
        if not opaque:
            preserved.update(state.key((receiver, owner, name)) for name in candidates - writes)
    return frozenset(preserved)


def invalidate_receiver(index, target, receiver, bindings):
    preserved = readonly_tasks(index, target, receiver, bindings)
    invalidate_values([{"<ref>": receiver}], bindings)
    if not preserved:
        return
    # 子对象仍全部失效；当前对象的其他成员逐项失效，不能沿用声明初值。
    # 旧的整对象失效绝不会进入此分支，因而不会被一次只读调用清除。
    changed = {
        state.key((receiver, owner, name))
        for owner in ancestors(index, target.owner)
        if (info := index.classes.get(owner)) is not None
        for name in info.types
        if name not in info.static_members
    }
    changed.update(
        key
        for key in bindings
        if key.startswith((f"{state.PREFIX}{receiver}|", f"{state.COLLECTION_PREFIX}{receiver}|"))
    )
    bindings[state.UNSTABLE] = (
        (bindings.get(state.UNSTABLE) or frozenset()) - {state.object_marker(receiver)}
    ) | (changed - preserved)


def invalidate(estimator, target, node, caller, bindings, receiver, supplied):
    values = list(arguments.values(estimator.index, node, caller, bindings))
    values.extend((supplied or {}).values())
    invalidate_values(values, bindings)
    state.invalidate_byref(estimator.index, node, caller, bindings)
    if receiver is state.MISSING:
        saved = arguments.snapshot(node, caller, bindings)
        receiver = saved.receiver if saved else state.MISSING
    if receiver is state.MISSING:
        receiver = state.receiver_for(estimator.index, target, node, caller, bindings)
    if receiver is not None:
        invalidate_receiver(estimator.index, target, receiver, bindings)
    if target.is_static:
        keys = {
            state.key(("static", owner, name))
            for owner in ancestors(estimator.index, target.owner)
            if (info := estimator.index.classes.get(owner)) is not None
            for name in info.static_members
        }
        bindings[state.UNSTABLE] = (bindings.get(state.UNSTABLE) or frozenset()) | keys
