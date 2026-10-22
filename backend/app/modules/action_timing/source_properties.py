"""属性访问器也可能执行动作；读、写及复合赋值分别计算。"""

import math

from app.modules.action_timing.source_flow import UNKNOWN, ZERO
from app.modules.action_timing.source_index import children, text
from app.modules.action_timing.source_tasks import CLOCK


def accessor_cost(
    estimator, target, node, method, bindings, stack, conditions, background, value=None
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
                math.trunc(current / right)
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


def assign_property(estimator, node, method, bindings, stack, conditions, background, owner=None):
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")
    operator = text(node.child_by_field_name("operator"))
    started = bindings.get(CLOCK, ZERO)
    before = ZERO
    if left.type == "member_access_expression":
        before = estimator.expression(
            left.child_by_field_name("expression"), method, bindings, stack, conditions, background
        )
    value = estimator.index.value(right, method, bindings)
    if operator != "=":
        current = estimator.index.value(left, method, bindings)
        getter = estimator.index.accessor(left, method, "get", owner)
        before = before.plus(
            accessor_cost(estimator, getter, left, method, bindings, stack, conditions, background)
        )
        value = assigned_value(current, value, operator)
    bindings[CLOCK] = started.plus(before)
    before = before.plus(
        estimator.expression(right, method, bindings, stack, conditions, background)
    )
    setter = estimator.index.accessor(left, method, "set", owner)
    bindings[CLOCK] = started.plus(before)
    before = before.plus(
        accessor_cost(
            estimator, setter, left, method, bindings, stack, conditions, background, value
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
    if owner is None:
        getter = estimator.index.accessor(left, method, "get")
        custom = (setter and setter.body is not None) or (getter and getter.body is not None)
        if custom and literal_getter(getter):
            bindings.pop(text(left), None)
        else:
            bindings[text(left)] = None if custom else value
        if left.type == "member_access_expression":
            receiver = left.child_by_field_name("expression")
            state = estimator.index.value(receiver, method, bindings)
            if receiver.type == "identifier" and isinstance(state, dict):
                bindings[text(receiver)] = {**state, text(left.child_by_field_name("name")): value}
    bindings[CLOCK] = started
    return before


def increment_property(estimator, node, method, bindings, stack, conditions, background):
    operand = children(node)[-1]
    started = bindings.get(CLOCK, ZERO)
    value = estimator.index.value(operand, method, bindings)
    cost = read_property(estimator, operand, method, bindings, stack, conditions, background)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        value += 1 if "++" in text(node) else -1
    else:
        value = None
    setter = estimator.index.accessor(operand, method, "set")
    bindings[CLOCK] = started.plus(cost)
    cost = cost.plus(
        accessor_cost(
            estimator, setter, operand, method, bindings, stack, conditions, background, value
        )
    )
    getter = estimator.index.accessor(operand, method, "get")
    if setter and setter.body is not None:
        if literal_getter(getter):
            bindings.pop(text(operand), None)
        else:
            bindings[text(operand)] = None
    else:
        bindings[text(operand)] = value
    bindings[CLOCK] = started
    return cost
