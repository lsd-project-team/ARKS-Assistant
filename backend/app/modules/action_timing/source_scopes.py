"""重复进入的源码作用域使用新变量槽，闭包仍可持有已经退出的槽。"""

from contextlib import contextmanager

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import children, text


def declarations(node):
    result = []
    for statement in children(node, "local_declaration_statement"):
        for declaration in children(statement, "variable_declaration"):
            result.extend(
                text(item.child_by_field_name("name"))
                for item in children(declaration, "variable_declarator")
                if item.child_by_field_name("name") is not None
            )
    return result


@contextmanager
def local_scope(estimator, names, bindings):
    estimator.scope_frames += 1
    before = {}
    for name in names:
        for key in (
            name,
            f"{state.LOCAL_ALIAS}{name}>",
            f"<delegate-variable:{name}>",
            f"<task-variable:{name}>",
        ):
            before[key] = bindings.get(key, state.MISSING)
        slot = (
            f"{state.LOCAL_PREFIX}{bindings.get(state.FRAME)}"
            f"|scope:{estimator.scope_frames}|{name}>"
        )
        bindings[f"{state.LOCAL_ALIAS}{name}>"] = slot
        bindings[name] = None
    try:
        yield
    finally:
        for key, value in before.items():
            if value is state.MISSING:
                bindings.pop(key, None)
            else:
                bindings[key] = value
