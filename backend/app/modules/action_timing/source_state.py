"""源码模拟的成员状态与对象身份；分支快照使用平面、不可变的值。"""

THIS = "<source-this>"
FRAME = "<source-frame>"
PREFIX = "<member:"
LOCAL_PREFIX = "<captured-local:"
LOCAL_ALIAS = "<captured-alias:"
MISSING = object()


def local_slot(node, method, bindings):
    name = source(node)
    if node is None or node.type != "identifier" or name not in method.types:
        return None
    return bindings.get(f"{LOCAL_ALIAS}{name}>", f"{LOCAL_PREFIX}{bindings.get(FRAME)}|{name}>")


def source(node):
    return node.text.decode("utf-8") if node is not None else ""


def member(index, owner, name, seen=None):
    seen = set() if seen is None else seen
    if owner not in index.classes or owner in seen:
        return None
    seen.add(owner)
    info = index.classes[owner]
    if name in info.types:
        return owner, name in info.static_members
    return next(
        (found for base in index.base_types(owner) if (found := member(index, base, name, seen))),
        None,
    )


def reference(index, node, method, bindings):
    if node is None or source(node) in {"this", "base"}:
        return bindings.get(THIS)
    value = index.value(node, method, bindings)
    return value.get("<ref>") if isinstance(value, dict) else None


def location(index, node, method, bindings, owner=None):
    if node is None:
        return None
    name = source(node)
    if node.type == "identifier":
        if owner is None and name in method.types:
            return None
        found = member(index, owner or method.owner, name)
        receiver = bindings.get(THIS)
    elif node.type == "member_access_expression":
        target = node.child_by_field_name("expression")
        name = source(node.child_by_field_name("name"))
        kind = owner or index.infer(target, method)
        found = member(index, kind, name)
        if found is None and kind and kind not in index.classes:
            # 外部参数对象仍可跟踪显式赋值；不据此断言SDK属性的执行时间。
            found = (kind, False)
        # 静态成员不需要对类型名求值，也不依赖当前实例。
        receiver = reference(index, target, method, bindings) if found and not found[1] else None
    else:
        return None
    if found is None:
        return None
    declaring, static = found
    return ("static" if static else receiver, declaring, name)


def key(location):
    receiver, owner, name = location
    return f"{PREFIX}{receiver or '*'}|{owner}|{name}>"


def read(index, node, method, bindings):
    local = local_slot(node, method, bindings)
    if local in bindings:
        return bindings[local]
    place = location(index, node, method, bindings)
    if place is None:
        return MISSING
    own = key(place)
    wildcard = key((None, place[1], place[2]))
    if own in bindings:
        return bindings[own]
    if wildcard in bindings:
        return None
    return MISSING


def write(index, node, method, bindings, value, owner=None):
    local = local_slot(node, method, bindings)
    if owner is None and local in bindings:
        bindings[local] = value
        bindings[source(node)] = value
        return
    place = location(index, node, method, bindings, owner)
    if place is None:
        bindings[source(node)] = value
        return
    if place[0] is None:
        # 无法证明两个引用是否指向同一对象。使该成员的所有已知实例失效，
        # 再保留通配失效标记，防止尚未读取的实例重新取声明初值。
        ending = f"|{place[1]}|{place[2]}>"
        for existing in list(bindings):
            if existing.startswith(PREFIX) and existing.endswith(ending):
                bindings[existing] = None
        value = None
    bindings[key(place)] = value


def context(bindings):
    return {
        name: value for name, value in bindings.items() if name.startswith((PREFIX, LOCAL_PREFIX))
    }


def materialize(value, bindings):
    if not isinstance(value, dict) or "<ref>" not in value:
        return value
    result = dict(value)
    start = f"{PREFIX}{value['<ref>']}|"
    for name, assigned in bindings.items():
        if name.startswith(start):
            member_name = name[len(start) :].rsplit("|", 1)[-1].removesuffix(">")
            result[member_name] = assigned
    return result


def transfer(before, after, *, uncertain=False, locals=False):
    """把调用或后台分支的写入带回；未确定先后关系时只传播失效。"""
    for name, value in after.items():
        if name.startswith((PREFIX, LOCAL_PREFIX)) or (locals and not name.startswith("<")):
            if name not in before or value != before[name]:
                before[name] = None if uncertain else value


def merge(bindings, branches):
    if not branches:
        return
    for name in set().union(*(branch.keys() for branch in branches)):
        values = [branch.get(name) for branch in branches]
        bindings[name] = values[0] if all(value == values[0] for value in values) else None


def receiver_for(index, target, node, caller, bindings):
    if target.is_static:
        return None
    if node.type == "object_creation_expression" and target.callable_kind == "constructor":
        return reference(index, node, caller, bindings)
    if node.type in {"constructor_initializer", "constructor_declaration"}:
        return bindings.get(THIS)
    if target.callable_kind == "initializer":
        return bindings.get(THIS)
    function = node.child_by_field_name("function") or node
    if function.type == "conditional_access_expression":
        return reference(index, function.child_by_field_name("condition"), caller, bindings)
    if function.type == "member_access_expression":
        return reference(index, function.child_by_field_name("expression"), caller, bindings)
    return bindings.get(THIS)


def byref_arguments(node):
    args = node.child_by_field_name("arguments")
    if args is None:
        return []
    return [
        (position, argument)
        for position, argument in enumerate(child for child in args.children if child.is_named)
        if any(child.type in {"ref", "out"} for child in argument.children)
    ]


def argument_target(argument):
    parts = [child for child in argument.children if child.is_named]
    if not parts:
        return None
    target = parts[-1]
    if target.type == "declaration_expression":
        target = target.child_by_field_name("name") or next(
            (child for child in reversed(target.children) if child.is_named), None
        )
    return target


def invalidate_byref(index, node, method, bindings):
    for _, argument in byref_arguments(node):
        target = argument_target(argument)
        if target is not None and source(target) != "_":
            write(index, target, method, bindings, None)
