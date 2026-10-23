"""委托调用列表为不可变快照；订阅不执行正文，触发才顺序执行。"""

from dataclasses import replace

from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO

MAX_HANDLERS = 128


def targets(bound):
    return bound.targets or (bound,) if isinstance(bound, delegates.BoundDelegate) else ()


def signature(kind):
    return "".join(kind.split()).replace("global::", "").removeprefix("System.")


def same_handler(index, left, right):
    if left is right:
        return True
    anonymous = {"lambda_expression", "anonymous_method_expression"}
    if left.node.type in anonymous or right.node.type in anonymous:
        # 相同变量保存同一实例；重新创建的同一lambda可能有不同闭包，不能猜缓存。
        return False if left.node != right.node else None
    first = delegates.method_group(index, left.node, left.closure.method, left.arity)
    second = delegates.method_group(index, right.node, right.closure.method, right.arity)
    if first is None or second is None:
        return None
    if first.key != second.key:
        return False
    if first.is_static:
        return True
    if left.receiver_id is state.MISSING or left.receiver_id is None:
        return None
    return left.receiver_id == right.receiver_id if right.receiver_id is not None else None


def combine(index, left, right, operator):
    if left is not delegates.NULL_DELEGATE and not isinstance(left, delegates.BoundDelegate):
        return None
    if right is not delegates.NULL_DELEGATE and not isinstance(right, delegates.BoundDelegate):
        return None
    if left is delegates.NULL_DELEGATE:
        return right if operator in {"+", "+="} else delegates.NULL_DELEGATE
    if right is delegates.NULL_DELEGATE:
        return left
    if not left.signature or signature(left.signature) != signature(right.signature):
        return None
    first, second = targets(left), targets(right)
    if operator in {"+", "+="}:
        result = first + second
        if len(result) > MAX_HANDLERS:
            return None
    else:
        result = first
        for start in range(len(first) - len(second), -1, -1):
            matches = [
                same_handler(index, a, b) for a, b in zip(first[start:], second, strict=False)
            ]
            if any(match is False for match in matches):
                continue
            if any(match is None for match in matches):
                return None
            result = first[:start] + first[start + len(second) :]
            break
    if not result:
        return delegates.NULL_DELEGATE
    return result[0] if len(result) == 1 else replace(result[-1], targets=result)


def assignment(index, left, right, method, bindings, current, operator):
    from app.modules.action_timing import source_dynamic
    from app.modules.action_timing.source_collections import raw_type

    if operator not in {"=", "+=", "-="}:
        return state.MISSING
    kind = raw_type(index, left, method)
    shape = source_dynamic.signature(index, kind, method)
    if shape is None:
        return state.MISSING
    bound = delegates.capture(index, right, method, bindings, signature_kind=kind)
    return bound if operator == "=" else combine(index, current, bound, operator)


def binary(index, node, method, bindings, left, right):
    from app.modules.action_timing import source_dynamic
    from app.modules.action_timing.source_index import text

    operator = text(node.child_by_field_name("operator"))
    if operator not in {"+", "-", "==", "!="}:
        return state.MISSING
    parts = (node.child_by_field_name("left"), node.child_by_field_name("right"))
    kind = next(
        (value.signature for value in (left, right) if isinstance(value, delegates.BoundDelegate)),
        "",
    ) or next(
        (
            source_dynamic.explicit_signature(index, part, method)
            for part in parts
            if source_dynamic.explicit_signature(index, part, method)
        ),
        "",
    )
    if source_dynamic.signature(index, kind, method) is None:
        return state.MISSING
    values = [
        delegates.capture(index, part, method, bindings, signature_kind=kind) for part in parts
    ]
    if operator in {"==", "!="}:
        if any(
            value is not delegates.NULL_DELEGATE and not isinstance(value, delegates.BoundDelegate)
            for value in values
        ):
            return None
        first, second = (targets(value) for value in values)
        matches = [same_handler(index, a, b) for a, b in zip(first, second, strict=False)]
        same = (
            False
            if len(first) != len(second) or any(match is False for match in matches)
            else None
            if any(match is None for match in matches)
            else True
        )
        return same if same is None or operator == "==" else not same
    return combine(index, *values, operator)


def initialize_instance(index, owner, bindings, reference):
    """只给正在new/构造的实例设置委托零值；已存在对象的订阅继续未定。"""
    from app.modules.action_timing import source_dynamic

    pending, seen = [owner], set()
    while pending:
        current = pending.pop()
        if current in seen or current not in index.classes:
            continue
        seen.add(current)
        info = index.classes[current]
        for name, kind in info.types.items():
            if (
                name in info.static_members
                or name not in info.field_members
                or source_dynamic.signature(index, kind, current) is None
            ):
                continue
            slot = state.key((reference, current, name))
            bindings[slot] = delegates.NULL_DELEGATE
            state.mark_write(bindings, slot)
        pending.extend(index.base_types(current))


def initialize_value(index, method, bindings):
    from app.modules.action_timing.source_dynamic import signature

    name = method.name.removeprefix(".initialize_")
    info = index.classes[method.owner]
    kind = info.types.get(name, "")
    if signature(index, kind, method) is not None:
        value = delegates.capture(index, method.body, method, bindings, signature_kind=kind)
        reference = "static" if name in info.static_members else bindings.get(state.THIS)
        slot = state.key((reference, method.owner, name))
        bindings[slot] = value
        state.mark_write(bindings, slot)


def execute(estimator, bound, method, bindings, stack, conditions, background, **options):
    from app.modules.action_timing.source_tasks import CLOCK

    started, cost = bindings.get(CLOCK, ZERO), ZERO
    entries = targets(bound)
    for position, target in enumerate(entries):
        bindings[CLOCK] = started.plus(cost)
        current = dict(options)
        if position != len(entries) - 1:
            current["join_result"] = False  # 只有最后一个返回Task交给调用者，先前任务仍在后台。
        cost = cost.plus(
            delegates.execute(
                estimator, target, method, bindings, stack, conditions, background, **current
            )
        )
        if bindings.get(delegates.COMPLETION) is not True:
            from app.modules.action_timing.source_parallel import invalidate_unexplored

            invalidate_unexplored(bindings)
            estimator.record(
                "unresolved",
                "处理器未证明正常返回，后续状态保持未定",
                target.node,
                target.closure.method,
                conditions,
                background,
            )
            cost = cost.plus(UNKNOWN)
            break
    bindings[CLOCK] = started
    return cost
