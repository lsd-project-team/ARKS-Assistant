"""继续核对被执行预算截断的源码；条件组成不冒充已执行的同步总时长。"""

from collections import deque

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_components as components
from app.modules.action_timing import source_deferred_components
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_entry_callbacks import callback_method
from app.modules.action_timing.source_index import children, text, value_children, walk
from app.modules.action_timing.source_local_functions import lexical_walk

MAX_CONTEXTS = 20000


def numeric_value(index, node, method, bindings):
    if node is None or any(
        part.type in {"member_access_expression", "invocation_expression", "assignment_expression"}
        or part.type in {"prefix_unary_expression", "postfix_unary_expression"}
        and ("++" in text(part) or "--" in text(part))
        or part.type == "identifier"
        and (text(part) not in bindings or not components.unchanged(method, text(part)))
        for part in walk(node)
    ):
        return None
    value = index.value(node, method, bindings)
    return value if components.number(value) else None


def supplied_values(index, call, caller, target, bindings):
    if target.callable_kind == "property_set":
        parent = call.parent
        if (
            parent is not None
            and parent.type == "assignment_expression"
            and parent.child_by_field_name("left") == call
        ):
            value = numeric_value(index, parent.child_by_field_name("right"), caller, bindings)
            return (
                {"value": value}
                if value is not None and components.unchanged(target, "value")
                else {}
            )
    nodes = arguments.arguments(call)
    slots = arguments.plan(target.parameters, nodes, variadic=target.variadic)
    if slots is None or target.variadic:
        return {}
    values = {}
    for position, (name, _, default) in enumerate(target.parameters):
        sources = [nodes[n] for n, slot in enumerate(slots) if slot == position]
        if sources:
            parts = value_children(sources[0])
            node = parts[-1] if parts else None
            value = numeric_value(index, node, caller, bindings)
        else:
            value = numeric_value(index, default, target, {})
        if value is not None and components.unchanged(target, name):
            values[name] = value
    return values


def construction_links(index, owner, caller, node, seen=None):
    seen = set() if seen is None else seen
    if owner in seen or owner not in index.classes:
        return []
    seen.add(owner)
    info = index.classes[owner]
    result = [(node, m, False) for m in info.initializers if not m.is_static]
    for base in index.base_types(owner):
        target = index.constructor(base, [], caller)
        if target:
            result.append((caller.node, target, False))
        elif not index.by_method.get((base, ".ctor")):
            result.extend(construction_links(index, base, caller, node, seen))
    return result


def links(index, method):
    cache = index.__dict__.setdefault("continuation_links", {})
    if method.key in cache:
        return cache[method.key]
    result = []
    if method.callable_kind == "constructor":
        initial = next(iter(children(method.node, "constructor_initializer")), None)
        if initial is not None:
            is_this = any(p.type == "this" for p in initial.children)
            owners = [method.owner] if is_this else index.base_types(method.owner)
            for owner in owners:
                target = index.constructor(owner, arguments.arguments(initial), method)
                if target:
                    result.append((initial, target, False))
        if initial is None and not method.is_static:
            result.extend(construction_links(index, method.owner, method, method.node))
    for node in lexical_walk(method.body):
        if node.type not in {
            "invocation_expression",
            "object_creation_expression",
            "identifier",
            "member_access_expression",
        }:
            continue
        if not components.call_context(node, method)[-1]:
            continue
        target = None
        if node.type == "invocation_expression":
            target = index.resolve(node, method)
            function = (
                text(node.child_by_field_name("function"))
                .removeprefix("global::")
                .removeprefix("System.Threading.Tasks.")
            )
            if (
                function in {"Task.Run", "Task.Factory.StartNew"}
                and target is None
                and index.lookup_type("Task", method) not in index.classes
            ):
                nodes = arguments.arguments(node)
                callback = delegates.unwrap(index, nodes[0], method) if nodes else None
                if callback is not None:
                    if callback.type in {"lambda_expression", "anonymous_method_expression"}:
                        work = callback_method(
                            callback, method, f"<continuation:{callback.start_byte}>"
                        )
                    else:
                        work = delegates.method_group(index, callback, method)
                    if work:
                        result.append((node, work, True))
        elif node.type == "object_creation_expression":
            owner = index.lookup_type(text(node.child_by_field_name("type")), method)
            target = index.constructor(owner, arguments.arguments(node), method)
            if owner in index.classes:
                for initializer in index.classes[owner].initializers:
                    if not initializer.is_static:
                        result.append((node, initializer, False))
                if target is None and not index.by_method.get((owner, ".ctor")):
                    result.extend(construction_links(index, owner, method, node))
        elif node.type in {"identifier", "member_access_expression"}:
            parent = node.parent
            selector = (
                parent
                and parent.type == "member_access_expression"
                and parent.child_by_field_name("name") == node
            )
            assigned = (
                parent
                and parent.type == "assignment_expression"
                and parent.child_by_field_name("left") == node
            )
            if not selector:
                target = index.accessor(node, method, "set" if assigned else "get")
        if target and target.body is not None and not index.polymorphic(node, method, target):
            result.append((node, target, False))
    cache[method.key] = tuple(result)
    return cache[method.key]


def collect(index, roots, existing):
    seen, facts, cycles = set(), [], set()
    known = {
        (
            part.get("method"),
            part["milliseconds"],
            tuple((s["path"], s["line"]) for s in part["sources"]),
            tuple(part["conditions"]),
        )
        for part in existing
    }
    seeds = deque(roots)
    pending = deque()
    visited_methods = set()
    edges = 0
    while (pending or seeds) and len(seen) < MAX_CONTEXTS:
        if not pending:
            seed = seeds.popleft()
            if seed.key in visited_methods:
                continue
            pending.append((seed, {}, (), (), False))
        method, values, ancestry, route, deferred = pending.popleft()
        if method.key in ancestry:
            cycles.add(method.key)
            continue  # 不把递归引用次数当作实际执行次数。
        identity = (method.key, tuple(sorted(values.items())), deferred)
        if identity in seen:
            continue
        seen.add(identity)
        visited_methods.add(method.key)
        for fact in (
            *components.literal_waits(index, method, values),
            *source_deferred_components.task_waits(index, method),
        ):
            key = (
                fact.get("method"),
                fact["milliseconds"],
                tuple((s["path"], s["line"]) for s in fact["sources"]),
                tuple(fact["conditions"]),
            )
            if key in known:
                continue
            known.add(key)
            facts.append(
                {
                    **fact,
                    "conditions": [
                        *(["后台回调实际启动"] if deferred else []),
                        *(route[-3:]),
                        *fact["conditions"],
                    ],
                    "deferred": deferred or fact.get("deferred", False),
                    "note": "沿尚未完全展开的源码调用链继续核对，"
                    "显示此子方法单次进入相应分支的等待组成；"
                    "实际调用次数、分支与完成关系另行确定，不累加到汇总。",
                }
            )
        for node, target, background in links(index, method):
            if not components.bound_context(index, node, method, values):
                continue
            edges += 1
            supplied = {} if background else supplied_values(index, node, method, target, values)
            location = (
                f"{method.owner}.{method.name} → {target.owner}.{target.name}"
                f"（{method.unit.path}:{node.start_point[0] + 1}）"
            )
            pending.append(
                (
                    target,
                    supplied,
                    (*ancestry, method.key),
                    (*route, location),
                    deferred or background,
                )
            )
    value_limits = [
        target
        for (key, _), target in index.__dict__.get("component_expression_limits", {}).items()
        if key in visited_methods
    ]
    return facts, {
        "source_methods": len(seen),
        "call_edges": edges,
        "recursive_targets": sorted(cycles),
        "pending_contexts": len(pending)
        + sum(m.key not in visited_methods for m in seeds)
        + len(value_limits),
        "pending_targets": [
            {"method": m.key, "path": m.unit.path, "line": m.node.start_point[0] + 1}
            for m in [
                *(p[0] for p in pending),
                *(m for m in seeds if m.key not in visited_methods),
            ][:20]
        ]
        + value_limits[:20],
    }
