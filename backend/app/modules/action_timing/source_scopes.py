"""重复进入的源码作用域使用新变量槽，闭包仍可持有已经退出的槽。"""

from contextlib import contextmanager

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import children, text

CALLABLES = {
    "lambda_expression",
    "anonymous_method_expression",
    "local_function_statement",
    "local_function_declaration",
}
SPACES = {
    "block",
    "switch_body",
    "switch_section",
    "for_statement",
    "while_statement",
    "do_statement",
    "foreach_statement",
    "for_each_statement",
    "using_statement",
    "catch_clause",
} | CALLABLES


def inline_declarations(node, index=None):
    """out声明属于最近的声明空间；不越过内层块、循环或匿名函数。"""
    if node is None:
        return ()
    cache = index.__dict__.setdefault("inline_declaration_cache", {}) if index else None
    identity = node
    if cache is not None and identity in cache:
        return cache[identity]
    pending, result = [node], []
    while pending:
        current = pending.pop()
        if current.type == "declaration_expression":
            name = current.child_by_field_name("name")
            if name is not None and name.type == "identifier" and text(name) != "_":
                result.append(current)
        for part in reversed(children(current)):
            if part.type in SPACES:
                continue
            if current.type == "if_statement" and part in {
                current.child_by_field_name("consequence"),
                current.child_by_field_name("alternative"),
            }:
                continue
            if part == current.child_by_field_name("body") and current.type in {
                "for_statement",
                "while_statement",
                "do_statement",
                "foreach_statement",
                "for_each_statement",
                "using_statement",
                "lock_statement",
            }:
                continue
            pending.append(part)
    value = tuple(result)
    if cache is not None:
        cache[identity] = value
    return value


def inline_names(node, index=None):
    return [text(part.child_by_field_name("name")) for part in inline_declarations(node, index)]


def embedded(node):
    parent = node.parent if node is not None else None
    if parent is None or node.type == "block":
        return False
    return (
        parent.type == "if_statement"
        and node
        in {parent.child_by_field_name("consequence"), parent.child_by_field_name("alternative")}
    ) or (
        parent.type
        in {
            "for_statement",
            "while_statement",
            "do_statement",
            "foreach_statement",
            "for_each_statement",
            "using_statement",
            "lock_statement",
        }
        and node == parent.child_by_field_name("body")
    )


def declarations(node, index=None):
    result = inline_names(node, index)
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
        yield before
    finally:
        restore(bindings, before)


def restore(bindings, before):
    for key, value in before.items():
        if value is state.MISSING:
            bindings.pop(key, None)
        else:
            bindings[key] = value
