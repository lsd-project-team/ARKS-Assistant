"""只读核对静态委托的源码写入候选；只供副作用并集，不据此绑定运行时目标。"""

from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_index import text, walk


def member(index, node, method):
    if node is None:
        return None
    if node.type == "identifier" and not index.local_type(node, method):
        owner, name = method.owner, text(node)
    elif node.type == "member_access_expression":
        owner = index.infer(node.child_by_field_name("expression"), method)
        name = text(node.child_by_field_name("name"))
    else:
        return None
    place = state.member(index, owner, name)
    return (place[0], name) if place and place[1] else None


def inventory(index):
    cached = index.__dict__.get("static_delegate_writes")
    if cached is not None:
        return cached
    from app.modules.action_timing.source_dynamic import signature

    fields = {
        (owner, name): []
        for owner, info in index.classes.items()
        for name in info.static_members & info.field_members
        if signature(index, info.types[name], owner) is not None
    }
    seen = set()
    for info in index.classes.values():
        for method in info.methods:
            for node in walk(method.body):
                if node.type not in {"assignment_expression", "argument"}:
                    continue
                identity = (method.unit.path, node.type, node.start_byte)
                if identity in seen:
                    continue
                seen.add(identity)
                if node.type == "assignment_expression":
                    field = member(index, node.child_by_field_name("left"), method)
                    if field in fields:
                        fields[field].append((node.child_by_field_name("right"), method))
                elif node.type == "argument" and any(
                    c.type in {"ref", "out"} for c in node.children
                ):
                    field = member(index, state.argument_target(node), method)
                    if field in fields:
                        fields[field].append((None, method))
        for name in info.static_members & info.field_members:
            if (info.name, name) not in fields or name not in info.defaults:
                continue
            unit, node = info.defaults[name]
            context = next((method for method in info.methods if method.unit is unit), None)
            if context is not None:
                fields[info.name, name].append((node, context))
    index.static_delegate_writes = fields
    return fields


def possible_methods(index, node, method):
    """未知写入/别名/虚目标继续未定；不按委托名称设置只读白名单。"""
    field = member(index, node, method)
    writes = inventory(index).get(field)
    if not writes or len(writes) > 128:
        return None
    result = {}
    kind = index.classes[field[0]].types[field[1]]
    for value, caller in writes:
        if value is not None and value.type == "null_literal":
            continue
        bound = delegates.capture(index, value, caller, {}, signature_kind=kind)
        if not isinstance(bound, delegates.BoundDelegate):
            return None
        for callback in bound.targets or (bound,):
            target = delegates.method_group(
                index, callback.node, callback.closure.method, callback.arity
            )
            if target is None or index.polymorphic(callback.node, callback.closure.method, target):
                return None
            result[target.key] = target
    return list(result.values()) if result else None
