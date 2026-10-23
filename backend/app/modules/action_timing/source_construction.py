"""对象构造的字段初始化、this/base 链与正文；不执行设备程序集。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_collection_expressions import initializer_values
from app.modules.action_timing.source_flow import UNKNOWN, ZERO
from app.modules.action_timing.source_index import children, text
from app.modules.action_timing.source_properties import assign_property
from app.modules.action_timing.source_tasks import CLOCK, create_task


def field_initializers(
    estimator, owner, method, bindings, stack, conditions, background, static=False
):
    info = estimator.index.classes.get(owner)
    cost = ZERO
    if not info:
        return cost
    started = bindings.get(CLOCK, ZERO)
    for initializer in info.initializers:
        if initializer.is_static != static:
            continue
        bindings[CLOCK] = started.plus(cost)
        cost = cost.plus(
            estimator.invoke(
                initializer, [], method, initializer.node, bindings, stack, conditions, background
            )
        )
    bindings[CLOCK] = started
    return cost


def implicit_constructor(estimator, owner, method, node, bindings, stack, conditions, background):
    marker = f"<implicit-constructor:{owner}>"
    info = estimator.index.classes.get(owner)
    if (
        info
        and not info.initializers
        and not estimator.index.base_types(owner)
        and not estimator.index.by_method.get((owner, ".ctor"))
    ):
        return ZERO
    if marker in stack or estimator.depth(stack) >= 7:
        estimator.truncated = True
        estimator.record("unresolved", "隐式构造链未能展开", node, method, conditions, background)
        return UNKNOWN
    if owner not in estimator.index.classes:
        # 外部数据/界面对象不估算CPU初始化成本；明确的硬件类型仍保留未知。
        if "LogicHardware" in owner or owner in {
            "Axis",
            "CamAxis",
            "AKRSCamera",
            "Sensor",
            "Electric",
        }:
            estimator.record(
                "call", "外部硬件对象构造耗时未定", node, method, conditions, background
            )
            return UNKNOWN
        return ZERO
    cost = field_initializers(
        estimator, owner, method, bindings, (*stack, marker), conditions, background
    )
    for base in estimator.index.base_types(owner):
        info = estimator.index.classes.get(base)
        if not info or not any(decl.type == "class_declaration" for _, decl in info.declarations):
            continue
        target = estimator.index.constructor(base, [], method)
        before = bindings.get(CLOCK, ZERO)
        bindings[CLOCK] = before.plus(cost)
        if target:
            cost = cost.plus(
                estimator.invoke(
                    target, [], method, node, bindings, (*stack, marker), conditions, background
                )
            )
        elif estimator.index.by_method.get((base, ".ctor")):
            estimator.record(
                "unresolved", "隐式基类构造未匹配到无参入口", node, method, conditions, background
            )
            cost = cost.plus(UNKNOWN)
        else:
            cost = cost.plus(
                implicit_constructor(
                    estimator,
                    base,
                    method,
                    node,
                    bindings,
                    (*stack, marker),
                    conditions,
                    background,
                )
            )
        bindings[CLOCK] = before
    return cost


def constructor_body(estimator, method, bindings, stack, conditions, background):
    initial = next(iter(children(method.node, "constructor_initializer")), None)
    is_this = initial is not None and any(part.type == "this" for part in initial.children)
    before = (
        ZERO
        if is_this
        else field_initializers(
            estimator,
            method.owner,
            method,
            bindings,
            stack,
            conditions,
            background,
            static=method.is_static,
        )
    )
    started = bindings.get(CLOCK, ZERO)
    if initial is not None:
        args = children(next(iter(children(initial, "argument_list")), None), "argument")
        owners = [method.owner] if is_this else estimator.index.base_types(method.owner)
        target = next(
            (
                target
                for owner in owners
                if (target := estimator.index.constructor(owner, args, method))
            ),
            None,
        )
        before = call_args.evaluate(
            estimator,
            initial,
            method,
            bindings,
            stack,
            conditions,
            background,
            target=target,
            prefix=before,
        )
    else:
        args = []
        owners = [] if method.is_static else estimator.index.base_types(method.owner)
    for owner in owners:
        info = estimator.index.classes.get(owner)
        if info and not any(decl.type == "class_declaration" for _, decl in info.declarations):
            continue
        target = estimator.index.constructor(owner, args, method)
        bindings[CLOCK] = started.plus(before)
        if target:
            before = before.plus(
                estimator.invoke(
                    target,
                    args,
                    method,
                    initial or method.node,
                    bindings,
                    stack,
                    conditions,
                    background,
                )
            )
        elif estimator.index.by_method.get((owner, ".ctor")):
            estimator.record(
                "unresolved",
                "构造函数重载未绑定",
                initial or method.node,
                method,
                conditions,
                background,
            )
            before = before.plus(UNKNOWN)
        else:
            before = before.plus(
                implicit_constructor(
                    estimator,
                    owner,
                    method,
                    initial or method.node,
                    bindings,
                    stack,
                    conditions,
                    background,
                )
            )
    bindings[CLOCK] = started.plus(before)
    body = estimator.block(method.body, method, bindings, stack, conditions, background)
    bindings[CLOCK] = started
    return body.prefix(before)


def create_object(estimator, node, method, bindings, stack, conditions, background):
    arguments = children(node.child_by_field_name("arguments"), "argument")
    started = bindings.get(CLOCK, ZERO)
    owner = estimator.index.lookup_type(text(node.child_by_field_name("type")), method)
    target = estimator.index.constructor(owner, arguments, method)
    cost = call_args.evaluate(
        estimator,
        node,
        method,
        bindings,
        stack,
        conditions,
        background,
        target=target,
    )
    if create_task(estimator, node, method, bindings):
        bindings[CLOCK] = started
        return cost
    estimator.allocations += 1
    bindings[f"<allocation:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}>"] = (
        f"new:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}:{estimator.allocations}"
    )
    receiver_id = state.reference(estimator.index, node, method, bindings)
    if state.FRESH in bindings and receiver_id is not None:
        bindings[state.FRESH] = (bindings.get(state.FRESH) or frozenset()) | {receiver_id}
    bindings[CLOCK] = started.plus(cost)
    if target:
        cost = cost.plus(
            estimator.invoke(
                target, arguments, method, node, bindings, stack, conditions, background
            )
        )
    elif estimator.index.by_method.get((owner, ".ctor")):
        estimator.record("unresolved", "对象构造重载未绑定", node, method, conditions, background)
        cost = cost.plus(UNKNOWN)
    elif (
        owner in estimator.index.classes
        or "LogicHardware" in owner
        or owner in {"Axis", "CamAxis", "AKRSCamera", "Sensor", "Electric"}
    ):
        constructor_bindings = {**bindings, state.THIS: receiver_id}
        cost = cost.plus(
            implicit_constructor(
                estimator, owner, method, node, constructor_bindings, stack, conditions, background
            )
        )
        state.transfer(bindings, constructor_bindings)
    collection = collections.created(estimator.index, node, method, bindings)
    for initializer in children(node, "initializer_expression"):
        if collections.known(collection):
            bindings[CLOCK] = started.plus(cost)
            extra, values = initializer_values(
                estimator, initializer, method, bindings, stack, conditions, background
            )
            cost = cost.plus(extra)
            previous = collection.get("<items>") or ()
            size = collection.get("<length>")
            collection["<items>"] = previous + values if size == len(previous) else None
            collection["<length>"] = size + len(values) if size is not None else None
            continue
        for part in children(initializer):
            bindings[CLOCK] = started.plus(cost)
            cost = cost.plus(
                assign_property(
                    estimator,
                    part,
                    method,
                    bindings,
                    stack,
                    conditions,
                    background,
                    owner=owner,
                    receiver_id=receiver_id,
                )
                if part.type == "assignment_expression"
                else estimator.expression(part, method, bindings, stack, conditions, background)
            )
    if collections.known(collection):
        bindings[call_args.return_key(node, method, bindings)] = collection
    bindings[CLOCK] = started
    return cost
