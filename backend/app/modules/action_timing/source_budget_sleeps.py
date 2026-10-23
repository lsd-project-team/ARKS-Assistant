"""调用额度用尽时，只保留无需执行子方法即可证明的必经字面量等待。"""

import re

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import Cost
from app.modules.action_timing.source_index import children, text, value_children
from app.modules.action_timing.source_numbers import literal, literal_type
from app.modules.action_timing.source_references import ancestors, invalidate_values


def invalidate(estimator, target, node, caller, bindings, receiver, supplied):
    """没有执行正文，接收对象、引用实参及本类型静态成员不能沿用旧值。"""
    values = list(arguments.values(estimator.index, node, caller, bindings))
    values.extend((supplied or {}).values())
    if receiver is state.MISSING:
        saved = arguments.snapshot(node, caller, bindings)
        receiver = saved.receiver if saved else state.MISSING
    if receiver is state.MISSING:
        receiver = state.receiver_for(estimator.index, target, node, caller, bindings)
    if receiver is not None:
        values.append({"<ref>": receiver})
    invalidate_values(values, bindings)
    state.invalidate_byref(estimator.index, node, caller, bindings)
    if target.is_static:
        keys = {
            state.key(("static", owner, name))
            for owner in ancestors(estimator.index, target.owner)
            if (info := estimator.index.classes.get(owner)) is not None
            for name in info.static_members
        }
        bindings[state.UNSTABLE] = (bindings.get(state.UNSTABLE) or frozenset()) | keys


def unsafe_expression(statement):
    pending = [statement]
    while pending:
        part = pending.pop()
        if part.type in {"lambda_expression", "anonymous_method_expression"}:
            continue  # 创建委托不表示已执行其正文。
        if part.type in {"await_expression", "throw_expression"}:
            return True
        pending.extend(children(part))
    return False


def sleep_value(index, method, node):
    function = re.sub(r"\s+", "", text(node.child_by_field_name("function")))
    function = function.removeprefix("global::")
    if function not in {"Thread.Sleep", "System.Threading.Thread.Sleep"}:
        return None, False
    kind = function.removesuffix(".Sleep")
    if (
        index.resolve(node, method) is not None
        or index.lookup_type(kind, method) in index.classes
        or (kind == "Thread" and "Thread" in method.types)
        or (kind == "Thread" and re.search(rb"\busing\s+Thread\s*=", method.unit.raw))
    ):
        return None, False
    nodes = arguments.arguments(node)
    if len(nodes) != 1 or arguments.argument_name(nodes[0]) not in {None, "millisecondsTimeout"}:
        return None, True
    values = value_children(nodes[0])
    value = values[-1] if values else None
    while value is not None and value.type == "parenthesized_expression":
        parts = value_children(value)
        value = parts[-1] if parts else None
    if value is None:
        return None, True
    if value.type != "integer_literal":
        invalid = value.type in {
            "real_literal",
            "boolean_literal",
            "string_literal",
            "null_literal",
        }
        if value.type == "prefix_unary_expression":
            parts = value_children(value)
            invalid |= (
                text(value).startswith("-")
                and bool(parts)
                and parts[-1].type in {"integer_literal", "real_literal"}
            )
        return None, invalid
    if literal_type(text(value)) != "int":
        return None, True
    duration = literal(text(value))
    return (
        duration if duration is not None and duration >= 0 else None
    ), duration is None or duration < 0


def templates(index, method):
    body = method.body
    if (
        method.callable_kind != "method"
        or body is None
        or body.type not in {"block", "arrow_expression_clause"}
        or any(text(part) == "async" for part in method.node.children)
    ):
        return ()
    if body.type == "arrow_expression_clause":
        parts = value_children(body)
        node = parts[-1] if parts else None
        if node is None or node.type != "invocation_expression":
            return ()
        duration, blocked = sleep_value(index, method, node)
        return ((node, duration),) if duration is not None and not blocked else ()
    result = []
    for statement in children(body):
        if statement.type in {"comment", "local_function_statement", "local_function_declaration"}:
            continue
        if statement.type not in {"expression_statement", "local_declaration_statement"}:
            break  # 首个分支、循环或出口之后的语句不能当作必经路径。
        if unsafe_expression(statement):
            break
        parts = value_children(statement)
        node = parts[0] if statement.type == "expression_statement" and parts else None
        if node is None or node.type != "invocation_expression":
            continue
        target = index.resolve(node, method)
        if target is not None and target.key == method.key:
            break
        duration, blocked = sleep_value(index, method, node)
        if blocked:
            break
        if duration is not None:
            result.append((node, duration))
    return tuple(result)


def preserve(estimator, method, conditions, background):
    identity = (method.key, method.type_scope)
    cache = estimator.literal_wait_summaries
    if identity not in cache:
        cache[identity] = templates(estimator.index, method)
    lower = 0
    for node, duration in cache[identity]:
        estimator.record(
            "delay",
            "调用受限，保留正常完成必经固定等待",
            node,
            method,
            conditions,
            background,
            milliseconds=duration,
            budget_summary=True,
        )
        lower += duration
    return Cost(lower, None) if cache[identity] else None
