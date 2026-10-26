"""条件组成的纯数值投影：常量、未改写局部量与互斥表达式；不执行源码。"""

from dataclasses import replace
from itertools import product

from app.modules.action_timing import source_components as components
from app.modules.action_timing.source_index import children, text, value_children
from app.modules.action_timing.source_numbers import binary_value

MAX_VARIANTS = 128


def constant(index, node, method):
    name = (
        text(node.child_by_field_name("name"))
        if node.type == "member_access_expression"
        else text(node)
    )
    owner = (
        index.infer(node.child_by_field_name("expression"), method)
        if node.type == "member_access_expression"
        else method.owner
    )
    for candidate in [owner, *index.base_types(owner)]:
        info = index.classes.get(candidate)
        if not info or name not in info.defaults:
            continue
        unit, value = info.defaults[name]
        parent = value.parent
        while parent is not None and parent.type not in {"field_declaration", "class_declaration"}:
            parent = parent.parent
        if parent is not None and any(text(p) == "const" for p in children(parent, "modifier")):
            return value, candidate, unit
    return None


def variants(index, node, method, bindings, before, seen=frozenset()):
    if node is None:
        return []
    kind = node.type
    if kind in {"integer_literal", "real_literal", "boolean_literal"}:
        return [(index.value(node, method, {}), [])]
    if kind in {"argument", "parenthesized_expression", "constant_pattern"}:
        parts = value_children(node)
        return variants(index, parts[-1] if parts else None, method, bindings, before, seen)
    if kind in {"identifier", "member_access_expression"}:
        name = text(node)
        if name in seen:
            return []
        if name in bindings and components.unchanged(method, name):
            return [(bindings[name], [])]
        # 局部量/形参遮蔽同名常量；不能跳过未知局部量去读取类字段。
        declared = (
            constant(index, node, method)
            if kind != "identifier" or name not in method.types
            else None
        )
        if declared is not None:
            value, owner, unit = declared
            context = replace(
                method,
                owner=owner,
                unit=unit,
                node=value,
                body_node=value,
                body_override=None,
                types={},
                initializers={},
                parameters=[],
            )
            return variants(index, value, context, {}, before, seen | {name})
        value = None
        if value is None and kind == "identifier" and components.unchanged(method, name):
            value = method.initializers.get(name)
            if value is not None and not (
                method.body.start_byte <= value.start_byte < value.end_byte <= before.start_byte
            ):
                value = None
            scope = value.parent if value is not None else None
            while scope is not None and scope.type not in {
                "block",
                "lambda_expression",
                "method_declaration",
            }:
                scope = scope.parent
            if scope is not None and not scope.start_byte <= before.start_byte < scope.end_byte:
                value = None
        return (
            variants(index, value, method, bindings, before, seen | {name})
            if value is not None
            else []
        )
    if kind == "conditional_expression":
        condition = node.child_by_field_name("condition")
        selector = variants(index, condition, method, bindings, before, seen)
        known = selector[0][0] if len(selector) == 1 and isinstance(selector[0][0], bool) else None
        return [
            (value, [text(condition) if flag else f"!({text(condition)})", *labels])
            for flag, field in [(True, "consequence"), (False, "alternative")]
            if known is None or known == flag
            for value, labels in variants(
                index, node.child_by_field_name(field), method, bindings, before, seen
            )
        ]
    if kind == "switch_expression":
        parts = children(node)
        selector = variants(index, parts[0], method, bindings, before, seen)
        known = selector[0][0] if len(selector) == 1 else None
        result = []
        for arm in children(node, "switch_expression_arm"):
            nodes = children(arm)
            pattern, value_node = nodes[0], nodes[-1]
            match = variants(index, pattern, method, bindings, before, seen)
            wildcard = text(pattern) == "_"
            if known is not None and (not wildcard and (not match or match[0][0] != known)):
                continue
            guard = next(iter(children(arm, "when_clause")), None)
            guarded = (
                variants(index, children(guard)[-1], method, bindings, before, seen)
                if guard is not None and children(guard)
                else []
            )
            if len(guarded) == 1 and guarded[0][0] is False:
                continue
            result.extend(
                (
                    value,
                    [f"{text(parts[0])} switch：{text(arm).rsplit('=>', 1)[0].strip()}", *labels],
                )
                for value, labels in variants(index, value_node, method, bindings, before, seen)
            )
            if known is not None and (guard is None or len(guarded) == 1 and guarded[0][0] is True):
                break
        return result
    if kind == "binary_expression":
        left = variants(index, node.child_by_field_name("left"), method, bindings, before, seen)
        right = variants(index, node.child_by_field_name("right"), method, bindings, before, seen)
        if len(left) * len(right) > MAX_VARIANTS:
            index.__dict__.setdefault("component_expression_limits", {})[
                (method.key, node.start_byte)
            ] = {
                "method": method.key,
                "path": method.unit.path,
                "line": node.start_point[0] + 1,
            }
            return []
        return [
            (value, [*lc, *rc])
            for (lv, lc), (rv, rc) in product(left, right)
            if (value := binary_value(text(node.child_by_field_name("operator")), lv, rv))
            is not None
        ]
    if kind == "prefix_unary_expression":
        parts = children(node)
        operator = text(node).strip()[:1]
        if text(node).lstrip().startswith(("++", "--")) or not parts:
            return []
        values = variants(index, parts[-1], method, bindings, before, seen)
        if operator == "!":
            return [(not value, labels) for value, labels in values if isinstance(value, bool)]
        if operator in {"-", "+"}:
            return [
                (value * (-1 if operator == "-" else 1), labels)
                for value, labels in values
                if components.number(value)
            ]
    return []
