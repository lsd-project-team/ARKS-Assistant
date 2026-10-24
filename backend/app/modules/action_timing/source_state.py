"""源码模拟的成员状态与对象身份；分支快照使用平面、不可变的值。"""

THIS = "<source-this>"
FRAME = "<source-frame>"
PREFIX = "<member:"
LOCAL_PREFIX = "<captured-local:"
LOCAL_ALIAS = "<captured-alias:"
COLLECTION_PREFIX = "<collection:"
UNSTABLE = "<source-concurrent-writes>"
UNKNOWN_MEMBERS = "<source-unknown-members>"
WRITES = "<source-dispatch-writes>"
FRESH = "<source-queue-new-objects>"
PRIVATE_PENDING = "<source-private-pending>"
PRIVATE_ACTIVE = "<source-private-active>"
LOCAL_FUNCTIONS = "<source-local-functions>"
MISSING = object()


def object_marker(reference):
    return f"<source-concurrent-object:{reference}>"


def object_unstable(reference, bindings):
    return object_marker(reference) in bindings.get(UNSTABLE, ())


def mark_write(bindings, name):
    if WRITES in bindings:
        bindings[WRITES] = (bindings.get(WRITES) or frozenset()) | {name}


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
        if owner is None and index.local_type(node, method):
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


def receiver_unstable(index, node, method, bindings):
    if node is None or node.type != "member_access_expression":
        return False
    target = node.child_by_field_name("expression")
    found = member(index, index.infer(target, method), source(node.child_by_field_name("name")))
    if found is not None and found[1]:
        return False
    # box已失效时，box.delay也必须未定，不能从Box声明重新取初值。
    return is_unstable(index, target, method, bindings)


def read(index, node, method, bindings):
    if receiver_unstable(index, node, method, bindings):
        return None
    local = local_slot(node, method, bindings)
    unstable = bindings.get(UNSTABLE)
    if local in bindings:
        return None if unstable and local in unstable else bindings[local]
    place = location(index, node, method, bindings)
    if place is None:
        return MISSING
    from app.modules.action_timing.source_private_state import unsafe

    if unsafe(index, place, bindings):
        return None
    own = key(place)
    wildcard = key((None, place[1], place[2]))
    if unstable and (
        own in unstable or wildcard in unstable or object_marker(place[0]) in unstable
    ):
        return None
    if own in bindings:
        return bindings[own]
    if wildcard in bindings:
        return None
    if bindings.get(UNKNOWN_MEMBERS) and place[0] not in (bindings.get(FRESH) or ()):
        default = index.member_default(place[1], place[2])
        node = default[1][1] if default else None
        declaration = (
            node.parent.parent.parent
            if node is not None and node.parent and node.parent.parent
            else None
        )
        if declaration is None or not any(source(part) == "const" for part in declaration.children):
            return None
    return MISSING


def is_unstable(index, node, method, bindings):
    from app.modules.action_timing.source_private_state import unsafe

    if receiver_unstable(index, node, method, bindings) or unsafe(
        index, location(index, node, method, bindings), bindings
    ):
        return True
    unstable = bindings.get(UNSTABLE)
    if not unstable:
        return False
    if local_slot(node, method, bindings) in unstable:
        return True
    place = location(index, node, method, bindings)
    return bool(
        place
        and (
            key(place) in unstable
            or key((None, place[1], place[2])) in unstable
            or object_marker(place[0]) in unstable
        )
    )


def write(index, node, method, bindings, value, owner=None):
    local = local_slot(node, method, bindings)
    if owner is None and local in bindings:
        bindings[local] = value
        mark_write(bindings, local)
        bindings[source(node)] = value
        return
    place = location(index, node, method, bindings, owner)
    if place is None:
        bindings[source(node)] = value
        return
    write_location(place, bindings, value)


def write_location(place, bindings, value):
    """使用赋值前已经求值的接收者位置，右侧不能改换写入目标。"""
    if place[0] is None:
        # 无法证明两个引用是否指向同一对象。使该成员的所有已知实例失效，
        # 再保留通配失效标记，防止尚未读取的实例重新取声明初值。
        ending = f"|{place[1]}|{place[2]}>"
        for existing in list(bindings):
            if existing.startswith(PREFIX) and existing.endswith(ending):
                bindings[existing] = None
                mark_write(bindings, existing)
        value = None
    bindings[key(place)] = value
    mark_write(bindings, key(place))


def context(bindings):
    return {
        name: value
        for name, value in bindings.items()
        if name.startswith((PREFIX, LOCAL_PREFIX, COLLECTION_PREFIX))
        or name
        in {
            UNSTABLE,
            UNKNOWN_MEMBERS,
            WRITES,
            FRESH,
            PRIVATE_PENDING,
            PRIVATE_ACTIVE,
            LOCAL_FUNCTIONS,
        }
    }


def materialize(value, bindings):
    if not isinstance(value, dict) or "<ref>" not in value:
        return value
    if "<self-type>" in value:
        # this不把基类/派生类的同名成员压成一个对象字典；访问时按声明所有者读取槽。
        return dict(value)
    result = dict(value)
    shared = object_unstable(value["<ref>"], bindings)
    if shared or (
        bindings.get(UNKNOWN_MEMBERS) and value["<ref>"] not in (bindings.get(FRESH) or ())
    ):
        result.update({key: None for key in result if not key.startswith("<")})
    start = f"{PREFIX}{value['<ref>']}|"
    for name, assigned in bindings.items():
        if name.startswith(start):
            member_name = name[len(start) :].rsplit("|", 1)[-1].removesuffix(">")
            result[member_name] = None if shared or name in bindings.get(UNSTABLE, ()) else assigned
    return result


def transfer(before, after, *, uncertain=False, locals=False):
    """把调用或后台分支的写入带回；未确定先后关系时只传播失效。"""
    for name, value in after.items():
        if name in {PRIVATE_ACTIVE, LOCAL_FUNCTIONS}:
            continue  # 当前执行目标属于调用帧，不带回发起者或其他并发分支。
        if name in {WRITES, FRESH, PRIVATE_PENDING, UNSTABLE}:
            if name in before or name in {PRIVATE_PENDING, UNSTABLE}:
                before[name] = (before.get(name) or frozenset()) | (value or frozenset())
            continue
        if name == UNKNOWN_MEMBERS and value:
            before[name] = True
            continue
        if name.startswith((PREFIX, LOCAL_PREFIX, COLLECTION_PREFIX)) or (
            locals and not name.startswith("<")
        ):
            if name not in before or value != before[name]:
                before[name] = None if uncertain else value


def merge(bindings, branches):
    if not branches:
        return
    if len(branches) == 1:
        bindings.update(
            {name: value if value == value else None for name, value in branches[0].items()}
        )
        return
    # 状态/出口的源顺序必须稳定；散列顺序会改变标签分支的展开与预算分配。
    from app.modules.action_timing.source_tasks import TaskPlan, merge_plans

    for name in dict.fromkeys(name for branch in branches for name in branch):
        values = [branch.get(name) for branch in branches]
        if name == UNKNOWN_MEMBERS:
            bindings[name] = any(value is True for value in values)
        elif name == PRIVATE_ACTIVE:
            bindings[name] = frozenset.intersection(*(value or frozenset() for value in values))
        elif name in {WRITES, FRESH, PRIVATE_PENDING, UNSTABLE}:
            bindings[name] = frozenset().union(*(value or () for value in values))
        elif isinstance(values[0], TaskPlan) and all(
            isinstance(value, TaskPlan) for value in values
        ):
            bindings[name] = merge_plans(values)
        elif all(value == values[0] for value in values):
            bindings[name] = values[0]
        else:
            bindings[name] = None


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
    args = node.child_by_field_name("arguments") or next(
        (child for child in node.children if child.type == "argument_list"), None
    )
    if args is None:
        return []
    return [
        (position, argument)
        for position, argument in enumerate(
            child for child in args.children if child.type == "argument"
        )
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


def discard_argument(index, argument, method):
    target = argument_target(argument)
    if target is None or source(target) != "_":
        return False
    return target.parent.type == "declaration_expression" or not (
        index.local_type(target, method) or member(index, method.owner, "_")
    )


def capture_ref(index, argument, method, bindings):
    if not any(child.type in {"ref", "out"} for child in argument.children):
        return None
    target = argument_target(argument)
    if target is None or discard_argument(index, argument, method):
        return None
    if target.type == "element_access_expression":
        from app.modules.action_timing import source_collections as collections

        element = collections.location(index, target, method, bindings)
        if element is None:
            return None
        data, position = element
        size = collections.length(data, bindings)
        if (
            data["<collection>"] != "array"
            or not isinstance(position, int)
            or isinstance(position, bool)
            or size is None
            or not 0 <= position < size
        ):
            collections.invalidate(data, bindings)
            return None
        slot = collections.key(data, f"item:{position}")
        if slot not in bindings:
            bindings[slot] = collections.item(data, position, bindings)
        return slot
    place = location(index, target, method, bindings)
    if place is not None:
        slot = key(place)
        if place[0] is None:
            write(index, target, method, bindings, None)
            # 通配失效槽不能当作真实地址；两个未知对象可能相同，也可能不同。
            return None
    elif target.type == "identifier":
        slot = local_slot(target, method, bindings)
        if slot is None:
            return None
    else:
        return None
    if slot not in bindings:
        bindings[slot] = index.value(target, method, bindings)
    return slot


def invalidate_byref(index, node, method, bindings):
    from app.modules.action_timing import source_arguments as call_args

    saved = call_args.snapshot(node, method, bindings)
    for position, argument in byref_arguments(node):
        slot = saved.references[position] if saved and position < len(saved.references) else None
        if slot is not None:
            bindings[slot] = None
            continue
        target = argument_target(argument)
        if target is not None and not discard_argument(index, argument, method):
            if target.type == "element_access_expression":
                from app.modules.action_timing import source_collections as collections

                element = collections.location(index, target, method, bindings)
                if element is not None:
                    collections.invalidate(element[0], bindings)
                    continue
            write(index, target, method, bindings, None)
