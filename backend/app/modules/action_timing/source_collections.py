"""静态集合值与共享元素状态；不调用目标程序的枚举器或集合方法。"""

import re

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import children, simple_type, text

PREFIX = "<collection:"
ARRAYS = {
    "array_creation_expression",
    "implicit_array_creation_expression",
    "collection_expression",
}


def key(data, name):
    return f"{PREFIX}{data['<ref>']}|{name}>"


def known(data):
    return isinstance(data, dict) and data.get("<collection>") in {"array", "list", "range"}


def length(data, bindings):
    return bindings.get(key(data, "length"), data.get("<length>")) if known(data) else None


def version(data, bindings):
    return bindings.get(key(data, "version"), 0) if known(data) else None


def item(data, position, bindings):
    if not known(data) or not isinstance(position, int) or isinstance(position, bool):
        return None
    size = length(data, bindings)
    if size is None or not 0 <= position < size:
        return None
    own = key(data, f"item:{position}")
    if own in bindings:
        return state.materialize(bindings[own], bindings)
    unknown = key(data, "unknown")
    if unknown in bindings and bindings[unknown] is not False:
        return None
    if data["<collection>"] == "range":
        return data["<start>"] + position
    values = data.get("<items>")
    return (
        state.materialize(values[position], bindings)
        if values is not None
        else data.get("<default>")
    )


def invalidate(data, bindings):
    if not known(data):
        return
    bindings[key(data, "unknown")] = True
    for name in list(bindings):
        if name.startswith(f"{PREFIX}{data['<ref>']}|item:"):
            bindings[name] = None
    if data["<collection>"] == "list":
        bindings[key(data, "length")] = None
        bindings[key(data, "version")] = None


def location(index, node, method, bindings):
    if node is None or node.type != "element_access_expression":
        return None
    saved = bindings.get(call_args.snapshot_key(node, method, bindings) + ":element")
    if saved is not None:
        return saved
    data = index.value(node.child_by_field_name("expression"), method, bindings)
    if not known(data):
        return None
    listing = node.child_by_field_name("subscript") or next(
        iter(children(node, "bracketed_argument_list")), None
    )
    args = children(listing, "argument")
    return data, index.value(args[0], method, bindings) if len(args) == 1 else None


def write(place, value, bindings):
    data, position = place
    size = length(data, bindings)
    if (
        isinstance(position, int)
        and not isinstance(position, bool)
        and size is not None
        and 0 <= position < size
    ):
        bindings[key(data, f"item:{position}")] = value
        if data["<collection>"] == "list":
            current = version(data, bindings)
            bindings[key(data, "version")] = current + 1 if current is not None else None
    else:
        invalidate(data, bindings)


def raw_type(index, node, method, seen=None):
    if node is None:
        return ""
    seen = set() if seen is None else seen
    identity = (method.key, node.start_byte, node.end_byte)
    if identity in seen:
        return ""
    seen = seen | {identity}
    if node.type in ARRAYS | {"object_creation_expression"}:
        kind = text(node.child_by_field_name("type"))
        if not kind:
            init = next(iter(children(node, "initializer_expression")), None)
            parts = children(init)
            kind = f"{index.infer(parts[0], method)}[]" if parts else "object[]"
        return kind
    if node.type == "identifier":
        kind = method.types.get(text(node), "")
        if kind and kind != "var":
            return kind
        if kind == "var":
            return raw_type(index, method.initializers.get(text(node)), method, seen)
        found = state.member(index, method.owner, text(node))
    elif node.type == "member_access_expression":
        owner = index.infer(node.child_by_field_name("expression"), method)
        found = state.member(index, owner, text(node.child_by_field_name("name")))
    elif node.type == "invocation_expression":
        if text(node.child_by_field_name("function")) in {
            "Enumerable.Range",
            "System.Linq.Enumerable.Range",
        }:
            return "IEnumerable<int>"
        target = index.resolve(node, method)
        return text(target.node.child_by_field_name("returns")) if target else ""
    else:
        return ""
    return (
        index.classes[found[0]].types.get(text(node.child_by_field_name("name")) or text(node), "")
        if found
        else ""
    )


def element_type(index, node, method):
    raw = re.sub(r"\[[^]]*\]", "[]", raw_type(index, node, method))
    if raw.endswith("[]"):
        return raw[:-2]
    found = re.match(r"(?:[\w.]+)<(.+)>", raw)
    return found[1].strip() if found and "," not in found[1] else "var"


def created(index, node, method, bindings):
    saved = bindings.get(call_args.return_key(node, method, bindings), state.MISSING)
    if known(saved):
        return saved
    kind = text(node.child_by_field_name("type"))
    owner = index.lookup_type(kind, method)
    array = node.type in ARRAYS
    is_list = (
        node.type == "object_creation_expression"
        and simple_type(owner) == "List"
        and owner not in index.classes
        and (
            kind.startswith("System.Collections.Generic.List<")
            or "System.Collections.Generic" in method.unit.namespaces
        )
    )
    if not array and not is_list:
        return state.MISSING
    init = node.child_by_field_name("initializer") or next(
        iter(children(node, "initializer_expression")), None
    )
    parts = [n for n in children(init) if n.type != "comment"]
    size = len(parts) if init is not None and not is_list else 0 if is_list else None
    copied = None
    if is_list:
        arguments = call_args.arguments(node)
        if arguments:
            first = call_args.values(index, node, method, bindings)[0]
            if known(first):
                size = length(first, bindings)
                copied = (
                    tuple(item(first, i, bindings) for i in range(size))
                    if size is not None and size <= 4096
                    else None
                )
            elif not isinstance(first, int) or isinstance(first, bool) or first < 0:
                size = None
    if array and init is None:
        dimensions = [
            n
            for n in children(node.child_by_field_name("type"))
            if n.type == "array_rank_specifier"
        ]
        values = [index.value(n, method, bindings) for rank in dimensions for n in children(rank)]
        size = (
            values[0]
            if len(values) == 1 and isinstance(values[0], int) and values[0] >= 0
            else None
        )
    element = element_type(index, node, method)
    ref = bindings.get(
        f"<allocation:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}>",
        f"collection:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}",
    )
    return {
        "<type>": kind or f"{element}[]",
        "<ref>": ref,
        "<collection>": "array" if array else "list",
        "<element_type>": element,
        "<length>": size,
        "<items>": tuple(index.value(n, method, bindings) for n in parts)
        if init is not None and not is_list
        else copied,
        "<default>": False
        if array and element == "bool"
        else 0
        if array and element in {"int", "long", "short", "byte", "double", "float", "decimal"}
        else None,
    }


def range_value(index, node, method, bindings):
    function = text(node.child_by_field_name("function"))
    if function not in {"Enumerable.Range", "System.Linq.Enumerable.Range"} or index.resolve(
        node, method
    ):
        return state.MISSING
    values = call_args.values(index, node, method, bindings)
    if len(values) != 2 or not all(isinstance(v, int) and not isinstance(v, bool) for v in values):
        return None
    start, count = values
    if count < 0 or not -(2**31) <= start <= start + max(count - 1, 0) < 2**31:
        return None
    return {
        "<type>": "IEnumerable<int>",
        "<collection>": "range",
        "<element_type>": "int",
        "<start>": start,
        "<length>": count,
        "<ref>": f"range:{method.key}:{node.start_byte}",
    }


def call(estimator, node, method, bindings):
    function = node.child_by_field_name("function")
    receiver = function.child_by_field_name("expression")
    saved = call_args.snapshot(node, method, bindings)
    data = (
        saved.receiver_value
        if saved is not None and saved.receiver_value is not state.MISSING
        else estimator.index.value(receiver, method, bindings)
    )
    if not known(data) or estimator.index.resolve(node, method) is not None:
        return False
    name = text(function.child_by_field_name("name"))
    values = call_args.values(estimator.index, node, method, bindings)
    if data["<collection>"] == "list" and name == "Add" and len(values) == 1:
        size, current = length(data, bindings), version(data, bindings)
        if size is None:
            invalidate(data, bindings)
        else:
            bindings[key(data, f"item:{size}")] = values[0]
            bindings[key(data, "length")] = size + 1
            bindings[key(data, "version")] = current + 1 if current is not None else None
        return True
    if data["<collection>"] == "list" and name == "Clear" and not values:
        current = version(data, bindings)
        invalidate(data, bindings)
        bindings[key(data, "length")] = 0
        bindings[key(data, "version")] = current + 1 if current is not None else None
        return True
    if name not in {"ToString", "Contains", "IndexOf", "GetHashCode", "Equals"}:
        invalidate(data, bindings)
    return False


def invalidate_arguments(index, node, method, bindings):
    # 包外调用可能修改传入集合；没有同版本实现时不沿用旧的元素或长度。
    for value in call_args.values(index, node, method, bindings):
        if known(value):
            invalidate(value, bindings)
