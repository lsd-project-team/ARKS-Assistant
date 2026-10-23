"""本地函数的词法绑定；声明不执行，退出块后的委托保留原捕获环境。"""

from contextlib import contextmanager
from dataclasses import dataclass, field, replace

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_closures as closures
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN
from app.modules.action_timing.source_index import children, initializer, simple_type, text

KINDS = {"local_function_statement", "local_function_declaration"}


def lexical_walk(node):
    pending = [node] if node is not None else []
    while pending:
        current = pending.pop()
        yield current
        pending.extend(
            child
            for child in reversed(children(current))
            if child.type not in KINDS | {"lambda_expression", "anonymous_method_expression"}
        )


def timing_walk(node):
    """lambda沿用目录的保守候选扫描，本地函数只在解析到调用后进入。"""
    pending = [node] if node is not None else []
    while pending:
        current = pending.pop()
        yield current
        pending.extend(part for part in reversed(children(current)) if part.type not in KINDS)


def declared_locals(node):
    types, values = {}, {}
    for part in lexical_walk(node):
        if part.type == "variable_declaration":
            kind = text(part.child_by_field_name("type"))
            for variable in children(part, "variable_declarator"):
                name = text(variable.child_by_field_name("name"))
                types[name], values[name] = kind, initializer(variable)
        elif part.type == "declaration_expression":
            name = text(part.child_by_field_name("name"))
            if name and name != "_":
                types[name], values[name] = text(part.child_by_field_name("type")), None
    return types, values


def definition(index, node, method, name=None):
    name = text(node) if name is None else name
    if name not in index.local_function_names:
        return None
    cache = index.__dict__.setdefault("local_function_definitions", {})
    key = (method.unit.path, node.start_byte, node.end_byte, name)
    if key not in cache:
        current, found = node.parent, None
        while current is not None:
            if current.type in {"block", "switch_section"}:
                found = next(
                    (
                        part
                        for part in children(current)
                        if part.type in KINDS and text(part.child_by_field_name("name")) == name
                    ),
                    None,
                )
                if found is not None:
                    break
            if current.type in {
                "method_declaration",
                "constructor_declaration",
                "accessor_declaration",
            }:
                break
            current = current.parent
        cache[key] = found
    return cache[key]


def describe(index, node, outer):
    params, variadic = arguments.declared_parameters(node)
    types, initializers = dict(outer.types), dict(outer.initializers)
    own_types, own_values = declared_locals(node)
    types.update(own_types)
    initializers.update(own_values)
    for name, kind, _ in params:
        types[name] = kind
        initializers.pop(name, None)
    result = replace(
        outer,
        name=f"<local:{text(node.child_by_field_name('name'))}:{node.start_byte}>",
        node=node,
        parameters=params,
        types=types,
        initializers=initializers,
        body_override=None,
        body_node=node.child_by_field_name("body"),
        callable_kind="local_function",
        is_virtual=False,
        is_static=outer.is_static
        or any(text(part) == "static" for part in children(node, "modifier")),
        variadic=variadic,
        type_scope=tuple(sorted(types.items())),
    )
    if hasattr(index, "method_kinds"):
        index.method_kinds[result.key] = "local_function"
    return result


def identity(node, method):
    return (method.unit.path, node.start_byte, node.end_byte)


@dataclass(eq=False)
class Environment:
    parent: object = None
    functions: dict = field(default_factory=dict)

    def get(self, key):
        current = self
        while isinstance(current, Environment):
            if key in current.functions:
                return current.functions[key]
            current = current.parent
        return None


def bind(index, node, method, bindings):
    captured_types = dict(method.types)
    for part in lexical_walk(node):
        if part.type == "identifier" and (kind := index.local_type(part, method)):
            captured_types[text(part)] = kind
    method = replace(method, types=captured_types)
    closure = closures.capture(method, bindings, node)
    target = describe(index, node, method)
    explicitly_static = any(text(part) == "static" for part in children(node, "modifier"))
    if explicitly_static:
        from app.modules.action_timing.source_dispatch import constant_local

        if any(not constant_local(method, name) for name, _ in closure.cells):
            return None
        owned = set(declared_locals(node)[0]) | {name for name, _, _ in target.parameters}
        for part in lexical_walk(node):
            if any(child.type in {"this", "base"} for child in part.children):
                return None
            if part.type == "identifier" and text(part) not in owned:
                parent = part.parent
                selector = (
                    parent is not None
                    and parent.type == "member_access_expression"
                    and parent.child_by_field_name("name") == part
                )
                member = state.member(index, method.owner, text(part))
                if not selector and member is not None and not member[1]:
                    return None
            if (
                part.type == "invocation_expression"
                and part.child_by_field_name("function").type == "identifier"
            ):
                called = index.resolve(part, method)
                if (
                    called is not None
                    and not called.is_static
                    and not (node.start_byte <= called.node.start_byte < node.end_byte)
                ):
                    return None
    if target.is_static:
        closure = replace(closure, receiver=None)
    return delegates.BoundDelegate(
        node,
        method.key,
        closure.receiver,
        closure,
        len(target.parameters),
        simple_type(target.return_type) == "Task",
        any(text(part) == "async" for part in children(node, "modifier"))
        and target.return_type == "void",
    )


def restore(bindings, previous):
    if previous is state.MISSING:
        bindings.pop(state.LOCAL_FUNCTIONS, None)
    else:
        bindings[state.LOCAL_FUNCTIONS] = previous


@contextmanager
def scope(estimator, node, method, bindings):
    previous = bindings.get(state.LOCAL_FUNCTIONS, state.MISSING)
    declarations = [part for part in children(node) if part.type in KINDS]
    if declarations:
        environment = Environment(None if previous is state.MISSING else previous)
        bindings[state.LOCAL_FUNCTIONS] = environment
        for declaration in declarations:
            environment.functions[identity(declaration, method)] = bind(
                estimator.index, declaration, method, bindings
            )
    try:
        yield previous
    finally:
        restore(bindings, previous)


def value(index, node, method, bindings):
    if node is None or node.type != "identifier":
        return state.MISSING
    parent = node.parent
    if (
        parent is not None
        and parent.type == "member_access_expression"
        and parent.child_by_field_name("name") == node
    ):
        return state.MISSING
    declaration = definition(index, node, method)
    if declaration is None:
        return state.MISSING
    environment = bindings.get(state.LOCAL_FUNCTIONS)
    return (
        environment.get(identity(declaration, method))
        if isinstance(environment, Environment)
        else None
    )


def captures(bound, bindings):
    return {
        state.LOCAL_FUNCTIONS: bound.closure.functions,
        **{name: bindings.get(slot) for name, slot in bound.closure.cells},
        **{f"{state.LOCAL_ALIAS}{name}>": slot for name, slot in bound.closure.cells},
    }


def environment_functions(bound, bindings):
    pending = [bindings.get(state.LOCAL_FUNCTIONS), bound.closure.functions]
    seen, result = set(), []
    while pending:
        environment = pending.pop()
        if not isinstance(environment, Environment) or id(environment) in seen:
            continue
        seen.add(id(environment))
        result.extend(
            value
            for value in environment.functions.values()
            if isinstance(value, delegates.BoundDelegate)
        )
        pending.append(environment.parent)
    return result


def call(estimator, node, method, bindings, stack, conditions, background):
    function = node.child_by_field_name("function")
    if function is None or function.type != "identifier":
        return None
    declaration = definition(estimator.index, function, method)
    if declaration is None:
        return None
    bound = value(estimator.index, function, method, bindings)
    if not isinstance(bound, delegates.BoundDelegate):
        estimator.record(
            "unresolved", "本地函数的词法环境未绑定", node, method, conditions, background
        )
        return UNKNOWN
    target = describe(estimator.index, declaration, bound.closure.method)
    return estimator.invoke(
        target,
        arguments.arguments(node),
        method,
        node,
        bindings,
        stack,
        conditions,
        background,
        receiver_id=bound.closure.receiver,
        captures=captures(bound, bindings),
    )
