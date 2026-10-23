"""只读投影矩形数组的维度与行序元素，不创建目标语言数组。"""

import math

from app.modules.action_timing.source_index import children, text, value_children


def first_rank(node):
    return next(iter(children(node.child_by_field_name("type"), "array_rank_specifier")), None)


def type_name(node):
    kind = node.child_by_field_name("type")
    return "".join(
        f"[{',' * sum(n.type == ',' for n in part.children)}]"
        if part.type == "array_rank_specifier"
        else text(part)
        for part in children(kind)
    )


def rank(node):
    if node.type == "collection_expression":
        return 1
    declaration = first_rank(node)
    parts = declaration.children if declaration is not None else node.children
    return 1 + sum(part.type == "," for part in parts)


def dimensions(node):
    return [part for part in children(first_rank(node)) if part.type != "comment"]


def initial(node):
    return node.child_by_field_name("initializer") or next(
        iter(children(node, "initializer_expression")), None
    )


def initializer_shape(node, depth):
    parts = value_children(node)
    if depth == 1:
        if any(part.type == "initializer_expression" for part in parts):
            return None, []
        return (len(parts),), parts
    shapes, leaves = [], []
    for part in parts:
        if part.type != "initializer_expression":
            return None, []
        shape, values = initializer_shape(part, depth - 1)
        if shape is None:
            return None, []
        shapes.append(shape)
        leaves.extend(values)
    if not shapes:
        return (0, *(None for _ in range(depth - 1))), []
    if any(shape != shapes[0] for shape in shapes):
        return None, []
    return (len(parts), *shapes[0]), leaves


def shape(index, node, method, bindings, sizes=None):
    count = rank(node)
    initializer = initial(node)
    inferred, leaves = initializer_shape(initializer, count) if initializer else (None, [])
    values = (
        tuple(index.value(part, method, bindings) for part in dimensions(node))
        if sizes is None
        else sizes
    )
    if not values and initializer is not None:
        return inferred, leaves
    if len(values) != count:
        return (None,) * count, leaves
    if any(isinstance(v, bool) or not isinstance(v, int) or v < 0 for v in values):
        return tuple(
            v if isinstance(v, int) and not isinstance(v, bool) and v >= 0 else None for v in values
        ), leaves
    if inferred is not None and inferred != values:
        return None, []
    return tuple(values), leaves


def length(shape):
    return (
        math.prod(shape)
        if shape is not None and all(isinstance(n, int) and n >= 0 for n in shape)
        else None
    )


def offset(data, positions, size=None):
    shape = data.get("<shape>", (size,))
    if shape is None or len(positions) != len(shape):
        return None
    result = 0
    for position, size in zip(positions, shape, strict=True):
        if (
            not isinstance(position, int)
            or isinstance(position, bool)
            or size is None
            or not 0 <= position < size
        ):
            return None
        result = result * size + position
    return result


def element(raw):
    # 外层秩在泛型参数之外；List<int[,]>里的逗号不是两个泛型参数。
    nesting = 0
    for i, char in enumerate(raw):
        nesting += (char == "<") - (char == ">")
        if char == "[" and nesting == 0:
            end = raw.find("]", i)
            return raw[:i] + raw[end + 1 :] if end >= 0 else "var"
    start = raw.find("<")
    if start < 0 or not raw.endswith(">"):
        return "var"
    content = raw[start + 1 : -1]
    nesting = 0
    for char in content:
        nesting += (char in "<[(") - (char in ">])")
        if char == "," and nesting == 0:
            return "var"
    return content.strip()
