"""当前对象只保留引用身份；不从声明类型推断精确运行时类型或结构体复制。"""

from app.modules.action_timing import source_state as state

SELF_TYPE = "<self-type>"


def self_value(index, method, bindings):
    info = index.classes.get(method.owner)
    if (
        method.is_static
        or not info
        or any(
            declaration.type == "struct_declaration"
            or (
                declaration.type == "record_declaration"
                and any(child.type == "struct" for child in declaration.children)
            )
            for _, declaration in info.declarations
        )
    ):
        return None
    reference = bindings.get(state.THIS)
    return {"<ref>": reference, SELF_TYPE: method.owner} if reference is not None else None


def receiver_use(node):
    parent = node.parent
    return parent is not None and (
        (
            parent.type == "member_access_expression"
            and parent.child_by_field_name("expression") == node
        )
        or (
            parent.type == "conditional_access_expression"
            and parent.child_by_field_name("condition") == node
        )
    )


def leaf_cost(estimator, node, method, bindings, conditions, background):
    from app.modules.action_timing.source_flow import ZERO

    if self_value(estimator.index, method, bindings) is not None:
        return ZERO
    if not method.is_static and receiver_use(node):
        return ZERO  # 结构体自身的成员访问不在这里创建值副本。
    estimator.record(
        "unresolved", "当前对象或值类型this的副本语义未绑定", node, method, conditions, background
    )
    return ZERO  # 身份/值副本未绑定不等于执行了额外的软件等待。


def ancestors(index, owner):
    pending, seen = [owner], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(index.base_types(current))
    return seen


def cast_value(index, node, method, value):
    if not isinstance(value, dict) or SELF_TYPE not in value:
        return state.MISSING
    target_node = node.child_by_field_name("type") or node.child_by_field_name("right")
    if target_node is None:
        return None
    target_source = target_node.text.decode("utf-8")
    if "<" in target_source or "[" in target_source:
        return None  # lookup_type会擦除泛型和数组形状，不能据此证明引用转换。
    target = index.lookup_type(target_source, method)
    if target in {"object", "System.Object"} or target in ancestors(index, value[SELF_TYPE]):
        return value
    return None


def equality_kind(index, kind, seen=None):
    """只对可核实的普通引用类型使用身份比较；运算符、record及外部基类留未定。"""
    if kind in {"object", "System.Object"} or kind.endswith("]"):
        return "identity"
    cache = index.__dict__.setdefault("reference_equality_kinds", {})
    if kind in cache:
        return cache[kind]
    info = index.classes.get(kind)
    seen = set() if seen is None else seen
    if not info or kind in seen:
        return "unknown"
    seen = seen | {kind}
    result = "identity"
    for _, declaration in info.declarations:
        if declaration.type in {"record_declaration", "struct_declaration"}:
            result = "custom"
        body = declaration.child_by_field_name("body")
        for member in body.children if body is not None else ():
            if member.type == "operator_declaration" and any(
                child.type in {"==", "!="} for child in member.children
            ):
                result = "custom"
    bases = [equality_kind(index, base, seen) for base in equality_bases(index, kind)]
    if "custom" in bases:
        result = "custom"
    elif result != "custom" and "unknown" in bases:
        result = "unknown"
    cache[kind] = result
    return result


def equality_bases(index, owner):
    """类运算符只沿基类查找；已核实的接口不能使普通空值判断变成SDK调用。"""
    from app.modules.action_timing.source_index import children, text

    for unit, declaration in index.classes[owner].declarations:
        for base_list in children(declaration, "base_list"):
            for node in children(base_list):
                source = text(node).removeprefix("global::")
                base = index.lookup_type(source, owner, unit)
                info = index.classes.get(base)
                if info is not None:
                    if all(part.type == "interface_declaration" for _, part in info.declarations):
                        continue
                elif source == "System.ComponentModel.INotifyPropertyChanged" or (
                    source == "INotifyPropertyChanged"
                    and "System.ComponentModel" in unit.namespaces
                ):
                    continue
                yield base


def equality(index, node, method, left, right):
    from app.modules.action_timing import source_collections as collections
    from app.modules.action_timing.source_collections import raw_type
    from app.modules.action_timing.source_index import text

    operator = text(node.child_by_field_name("operator"))
    if operator not in {"==", "!="}:
        return False, None, False
    nodes = (node.child_by_field_name("left"), node.child_by_field_name("right"))
    kinds = []
    for part, value in zip(nodes, (left, right), strict=True):
        if text(part) == "null":
            continue
        kind = equality_kind(index, index.infer(part, method))
        raw = raw_type(index, part, method) if collections.known(value) else ""
        if collections.known(value) and (
            raw.endswith("]")
            or (
                raw.split("<", 1)[0] in {"List", "System.Collections.Generic.List"}
                and index.lookup_type(raw, method) not in index.classes
            )
        ):
            kind = "identity"
        kinds.append(kind)
    references = [part.get("<ref>") if isinstance(part, dict) else None for part in (left, right)]
    if "custom" in kinds:
        return True, None, "source"
    if not any(reference is not None for reference in references):
        return False, None, False
    if any(kind != "identity" for kind in kinds):
        return True, None, "external"
    if all(reference is not None for reference in references):
        same = references[0] == references[1]
    elif any(text(part) == "null" for part in nodes):
        same = False
    else:
        return True, None, False
    return True, same if operator == "==" else not same, False


def invalidate_values(values, bindings, *, require_self=False):
    """只使显式传入对象及可达内容失效，外部运算不凭空改写无关实例。"""
    from app.modules.action_timing.source_numbers import NUMERIC_TYPES

    pending = list(values)
    if not any(isinstance(value, (dict, tuple, list)) for value in pending):
        return False
    members = {}
    for key, value in state.context(bindings).items():
        for prefix in (state.PREFIX, state.COLLECTION_PREFIX):
            if key.startswith(prefix):
                members.setdefault(key.removeprefix(prefix).split("|", 1)[0], []).append(value)
                break
    references, seen, escaped, steps = set(), set(), False, 0
    while pending and steps < 4096:
        value = pending.pop()
        if not isinstance(value, (dict, tuple, list)) or id(value) in seen:
            continue
        seen.add(id(value))
        steps += 1
        if not isinstance(value, dict):
            pending.extend(value)
            continue
        escaped |= SELF_TYPE in value
        reference = value.get("<ref>")
        if reference is not None and reference not in references:
            references.add(reference)
            pending.extend(members.get(reference, ()))
        if value.get("<element_type>") not in NUMERIC_TYPES | {"bool", "char", "string"}:
            pending.extend(value.values())
    if not escaped and not pending and require_self:
        return False
    unstable = {state.object_marker(reference) for reference in references}
    if pending:
        unstable.update(
            name for name in bindings if name.startswith((state.PREFIX, state.COLLECTION_PREFIX))
        )
        bindings[state.UNKNOWN_MEMBERS] = True
    bindings[state.UNSTABLE] = (bindings.get(state.UNSTABLE) or frozenset()) | unstable
    return True


def escape_this(index, node, method, bindings):
    """未解析代码可能保留并改写this；沿已知成员/集合追踪，保留失效。"""
    from app.modules.action_timing import source_arguments as arguments

    return invalidate_values(
        arguments.values(index, node, method, bindings), bindings, require_self=True
    )
