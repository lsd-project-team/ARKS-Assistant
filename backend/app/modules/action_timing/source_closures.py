"""闭包用共享变量槽跨方法传递，执行时的新局部变量保持独立。"""

from dataclasses import dataclass, replace

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO
from app.modules.action_timing.source_index import children, text, walk


@dataclass(frozen=True)
class Closure:
    method: object
    receiver: object
    cells: tuple
    functions: object = None


def capture(method, bindings, node):
    from app.modules.action_timing.source_local_functions import lexical_walk

    cells = []
    declared = {name for name, _, _ in parameters(node)}
    declared.update(
        text(part.child_by_field_name("name"))
        for part in lexical_walk(node)
        if part.type in {"variable_declarator", "declaration_expression"}
    )
    used = {
        text(part)
        for part in walk(node)
        if part.type == "identifier" and text(part) not in declared
    }
    for name in method.types:
        if name not in used:
            continue
        initial = method.initializers.get(name)
        if name not in bindings or (
            initial is not None
            and initial.start_byte > node.start_byte
            and f"{state.LOCAL_ALIAS}{name}>" not in bindings
        ):
            continue
        key = bindings.get(
            f"{state.LOCAL_ALIAS}{name}>",
            f"{state.LOCAL_PREFIX}{bindings.get(state.FRAME)}|{name}>",
        )
        if key not in bindings:
            bindings[key] = bindings.get(name)
        cells.append((name, key))
    return Closure(
        replace(method, types=dict(method.types)),
        bindings.get(state.THIS),
        tuple(cells),
        bindings.get(state.LOCAL_FUNCTIONS),
    )


def returned(index, node, method, bindings):
    """返回lambda时用返回签名完成一次绑定；此时仍不执行lambda正文。"""
    from app.modules.action_timing import source_delegates as delegates

    while node is not None and node.type in {"arrow_expression_clause", "parenthesized_expression"}:
        node = children(node)[-1] if children(node) else None
    if node is not None and node.type in {"lambda_expression", "anonymous_method_expression"}:
        return delegates.capture(index, node, method, bindings, signature_kind=method.return_type)
    return index.value(node, method, bindings)


def parameters(node):
    source = node.child_by_field_name("parameters") or node.child_by_field_name("parameter")
    if source is None:
        return []
    nodes = [source] if source.type in {"implicit_parameter", "identifier"} else children(source)
    return [
        (
            text(part.child_by_field_name("name")) or text(part),
            text(part.child_by_field_name("type")) or "var",
            None,
        )
        for part in nodes
    ]


def enter(estimator, bound, node, bindings, values, argument_types=()):
    from app.modules.action_timing.source_local_functions import declared_locals
    from app.modules.action_timing.source_tasks import CLOCK

    closure = bound.closure
    args = parameters(node)
    args = [
        (
            name,
            argument_types[position] if kind == "var" and position < len(argument_types) else kind,
            default,
        )
        for position, (name, kind, default) in enumerate(args)
    ]
    estimator.frames += 1
    local_types, local_values = declared_locals(node)
    method = replace(
        closure.method,
        name=f"<callback:{node.start_byte}>",
        node=node,
        types={**closure.method.types, **local_types, **{name: kind for name, kind, _ in args}},
        parameters=args,
        body_override=None,
        body_node=node.child_by_field_name("body"),
        initializers={
            **local_values,
            **{
                name: value
                for name, value in closure.method.initializers.items()
                if name not in {arg[0] for arg in args} and name not in local_values
            },
        },
        callable_kind="delegate",
        variadic=False,
    )
    scope = {
        **estimator.context,
        **state.context(bindings),
        state.THIS: closure.receiver,
        state.FRAME: str(estimator.frames),
        state.LOCAL_FUNCTIONS: closure.functions,
        CLOCK: bindings.get(CLOCK, ZERO),
        **{name: bindings.get(key) for name, key in closure.cells},
        **{f"{state.LOCAL_ALIAS}{name}>": key for name, key in closure.cells},
    }
    for (name, _, _), value in zip(args, values, strict=True):
        scope.pop(f"{state.LOCAL_ALIAS}{name}>", None)
        scope[name] = value
    return method, scope
