"""已绑定Delegate的反射调用；仅解释签名、参数与返回值，不执行运行库反射。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN
from app.modules.action_timing.source_index import children, simple_type, text
from app.modules.action_timing.source_numbers import NUMERIC_TYPES


def signature(index, kind, method):
    kind = "".join(kind.split()).removeprefix("global::")
    base, separator, content = kind.partition("<")
    special = {
        "MethodInvoker": ((), "void"),
        "System.Windows.Forms.MethodInvoker": ((), "void"),
        "SendOrPostCallback": (("object",), "void"),
        "System.Threading.SendOrPostCallback": (("object",), "void"),
    }
    if kind in special and index.lookup_type(base, method) not in index.classes:
        return special[kind]
    if base not in {"Action", "System.Action", "Func", "System.Func"}:
        return None
    if index.lookup_type(base, method) in index.classes:
        return None
    if not separator:
        return ((), "void") if simple_type(base) == "Action" else None
    if not content.endswith(">"):
        return None
    parts, start, depth = [], 0, 0
    for position, char in enumerate(content[:-1]):
        depth += (char in "<[(") - (char in ">])")
        if char == "," and depth == 0:
            parts.append(content[start:position])
            start = position + 1
    parts.append(content[start:-1])
    return (
        (tuple(parts), "void") if simple_type(base) == "Action" else (tuple(parts[:-1]), parts[-1])
    )


def explicit_signature(index, node, method):
    while node is not None:
        if node.type in {"argument", "parenthesized_expression"}:
            parts = children(node)
            node = parts[-1] if parts else None
        elif node.type in {"cast_expression", "object_creation_expression"}:
            kind = text(node.child_by_field_name("type"))
            if signature(index, kind, method) is not None:
                return kind
            if node.type == "object_creation_expression":
                break
            node = node.child_by_field_name("value")
        else:
            kind = collections.raw_type(index, node, method)
            return kind if signature(index, kind, method) is not None else ""
    return ""


def prefer_typed_callback(index, methods, nodes, caller):
    """匿名回调的具体委托优于通用Delegate；多个具体委托之间仍保留歧义。"""
    from app.modules.action_timing import source_closures as closures

    for position, node in enumerate(nodes):
        value = unwrapped(node)
        if value is None or value.type not in {"lambda_expression", "anonymous_method_expression"}:
            continue
        groups = []
        for method in methods:
            slots = call_args.plan(method.parameters, nodes, variadic=method.variadic)
            kind = method.parameters[slots[position]][1]
            shape = signature(index, kind, method)
            groups.append((method, shape, kind))
        # 其他实参也必须具有相同的参数目标；不能仅凭委托更具体忽略不同转换。
        if any(
            len(
                {
                    method.parameters[
                        call_args.plan(method.parameters, nodes, variadic=method.variadic)[other]
                    ][1]
                    for method in methods
                }
            )
            != 1
            for other in range(len(nodes))
            if other != position
        ):
            continue
        concrete = [
            method
            for method, shape, _ in groups
            if shape is not None and len(shape[0]) == len(closures.parameters(value))
        ]
        generic = {"Delegate", "System.Delegate", "MulticastDelegate", "System.MulticastDelegate"}
        if len(concrete) == 1 and all(
            method is concrete[0] or kind in generic for method, _, kind in groups
        ):
            return concrete
    return methods


def receiver(node):
    function = node.child_by_field_name("function")
    if function is None:
        return None
    if function.type == "conditional_access_expression":
        member = next(iter(children(function, "member_binding_expression")), None)
        name = text(member.child_by_field_name("name")) if member else ""
        return function.child_by_field_name("condition") if name == "DynamicInvoke" else None
    return (
        function.child_by_field_name("expression")
        if text(function.child_by_field_name("name")) == "DynamicInvoke"
        else None
    )


def operation(index, node, method):
    target = receiver(node)
    kind = index.infer(target, method)
    return (
        target is not None
        and kind not in index.classes
        and simple_type(kind)
        in {
            "Action",
            "Func",
            "Delegate",
            "MulticastDelegate",
            "MethodInvoker",
            "SendOrPostCallback",
        }
    )


def unwrapped(node):
    while node is not None and node.type in {"argument", "parenthesized_expression"}:
        parts = children(node)
        node = parts[-1] if parts else None
    return node


def argument_type(index, node, method):
    node = unwrapped(node)
    if node is None:
        return ""
    return (
        text(node.child_by_field_name("type"))
        if node.type == "cast_expression"
        else (collections.raw_type(index, node, method) or index.infer(node, method))
    )


def arguments(index, node, method, bindings):
    nodes = call_args.arguments(node)
    return argument_values(
        index, nodes, call_args.values(index, node, method, bindings), method, bindings
    )


def argument_values(index, nodes, values, method, bindings):
    names = [call_args.argument_name(part) for part in nodes]
    if any(names) and (len(nodes) != 1 or names != ["args"]):
        return None
    types = tuple(argument_type(index, part, method) for part in nodes)
    if not nodes or (len(nodes) == 1 and text(unwrapped(nodes[0])) == "null"):
        return (), ()
    if len(nodes) == 1 and reference_array(index, types[0], method):
        data = values[0]
        size = collections.length(data, bindings)
        if size is None or size > 256 or data.get("<shape>", (size,)) != (size,):
            return None
        return (
            tuple(collections.item(data, position, bindings) for position in range(size)),
            tuple(collections.item_type(data, position, bindings) for position in range(size)),
        )
    return values, types


def reference_array(index, kind, method):
    if not kind.endswith("[]"):
        return False
    element = kind[:-2]
    if element in NUMERIC_TYPES | {"bool"} | index.enums:
        return False
    owner = index.lookup_type(element, method)
    info = index.classes.get(owner)
    if info and any(
        declaration.type == "struct_declaration" for _, declaration in info.declarations
    ):
        return False
    return (
        element in {"object", "System.Object", "string", "System.String"}
        or element.endswith("[]")
        or bool(info)
    )


def compatible(expected, actual):
    aliases = {
        "Int32": "int",
        "Int64": "long",
        "Boolean": "bool",
        "Double": "double",
        "Object": "object",
    }
    expected, actual = expected.removeprefix("System."), actual.removeprefix("System.")
    expected, actual = aliases.get(expected, expected), aliases.get(actual, actual)
    return expected == "object" or bool(actual and expected == actual)


def invoke(estimator, node, method, bindings, stack, conditions, background):
    from app.modules.action_timing import source_delegates as delegates

    target = receiver(node)
    if target is None:
        return None
    saved = call_args.snapshot(node, method, bindings)
    bound = saved.receiver_value if saved is not None else state.MISSING
    if bound is state.MISSING:
        bound = delegates.stored(target, method, bindings, estimator.index)
    if not operation(estimator.index, node, method) and not isinstance(
        bound, delegates.BoundDelegate
    ):
        return None
    prepared = arguments(estimator.index, node, method, bindings)
    shape = (
        signature(estimator.index, bound.signature, bound.closure.method)
        if isinstance(bound, delegates.BoundDelegate)
        else None
    )
    if (
        not shape
        or prepared is None
        or len(prepared[0]) != bound.arity
        or len(shape[0]) != bound.arity
        or not all(
            compatible(expected, actual)
            for expected, actual in zip(shape[0], prepared[1], strict=True)
        )
    ):
        estimator.record(
            "unresolved", "反射委托目标或参数签名未绑定", node, method, conditions, background
        )
        return UNKNOWN
    return delegates.invoke_bound(
        estimator, node, bound, method, bindings, stack, conditions, background, *prepared
    )


def pattern(estimator, node, method, bindings, stack, conditions, background):
    """只证明具体框架委托的精确类型模式；未知目标仍保留两分支。"""
    from app.modules.action_timing import source_delegates as delegates

    value_node = node.child_by_field_name("expression")
    pattern_node = node.child_by_field_name("pattern")
    if pattern_node is None or pattern_node.type != "declaration_pattern":
        return None
    kind = text(pattern_node.child_by_field_name("type"))
    shape = signature(estimator.index, kind, method)
    if shape is None:
        return None
    before = estimator.expression(value_node, method, bindings, stack, conditions, background)
    bound = delegates.capture(estimator.index, value_node, method, bindings)
    actual = (
        signature(estimator.index, bound.signature, bound.closure.method)
        if isinstance(bound, delegates.BoundDelegate)
        else None
    )
    value = None
    if bound is delegates.NULL_DELEGATE:
        value = False
    elif actual == shape:
        value = True
    elif actual is not None and (
        (actual[1] == "void") != (shape[1] == "void") or len(actual[0]) != len(shape[0])
    ):
        value = False
    # 同类泛型委托的不同引用类型可能协变/逆变，签名不等不能证明模式为false。
    bindings[call_args.return_key(node, method, bindings)] = value
    name = text(pattern_node.child_by_field_name("name"))
    bindings[name] = bound if value else None
    bindings[f"{delegates.DELEGATE_PREFIX}{name}>"] = (method.key, bound if value else None)
    return before


def null_comparison(node, left, right):
    from app.modules.action_timing.source_delegates import NULL_DELEGATE, BoundDelegate

    operator = text(node.child_by_field_name("operator"))
    if operator not in {"==", "!="}:
        return None
    value = (
        right
        if text(node.child_by_field_name("left")) == "null"
        else (left if text(node.child_by_field_name("right")) == "null" else None)
    )
    if isinstance(value, BoundDelegate) or value is NULL_DELEGATE:
        return (value is NULL_DELEGATE) == (operator == "==")
    return None
