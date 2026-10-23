"""WinForms及同步上下文的派发边界；不创建窗口、线程或执行设备代码。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_dynamic
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO
from app.modules.action_timing.source_hardware import receiver_declaration
from app.modules.action_timing.source_index import children, simple_type, text, walk
from app.modules.action_timing.source_tasks import (
    CLOCK,
    is_fresh,
    known_task,
    remember_plan,
    task_ids,
)

CONTROL_TYPES = {
    "System.Windows.Forms.Control",
    "System.Windows.Forms.Form",
    "System.Windows.Forms.UserControl",
    "System.Windows.Forms.ListView",
    "DevExpress.XtraEditors.XtraForm",
    "DevExpress.XtraEditors.XtraUserControl",
    "DevExpress.XtraEditors.SimpleButton",
}
CONTEXT_TYPES = {
    "System.Threading.SynchronizationContext",
    "System.Windows.Forms.WindowsFormsSynchronizationContext",
}


def function_parts(node):
    function = node.child_by_field_name("function")
    if function is None:
        return None, ""
    if function.type == "identifier":
        return None, text(function)
    if function.type == "conditional_access_expression":
        member = next(iter(children(function, "member_binding_expression")), None)
        return function.child_by_field_name("condition"), text(
            member.child_by_field_name("name")
        ) if member else ""
    return function.child_by_field_name("expression"), text(function.child_by_field_name("name"))


def receiver_kind(index, node, method):
    receiver, name = function_parts(node)
    if name not in {"Send", "Post", "Invoke", "BeginInvoke"}:
        return None
    if receiver is None and (name in method.types or index.member_type(method.owner, name)):
        return None
    if index.has_source_call(node, method):
        return None  # 自有同名实现或重载不完整时，不能替换成框架派发。
    owner = index.infer(receiver, method) if receiver is not None else method.owner
    pending, seen = [(owner, method.unit)], set()
    declaration = receiver_declaration(index, receiver, method)
    if declaration is not None:
        pending.append((owner, declaration))
    while pending:
        owner, unit = pending.pop()
        if (owner, unit.path) in seen:
            continue
        seen.add((owner, unit.path))
        info = index.classes.get(owner)
        if info is not None:
            pending.extend(
                (base, unit) for base in index.base_types(owner) for unit, _ in info.declarations
            )
            continue
        for family, kinds, operations in (
            ("context", CONTEXT_TYPES, {"Send", "Post"}),
            ("control", CONTROL_TYPES, {"Invoke", "BeginInvoke"}),
        ):
            if name not in operations:
                continue
            if any(
                owner == kind
                or (owner == simple_type(kind) and kind.rsplit(".", 1)[0] in unit.namespaces)
                for kind in kinds
            ):
                return family
    return None


def callback_position(index, node, method):
    family = receiver_kind(index, node, method)
    if family is None:
        return None
    nodes = call_args.arguments(node)
    if family == "context":
        slots = call_args.plan([("d", "", None), ("state", "", None)], nodes)
    else:
        slots = call_args.plan([("method", "", None), ("args", "", None)], nodes, variadic=True)
    return (family, slots.index(0)) if slots is not None and 0 in slots else None


def capture_callback(index, node, method, bindings, family):
    return delegates.capture(
        index,
        node,
        method,
        bindings,
        arity=1 if family == "context" else 0,
        returns_task=False if family == "context" else None,
        discards_result=family == "context",
        signature_kind="System.Threading.SendOrPostCallback" if family == "context" else "",
    )


def prepare(index, node, method, bindings, family, position):
    nodes = call_args.arguments(node)
    saved = call_args.snapshot(node, method, bindings)
    bound = saved.callbacks[position] if saved is not None else state.MISSING
    if bound is state.MISSING:
        bound = capture_callback(index, nodes[position], method, bindings, family)
    values = call_args.values(index, node, method, bindings)
    if family == "context":
        return bound, (values[1 - position],), ("object",)
    positions = [number for number in range(len(nodes)) if number != position]
    # 只投影args部分；回调实参仍在原调用中按源顺序求值。
    parts = [nodes[number] for number in positions]
    prepared = source_dynamic.argument_values(
        index, parts, tuple(values[number] for number in positions), method, bindings
    )
    return (bound, *prepared) if prepared is not None else (None, (), ())


def constant_local(method, name):
    node = method.initializers.get(name)
    parent = node.parent if node is not None else None
    while parent is not None and parent.type not in {"local_declaration_statement", "block"}:
        parent = parent.parent
    return (
        parent is not None
        and parent.type == "local_declaration_statement"
        and any(text(part) == "const" for part in parent.children)
    )


def reassigned(method, name):
    cache = method.unit.__dict__.setdefault("dispatch_written_names", {})
    body = method.body
    key = (body.start_byte, body.end_byte) if body is not None else None
    if key not in cache:
        written = set()
        for part in walk(body):
            if part.type in {
                "assignment_expression",
                "prefix_unary_expression",
                "postfix_unary_expression",
            }:
                written.add(
                    text(part.child_by_field_name("left") or part.child_by_field_name("operand"))
                )
            if part.type == "argument" and any(
                child.type in {"ref", "out"} for child in part.children
            ):
                written.add(text(state.argument_target(part)))
        cache[key] = frozenset(written)
    return name in cache[key]


def queued_scope(bound, bindings):
    scope = dict(bindings)
    captured = [
        bound,
        *(
            value
            for value in state.context(bindings).values()
            if isinstance(value, delegates.BoundDelegate)
        ),
    ]
    constants = {
        slot
        for callback in captured
        for name, slot in callback.closure.cells
        if constant_local(callback.closure.method, name)
    }
    methods = [bound.closure.method]
    methods.extend(
        value.closure.method
        for value in state.context(bindings).values()
        if isinstance(value, delegates.BoundDelegate)
    )
    for key, value in state.context(scope).items():
        if key.startswith(state.LOCAL_PREFIX):
            name = key.rsplit("|", 1)[-1].removesuffix(">")
            stable_delegate = isinstance(value, delegates.BoundDelegate) and not any(
                reassigned(method, name) for method in methods
            )
            if (
                key not in constants
                and not stable_delegate
                and not known_task(value)
                and not isinstance(value, dict)
            ):
                scope[key] = None
        elif key.startswith(state.PREFIX):
            scope[key] = None
        if collections.known(value):
            collections.invalidate(value, scope)
    scope[state.UNKNOWN_MEMBERS] = True
    scope[state.WRITES] = frozenset()
    scope[state.FRESH] = frozenset()
    scope[CLOCK] = bindings.get(CLOCK, ZERO).plus(UNKNOWN)
    return scope


def handle(estimator, node, method, bindings, stack, conditions, background):
    position = callback_position(estimator.index, node, method)
    if position is None:
        return None
    family, position = position
    bound, values, types = prepare(estimator.index, node, method, bindings, family, position)
    receiver, name = function_parts(node)
    asynchronous = name in {"Post", "BeginInvoke"}
    shape = (
        source_dynamic.signature(estimator.index, bound.signature, bound.closure.method)
        if isinstance(bound, delegates.BoundDelegate)
        else None
    )
    valid_types = not shape or (
        len(shape[0]) == len(types)
        and all(
            source_dynamic.compatible(expected, actual)
            for expected, actual in zip(shape[0], types, strict=True)
        )
    )
    if (
        not isinstance(bound, delegates.BoundDelegate)
        or bound.arity != len(values)
        or not valid_types
    ):
        if asynchronous and not isinstance(bound, delegates.BoundDelegate):
            from app.modules.action_timing.source_parallel import invalidate_unexplored
            from app.modules.action_timing.source_private_state import remember

            remember(bindings, None)
            invalidate_unexplored(bindings)
        estimator.record(
            "unresolved",
            "派发回调或参数尚未绑定",
            node,
            method,
            conditions,
            background,
            dispatch=True,
        )
        return UNKNOWN
    snapshot = call_args.snapshot(node, method, bindings)
    receiver_value = snapshot.receiver_value if snapshot is not None else state.MISSING
    if receiver_value is state.MISSING:
        receiver_value = (
            estimator.index.value(receiver, method, bindings) if receiver is not None else None
        )
    actual = (
        estimator.index.lookup_type(receiver_value.get("<type>", ""), method)
        if isinstance(receiver_value, dict)
        else ""
    )
    if actual in estimator.index.classes and estimator.index.by_method.get((actual, name)):
        estimator.record(
            "unresolved",
            "实际实例有源码派发重载，框架契约不替代它",
            node,
            method,
            conditions,
            background,
            dispatch=True,
        )
        return UNKNOWN
    if asynchronous:
        from app.modules.action_timing.source_private_state import activate, remember

        activity = remember(bindings, bound)
    scope = queued_scope(bound, bindings) if asynchronous else bindings
    if asynchronous:
        activate(estimator.index, scope, activity)
    start = len(estimator.stages)
    previous = task_ids(bindings.values())
    cost = delegates.execute(
        estimator,
        bound,
        method,
        scope,
        stack,
        (*conditions, "派发成功并执行回调"),
        background or asynchronous,
        argument_values=values,
        argument_types=types,
        join_result=False,
    )
    result = scope.get(delegates.RESULT)
    if asynchronous:
        state.transfer(
            bindings, {state.PRIVATE_PENDING: scope.get(state.PRIVATE_PENDING)}, uncertain=True
        )
        for stage in estimator.stages[start:]:
            stage["background"] = True
        unknown_target = any(
            stage["kind"] == "unresolved"
            and stage["label"]
            in {"委托目标为空或尚未绑定", "反射委托目标或参数签名未绑定", "回调达到展开边界"}
            for stage in estimator.stages[start:]
        )
        if estimator.truncated or unknown_target:
            from app.modules.action_timing.source_parallel import invalidate_unexplored

            invalidate_unexplored(bindings)
        else:
            for key in scope.get(state.WRITES, ()):
                if key.startswith((state.PREFIX, state.LOCAL_PREFIX, state.COLLECTION_PREFIX)):
                    bindings[key] = None
                    state.mark_write(bindings, key)
        estimator.record(
            "background",
            "回调已排队，完成时间未定",
            node,
            method,
            conditions,
            True,
            dispatch=True,
            note="排队后的共享状态可能变化，后台回调不并入发起者经过时间；未估计UI线程和调度开销",
        )
        bindings[call_args.return_key(node, method, bindings)] = None
        return ZERO
    if name == "Invoke":
        if known_task(result):
            remember_plan(node, method, bindings, result, fresh=is_fresh(result, previous))
        else:
            bindings[call_args.return_key(node, method, bindings)] = result
    concrete_base = (
        family == "context"
        and isinstance(receiver_value, dict)
        and receiver_value.get("<type>")
        in {"SynchronizationContext", "System.Threading.SynchronizationContext"}
    )
    estimator.record(
        "call" if concrete_base else "wait",
        "同步回调返回" if concrete_base else "同步派发队列/窗口条件未定",
        node,
        method,
        conditions,
        background,
        dispatch=True,
        resolved=concrete_base,
        note="同步派发仅等待回调返回；回调返回的Task仍需源码显式等待，不将发起当作异步体完成",
    )
    return cost if concrete_base else UNKNOWN.plus(cost)
