"""属性访问器也可能执行动作；读、写及复合赋值分别计算。"""

import math

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_collection_expressions import evaluate_location
from app.modules.action_timing.source_flow import UNKNOWN, ZERO
from app.modules.action_timing.source_index import children, text
from app.modules.action_timing.source_numbers import bounded, quotient
from app.modules.action_timing.source_tasks import CLOCK, track_binding


def accessor_cost(
    estimator,
    target,
    node,
    method,
    bindings,
    stack,
    conditions,
    background,
    value=None,
    receiver_id=state.MISSING,
):
    if target is None:
        return ZERO
    if estimator.index.polymorphic(node, method, target):
        estimator.record(
            "unresolved", "属性的实际访问器由运行时类型决定", node, method, conditions, background
        )
        return UNKNOWN
    if target.body is None:
        return ZERO
    return estimator.invoke(
        target,
        [],
        method,
        node,
        bindings,
        stack,
        conditions,
        background,
        argument_values={"value": value} if target.callable_kind == "property_set" else {},
        receiver_id=receiver_id,
    )


def read_property(estimator, node, method, bindings, stack, conditions, background):
    before = ZERO
    if node.type == "member_access_expression":
        before = estimator.expression(
            node.child_by_field_name("expression"), method, bindings, stack, conditions, background
        )
    getter = estimator.index.accessor(node, method, "get")
    started = bindings.get(CLOCK, ZERO)
    bindings[CLOCK] = started.plus(before)
    cost = accessor_cost(estimator, getter, node, method, bindings, stack, conditions, background)
    bindings[CLOCK] = started
    return before.plus(cost)


def assigned_value(current, right, operator):
    if operator == "=":
        return right
    if not all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in (current, right)
    ):
        return None

    try:
        operations = {
            "+=": lambda: current + right,
            "-=": lambda: current - right,
            "*=": lambda: current * right,
            "/=": lambda: (
                quotient(current, right)
                if isinstance(current, int) and isinstance(right, int)
                else current / right
            ),
        }
        value = operations[operator]() if operator in operations else None
        return value if value is not None and math.isfinite(value) else None
    except (ValueError, OverflowError, ZeroDivisionError):
        return None


def literal_getter(target):
    if target is None or target.body is None:
        return False
    parts = children(target.body)
    if target.body.type == "block":
        parts = children(parts[-1]) if parts and parts[-1].type == "return_statement" else []
    return bool(parts and parts[-1].type in {"integer_literal", "real_literal", "boolean_literal"})


def assign_property(
    estimator,
    node,
    method,
    bindings,
    stack,
    conditions,
    background,
    owner=None,
    receiver_id=state.MISSING,
):
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    operator = text(node.child_by_field_name("operator"))
    started = bindings.get(CLOCK, ZERO)
    before = ZERO
    place = None
    if left.type == "element_access_expression":
        before, place = evaluate_location(
            estimator, left, method, bindings, stack, conditions, background
        )
    if left.type == "member_access_expression":
        before = estimator.expression(
            left.child_by_field_name("expression"), method, bindings, stack, conditions, background
        )
    location_bindings = (
        bindings if receiver_id is state.MISSING else {**bindings, state.THIS: receiver_id}
    )
    member_place = state.location(estimator.index, left, method, location_bindings, owner)
    if operator != "=":
        getter = estimator.index.accessor(left, method, "get", owner)
        before = before.plus(
            accessor_cost(estimator, getter, left, method, bindings, stack, conditions, background)
        )
        current = (
            collections.item(*place, bindings)
            if place is not None
            else estimator.index.value(left, method, bindings)
        )
    bindings[CLOCK] = started.plus(before)
    before = before.plus(
        estimator.expression(right, method, bindings, stack, conditions, background)
    )
    value = estimator.index.value(right, method, bindings)
    from app.modules.action_timing.source_multicast import assignment

    callback = assignment(
        estimator.index,
        left,
        right,
        method,
        bindings,
        current if operator != "=" else None,
        operator,
    )
    if callback is not state.MISSING:
        value = callback
    elif operator != "=":
        value = assigned_value(current, value, operator)
    value, overflow = bounded(estimator.index, left, method, value)
    if overflow:
        estimator.record(
            "unresolved", "整数运算溢出，赋值结果未定", node, method, conditions, background
        )
        before = before.plus(UNKNOWN)
    setter = estimator.index.accessor(left, method, "set", owner)
    bindings[CLOCK] = started.plus(before)
    before = before.plus(
        accessor_cost(
            estimator,
            setter,
            left,
            method,
            bindings,
            stack,
            conditions,
            background,
            value,
            receiver_id=receiver_id,
        )
    )
    if setter is None and left.type == "member_access_expression":
        receiver_type = estimator.index.infer(left.child_by_field_name("expression"), method)
        if receiver_type not in estimator.index.classes and receiver_type.split(".")[-1] in {
            "Axis",
            "CamAxis",
            "Sensor",
            "Electric",
            "AKRSCamera",
        }:
            estimator.record(
                "call", "外部硬件属性写入的行为未解析", left, method, conditions, background
            )
            before = before.plus(UNKNOWN)
    getter = estimator.index.accessor(left, method, "get", owner)
    custom = (setter and setter.body is not None) or (getter and getter.body is not None)
    if place is not None:
        collections.write(place, value, bindings)
    elif left.type == "element_access_expression" and state.WRITES in bindings:
        # 排队回调中的集合内容可能已变化；缺少实例也不能让调用者保留旧元素。
        state.write(estimator.index, left.child_by_field_name("expression"), method, bindings, None)
    elif not custom:
        target_bindings = (
            bindings if receiver_id is state.MISSING else {**bindings, state.THIS: receiver_id}
        )
        if callback is not state.MISSING and member_place is not None:
            state.write_location(member_place, target_bindings, value)
        else:
            state.write(estimator.index, left, method, target_bindings, value, owner)
        if target_bindings is not bindings:
            state.transfer(bindings, target_bindings)
    elif setter and estimator.index.polymorphic(left, method, setter):
        state.write(estimator.index, left, method, bindings, None, owner)
    track_binding(
        estimator.index,
        left,
        right if operator == "=" and not custom else None,
        method,
        bindings,
        assigned_delegate=callback if not custom else state.MISSING,
    )
    bindings[CLOCK] = started
    bindings[call_args.return_key(node, method, bindings)] = value
    return before


def increment_property(estimator, node, method, bindings, stack, conditions, background):
    operand = children(node)[-1]
    started = bindings.get(CLOCK, ZERO)
    place = None
    if operand.type == "element_access_expression":
        cost, place = evaluate_location(
            estimator, operand, method, bindings, stack, conditions, background
        )
    else:
        cost = read_property(estimator, operand, method, bindings, stack, conditions, background)
    previous = (
        collections.item(*place, bindings)
        if place is not None
        else estimator.index.value(operand, method, bindings)
    )
    value = previous
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value += 1 if "++" in text(node) else -1
    else:
        value = None
    value, overflow = bounded(estimator.index, operand, method, value)
    if overflow:
        estimator.record(
            "unresolved", "整数自增溢出，结果未定", node, method, conditions, background
        )
        cost = cost.plus(UNKNOWN)
    setter = estimator.index.accessor(operand, method, "set")
    bindings[CLOCK] = started.plus(cost)
    cost = cost.plus(
        accessor_cost(
            estimator, setter, operand, method, bindings, stack, conditions, background, value
        )
    )
    if place is not None:
        collections.write(place, value, bindings)
    elif setter is None or setter.body is None:
        state.write(estimator.index, operand, method, bindings, value)
    bindings[CLOCK] = started
    bindings[call_args.return_key(node, method, bindings)] = (
        previous if node.type == "postfix_unary_expression" else value
    )
    return cost
