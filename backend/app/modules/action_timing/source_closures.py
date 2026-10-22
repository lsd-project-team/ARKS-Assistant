"""闭包用共享变量槽跨方法传递，执行时的新局部变量保持独立。"""

from dataclasses import dataclass, replace

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO
from app.modules.action_timing.source_index import children, text


@dataclass(frozen=True)
class Closure:
    method: object
    receiver: object
    cells: tuple


def capture(method, bindings, node):
    cells = []
    for name in method.types:
        initial = method.initializers.get(name)
        if name not in bindings or (initial is not None and initial.start_byte > node.start_byte):
            continue
        key = bindings.get(
            f"{state.LOCAL_ALIAS}{name}>",
            f"{state.LOCAL_PREFIX}{bindings.get(state.FRAME)}|{name}>",
        )
        if key not in bindings:
            bindings[key] = bindings.get(name)
        cells.append((name, key))
    return Closure(method, bindings.get(state.THIS), tuple(cells))


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


def enter(estimator, bound, node, bindings, values):
    from app.modules.action_timing.source_tasks import CLOCK

    closure = bound.closure
    args = parameters(node)
    estimator.frames += 1
    method = replace(
        closure.method,
        name=f"<callback:{node.start_byte}>",
        node=node,
        types={**closure.method.types, **{name: kind for name, kind, _ in args}},
        parameters=args,
        body_override=None,
        body_node=node.child_by_field_name("body"),
        initializers={
            name: value
            for name, value in closure.method.initializers.items()
            if name not in {arg[0] for arg in args}
        },
        callable_kind="delegate",
    )
    scope = {
        **estimator.context,
        **state.context(bindings),
        state.THIS: closure.receiver,
        state.FRAME: str(estimator.frames),
        CLOCK: bindings.get(CLOCK, ZERO),
        **{name: bindings.get(key) for name, key in closure.cells},
        **{f"{state.LOCAL_ALIAS}{name}>": key for name, key in closure.cells},
    }
    for (name, _, _), value in zip(args, values, strict=True):
        scope.pop(f"{state.LOCAL_ALIAS}{name}>", None)
        scope[name] = value
    return method, scope
