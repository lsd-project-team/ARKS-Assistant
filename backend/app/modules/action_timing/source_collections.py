"""静态集合值与共享元素状态；不调用目标程序的枚举器或集合方法。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import children, simple_type, text
from app.modules.action_timing.source_numbers import coerce

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
    if (
        known(data)
        and data["<collection>"] == "list"
        and state.object_unstable(data["<ref>"], bindings)
    ):
        return None
    if known(data) and key(data, "length") in bindings.get(state.UNSTABLE, ()):
        return None
    return bindings.get(key(data, "length"), data.get("<length>")) if known(data) else None


def version(data, bindings):
    if (
        known(data)
        and data["<collection>"] == "list"
        and state.object_unstable(data["<ref>"], bindings)
    ):
        return None
    if known(data) and key(data, "version") in bindings.get(state.UNSTABLE, ()):
        return None
    return bindings.get(key(data, "version"), 0) if known(data) else None


def item(data, position, bindings):
    if not known(data) or not isinstance(position, int) or isinstance(position, bool):
        return None
    size = length(data, bindings)
    if size is None or not 0 <= position < size:
        return None
    own = key(data, f"item:{position}")
    if own in bindings.get(state.UNSTABLE, ()) or state.object_unstable(data["<ref>"], bindings):
        return None
    if own in bindings:
        return state.materialize(coerce(data.get("<element_type>"), bindings[own]), bindings)
    unknown = key(data, "unknown")
    if unknown in bindings and bindings[unknown] is not False:
        return None
    if data["<collection>"] == "range":
        return data["<start>"] + position
    values = data.get("<items>")
    value = (
        state.materialize(values[position], bindings)
        if values is not None
        else data.get("<default>")
    )
    return coerce(data.get("<element_type>"), value)


def invalidate(data, bindings):
    if not known(data):
        return
    bindings[key(data, "unknown")] = True
    state.mark_write(bindings, key(data, "unknown"))
    for name in list(bindings):
        if name.startswith(f"{PREFIX}{data['<ref>']}|item:"):
            bindings[name] = None
            state.mark_write(bindings, name)
    if data["<collection>"] == "list":
        bindings[key(data, "length")] = None
        bindings[key(data, "version")] = None
        state.mark_write(bindings, key(data, "length"))
        state.mark_write(bindings, key(data, "version"))


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
    from app.modules.action_timing.source_array_values import offset

    return data, offset(
        data, [index.value(arg, method, bindings) for arg in args], length(data, bindings)
    )


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
        state.mark_write(bindings, key(data, f"item:{position}"))
        if data.get("<element_type>") in {"object", "System.Object"}:
            bindings[key(data, f"type:{position}")] = None
            state.mark_write(bindings, key(data, f"type:{position}"))
        if data["<collection>"] == "list":
            current = version(data, bindings)
            bindings[key(data, "version")] = current + 1 if current is not None else None
    else:
        invalidate(data, bindings)


def item_type(data, position, bindings):
    """object[]元素的装箱类型不能由Python数值反推，未知写入使旧类型失效。"""
    if not known(data) or length(data, bindings) is None:
        return ""
    if state.object_unstable(data["<ref>"], bindings) or bindings.get(key(data, "unknown")):
        return ""
    own = key(data, f"type:{position}")
    if own in bindings.get(state.UNSTABLE, ()):
        return ""
    kind = data.get("<element_type>", "")
    return bindings.get(own) or "" if kind in {"object", "System.Object"} else kind


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
        if node.type in ARRAYS and kind:
            from app.modules.action_timing.source_array_values import type_name

            kind = type_name(node)
        if not kind:
            from app.modules.action_timing import source_array_values as arrays

            count = arrays.rank(node)
            _, parts = arrays.initializer_shape(arrays.initial(node), count)
            element = index.infer(parts[0], method) if parts else "object"
            from app.modules.action_timing.source_numbers import promoted

            for part in parts[1:]:
                other = index.infer(part, method)
                if element != other:
                    element = promoted(element, other) or "var"
            kind = f"{element}[{',' * (count - 1)}]"
        return kind
    if node.type == "identifier":
        kind, value_node = index.local_definition(node, method)
        if kind and kind != "var":
            return kind
        if kind == "var":
            return raw_type(index, value_node, method, seen)
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
        return target.return_type if target else ""
    else:
        return ""
    return (
        index.classes[found[0]].types.get(text(node.child_by_field_name("name")) or text(node), "")
        if found
        else ""
    )


def element_type(index, node, method):
    from app.modules.action_timing.source_array_values import element

    return element(raw_type(index, node, method))


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
    dimensions = None
    if array:
        from app.modules.action_timing import source_array_values as arrays

        dimensions, parts = arrays.shape(index, node, method, bindings)
        size = arrays.length(dimensions)
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
        **({"<shape>": dimensions} if array else {}),
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
    if estimator.index.resolve(node, method) is not None:
        return False
    name = text(function.child_by_field_name("name"))
    if not known(data):
        kind = raw_type(estimator.index, receiver, method)
        base = kind.split("<", 1)[0].split(".")[-1]
        if (
            state.WRITES in bindings
            and base in {"List", "IList", "ICollection", "Dictionary", "IDictionary"}
            and name
            in {
                "Add",
                "Clear",
                "Insert",
                "Remove",
                "RemoveAt",
                "RemoveAll",
                "RemoveRange",
                "AddRange",
                "Sort",
                "Reverse",
            }
        ):
            state.write(estimator.index, receiver, method, bindings, None)
        return False
    values = call_args.values(estimator.index, node, method, bindings)
    if name == "ToArray" and not values:
        size = length(data, bindings)
        if size is not None and size <= 256:
            estimator.allocations += 1
            result = {
                "<collection>": "array",
                "<ref>": f"array-copy:{estimator.allocations}",
                "<length>": size,
                "<shape>": (size,),
                "<element_type>": data.get("<element_type>"),
                "<items>": tuple(item(data, i, bindings) for i in range(size)),
            }
            bindings[call_args.return_key(node, method, bindings)] = result
            return True
    if data["<collection>"] == "array" and name in {
        "GetLength",
        "GetLongLength",
        "GetLowerBound",
        "GetUpperBound",
    }:
        shape = data.get("<shape>")
        dimension = values[0] if len(values) == 1 else None
        size = (
            shape[dimension]
            if shape is not None
            and isinstance(dimension, int)
            and not isinstance(dimension, bool)
            and 0 <= dimension < len(shape)
            else None
        )
        result = (
            None
            if size is None
            else {
                "GetLength": size,
                "GetLongLength": size,
                "GetLowerBound": 0,
                "GetUpperBound": size - 1,
            }[name]
        )
        bindings[call_args.return_key(node, method, bindings)] = result
        return True
    if data["<collection>"] == "list" and name == "Add" and len(values) == 1:
        size, current = length(data, bindings), version(data, bindings)
        if size is None:
            invalidate(data, bindings)
        else:
            bindings[key(data, f"item:{size}")] = values[0]
            bindings[key(data, "length")] = size + 1
            bindings[key(data, "version")] = current + 1 if current is not None else None
            for name in (f"item:{size}", "length", "version"):
                state.mark_write(bindings, key(data, name))
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
