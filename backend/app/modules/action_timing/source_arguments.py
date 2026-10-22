"""参数名决定绑定位置；实参仍按出现顺序求值并保存当时的值。"""

from dataclasses import dataclass

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO


def arguments(node):
    if node is None:
        return []
    listing = node.child_by_field_name("arguments") or next(
        (part for part in node.children if part.type == "argument_list"), None
    )
    return [part for part in listing.children if part.type == "argument"] if listing else []


def argument_name(node):
    if not any(part.type == ":" for part in node.children):
        return None
    name = node.child_by_field_name("name")
    return name.text.decode("utf-8").removeprefix("@") if name is not None else None


def plan(parameters, nodes, provided=()):
    """返回每个实参对应的形参位置；拒绝缺参、重名及不合法的混用顺序。"""
    names = [name.removeprefix("@") for name, _, _ in parameters]
    assigned, result, displaced = set(), [], False
    for position, node in enumerate(nodes):
        name = argument_name(node)
        if name is None:
            if displaced or position >= len(parameters):
                return None
            slot = position
        else:
            if name not in names:
                return None
            slot = names.index(name)
            displaced |= slot != position
        if slot in assigned:
            return None
        assigned.add(slot)
        result.append(slot)
    if any(
        slot not in assigned and default is None and name not in provided
        for slot, (name, _, default) in enumerate(parameters)
    ):
        return None
    return tuple(result)


@dataclass(frozen=True)
class Evaluated:
    values: tuple
    callbacks: tuple
    receiver: object = state.MISSING
    references: tuple = ()
    receiver_value: object = state.MISSING


def snapshot_key(node, method, bindings):
    return f"<arguments:{bindings.get(state.FRAME)}|{method.key}|{node.start_byte}:{node.end_byte}>"


def snapshot(node, method, bindings):
    saved = bindings.get(snapshot_key(node, method, bindings))
    return saved if isinstance(saved, Evaluated) else None


def return_key(node, method, bindings):
    return snapshot_key(node, method, bindings) + ":return"


def values(index, node, method, bindings, seen=None):
    saved = snapshot(node, method, bindings)
    return (
        tuple(state.materialize(value, bindings) for value in saved.values)
        if saved is not None
        else tuple(index.value(arg, method, bindings, seen) for arg in arguments(node))
    )


def evaluate(
    estimator,
    node,
    method,
    bindings,
    stack,
    conditions,
    background,
    target=None,
    prefix=ZERO,
    receiver=state.MISSING,
    receiver_value=state.MISSING,
):
    from app.modules.action_timing import source_delegates as delegates
    from app.modules.action_timing.source_tasks import CLOCK

    nodes = arguments(node)
    bindings.pop(return_key(node, method, bindings), None)
    slots = plan(target.parameters, nodes) if target is not None else None
    started, cost = bindings.get(CLOCK, ZERO), prefix
    scalars, callbacks, references = [], [], []
    for position, arg in enumerate(nodes):
        bindings[CLOCK] = started.plus(cost)
        cost = cost.plus(estimator.expression(arg, method, bindings, stack, conditions, background))
        scalars.append(estimator.index.value(arg, method, bindings))
        references.append(state.capture_ref(estimator.index, arg, method, bindings))
        bound = state.MISSING
        if slots is not None:
            _, kind, _ = target.parameters[slots[position]]
            arity = delegates.signature_arity(kind)
            if (
                arity is not None
                and estimator.index.lookup_type(kind, target) not in estimator.index.classes
            ):
                bound = delegates.capture(
                    estimator.index,
                    arg,
                    method,
                    bindings,
                    arity,
                    returns_task="Task" in kind and kind.replace("System.", "").startswith("Func<"),
                )
        callbacks.append(bound)
    # 下一次访问该调用时覆盖快照；快照仅属于当前帧，不进入被调方法的状态。
    bindings[snapshot_key(node, method, bindings)] = Evaluated(
        tuple(scalars), tuple(callbacks), receiver, tuple(references), receiver_value
    )
    bindings[CLOCK] = started.plus(cost)
    return cost
