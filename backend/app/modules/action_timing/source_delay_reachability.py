"""展开受限时核对源码中是否还有可识别停留；CPU未知与停留范围分别处理。"""

import re

from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_hardware import hardware_operation
from app.modules.action_timing.source_index import children, text, walk


def possible(index, method):
    cache = getattr(index, "delay_reachability", None)
    if cache is None:
        cache = index.delay_reachability = {}
    identity = (method.key, method.type_scope)
    if identity in cache:
        return cache[identity]
    pending, seen = [method], set()
    while pending:
        current = pending.pop()
        key = (current.key, current.type_scope)
        if key in seen or cache.get(key) is False:
            continue
        if cache.get(key) is True or len(seen) >= 1000:
            cache[identity] = True
            return True
        seen.add(key)
        for node in walk(current.body):
            target = None
            if node.type == "invocation_expression":
                function = text(node.child_by_field_name("function"))
                target = index.resolve(node, current)
                if (
                    re.search(r"Sleep|Delay", function.rsplit(".", 1)[-1], re.I)
                    or hardware_operation(index, node, current)
                    or delegates.typed_invocation(index, node, current)
                    or (target and index.polymorphic(node, current, target))
                    or (target is None and index.has_source_call(node, current))
                ):
                    cache[identity] = True
                    return True
            elif node.type == "object_creation_expression":
                owner = index.lookup_type(text(node.child_by_field_name("type")), current)
                if owner in index.classes:
                    pending.extend(index.by_method.get((owner, ".ctor"), []))
                    pending.extend(index.classes[owner].initializers)
                    for base in index.base_types(owner):
                        pending.extend(index.by_method.get((base, ".ctor"), []))
                        if base in index.classes:
                            pending.extend(index.classes[base].initializers)
            elif node.type in {"identifier", "member_access_expression"}:
                parent = node.parent
                assigned = (
                    parent is not None
                    and parent.type == "assignment_expression"
                    and parent.child_by_field_name("left") == node
                )
                target = index.accessor(node, current, "set" if assigned else "get")
                if assigned and text(parent.child_by_field_name("operator")) != "=":
                    getter = index.accessor(node, current, "get")
                    if getter:
                        pending.append(getter)
            if target and target.body is not None:
                pending.append(target)
        if current.callable_kind == "constructor":
            initial = next(iter(children(current.node, "constructor_initializer")), None)
            owners = (
                [current.owner]
                if initial is not None and any(n.type == "this" for n in initial.children)
                else index.base_types(current.owner)
            )
            for owner in owners:
                pending.extend(index.by_method.get((owner, ".ctor"), []))
                if owner in index.classes:
                    pending.extend(index.classes[owner].initializers)
    # 已遍历完全部可绑定边，seen里的纯CPU路径都不含可识别停留。
    for key in seen:
        cache[key] = False
    return False
