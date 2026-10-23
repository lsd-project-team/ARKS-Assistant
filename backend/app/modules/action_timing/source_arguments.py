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


def plan(parameters, nodes, provided=(), *, variadic=False):
    """返回每个实参对应的形参位置；拒绝缺参、重名及不合法的混用顺序。"""
    names = [name.removeprefix("@") for name, _, _ in parameters]
    assigned, result, displaced, named_tail = set(), [], False, False
    for position, node in enumerate(nodes):
        name = argument_name(node)
        if name is None:
            if displaced or (position >= len(parameters) and not variadic):
                return None
            slot = min(position, len(parameters) - 1) if variadic else position
        else:
            if name not in names:
                return None
            slot = names.index(name)
            displaced |= slot != position
        repeated_tail = variadic and slot == len(parameters) - 1 and name is None and not named_tail
        if slot in assigned and not repeated_tail:
            return None
        named_tail |= variadic and slot == len(parameters) - 1 and name is not None
        assigned.add(slot)
        result.append(slot)
    if any(
        slot not in assigned
        and default is None
        and name not in provided
        and not (variadic and slot == len(parameters) - 1)
        for slot, (name, _, default) in enumerate(parameters)
    ):
        return None
    return tuple(result)


def declared_parameters(node):
    """当前C#语法树把params尾参数直接放在parameter_list，不能只读parameter节点。"""
    from app.modules.action_timing.source_index import children, initializer, text

    listing = node.child_by_field_name("parameters")
    result = [
        (
            text(part.child_by_field_name("name")),
            text(part.child_by_field_name("type")),
            initializer(part),
        )
        for part in children(listing, "parameter")
    ]
    variadic = listing is not None and any(part.type == "params" for part in listing.children)
    if variadic:
        result.append(
            (
                text(listing.child_by_field_name("name")),
                text(listing.child_by_field_name("type")),
                None,
            )
        )
    return result, variadic


def bound_values(estimator, target, nodes, slots, scalars, caller, bindings):
    result = {target.parameters[slot][0]: value for slot, value in zip(slots, scalars, strict=True)}
    if not target.variadic:
        return result
    from app.modules.action_timing import source_collections as collections
    from app.modules.action_timing import source_dynamic

    name, kind, _ = target.parameters[-1]
    positions = [
        position for position, slot in enumerate(slots) if slot == len(target.parameters) - 1
    ]
    types = [
        source_dynamic.argument_type(estimator.index, nodes[position], caller)
        for position in positions
    ]
    if len(positions) == 1:
        position = positions[0]
        if params_normal(estimator.index, target, nodes, caller):
            result[name] = scalars[position]
            return result
        if argument_name(nodes[position]) is not None:
            return None  # 命名params只能使用正常数组形式，不把非法标量包装成数组。
    values = tuple(scalars[position] for position in positions)
    data = {
        "<collection>": "array",
        "<type>": kind,
        "<element_type>": kind.removesuffix("[]"),
        "<ref>": f"params:{estimator.frames}:{caller.unit.path}:{target.node.start_byte}",
        "<length>": len(values),
        "<shape>": (len(values),),
        "<items>": values,
    }
    result[name] = data
    if data["<element_type>"] in {"object", "System.Object"}:
        for position, kind in enumerate(types):
            bindings[collections.key(data, f"type:{position}")] = kind
    return result


def params_normal(index, target, nodes, caller):
    if not target.variadic:
        return False
    from app.modules.action_timing import source_dynamic
    from app.modules.action_timing.source_index import text

    slots = plan(target.parameters, nodes, variadic=True)
    positions = [
        position for position, slot in enumerate(slots or ()) if slot == len(target.parameters) - 1
    ]
    if len(positions) != 1:
        return False
    node = nodes[positions[0]]
    actual = source_dynamic.argument_type(index, node, caller)
    kind = target.parameters[-1][1]
    return (
        text(source_dynamic.unwrapped(node)) == "null"
        or actual == kind
        or (
            kind in {"object[]", "System.Object[]"}
            and source_dynamic.reference_array(index, actual, caller)
        )
    )


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
    from app.modules.action_timing import source_dispatch
    from app.modules.action_timing.source_tasks import CLOCK

    nodes = arguments(node)
    bindings.pop(return_key(node, method, bindings), None)
    slots = plan(target.parameters, nodes, variadic=target.variadic) if target is not None else None
    dispatch = (
        source_dispatch.callback_position(estimator.index, node, method) if target is None else None
    )
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
                or kind
                in {"Delegate", "System.Delegate", "MulticastDelegate", "System.MulticastDelegate"}
            ) and estimator.index.lookup_type(kind, target) not in estimator.index.classes:
                bound = delegates.capture(
                    estimator.index,
                    arg,
                    method,
                    bindings,
                    arity or 0,
                    returns_task=None
                    if arity is None
                    else "Task" in kind and kind.replace("System.", "").startswith("Func<"),
                    discards_result=kind.replace("System.", "").split("<", 1)[0] == "Action",
                    signature_kind=kind,
                )
        if dispatch is not None and position == dispatch[1]:
            bound = source_dispatch.capture_callback(
                estimator.index, arg, method, bindings, dispatch[0]
            )
        callbacks.append(bound)
    # 下一次访问该调用时覆盖快照；快照仅属于当前帧，不进入被调方法的状态。
    bindings[snapshot_key(node, method, bindings)] = Evaluated(
        tuple(scalars), tuple(callbacks), receiver, tuple(references), receiver_value
    )
    bindings[CLOCK] = started.plus(cost)
    return cost
