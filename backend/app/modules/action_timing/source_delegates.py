"""只展开源码已绑定的委托；创建、传递与执行是三个不同的时点。"""

from dataclasses import dataclass, replace

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_closures as closures
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost
from app.modules.action_timing.source_index import children, simple_type, text, walk

DELEGATE_PREFIX = "<delegate-variable:"
NULL_DELEGATE = object()
RESULT = "<delegate-result>"


@dataclass(frozen=True)
class BoundDelegate:
    node: object
    method_key: str
    receiver_id: object = state.MISSING
    closure: object = None
    arity: int = 0
    returns_task: bool = False
    async_void: bool = False
    discards_result: bool = False
    signature: str = ""


def unwrap(index, node, method, bindings=None):
    if isinstance(node, BoundDelegate) or node is NULL_DELEGATE:
        return node
    while node is not None:
        if node.type in {"argument", "parenthesized_expression"}:
            parts = children(node)
            node = parts[-1] if parts else None
        elif node.type == "cast_expression":
            node = node.child_by_field_name("value")
        elif node.type == "object_creation_expression":
            kind = index.lookup_type(text(node.child_by_field_name("type")), method)
            args = children(node.child_by_field_name("arguments"), "argument")
            if (
                kind in index.classes
                or simple_type(kind)
                not in {"Action", "Func", "MethodInvoker", "SendOrPostCallback"}
                or len(args) != 1
            ):
                return None
            node = args[0]
        else:
            break
    if node is not None and node.type in {"identifier", "member_access_expression"}:
        value = stored(node, method, bindings or {}, index)
        if value is not None:
            return value
    if node is not None and node.type in {"element_access_expression", "invocation_expression"}:
        value = index.value(node, method, bindings or {})
        if isinstance(value, BoundDelegate) or value is NULL_DELEGATE:
            return value
    return node


def method_group(index, node, caller, arity=0):
    if isinstance(node, BoundDelegate):
        node = node.node
    if node is None:
        return None
    if node.type == "identifier" and text(node) not in caller.types:
        owner, name = caller.owner, text(node)
    elif node.type == "member_access_expression":
        owner = index.infer(node.child_by_field_name("expression"), caller)
        name = text(node.child_by_field_name("name"))
    else:
        return None
    seen = set()
    pending = [owner]
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        candidates = [
            target
            for target in index.by_method.get((current, name), [])
            if len(target.parameters) == arity
        ]
        if candidates:
            return candidates[0] if len(candidates) == 1 else None
        pending.extend(index.base_types(current))
    return None


def execute(
    estimator,
    node,
    method,
    bindings,
    stack,
    conditions,
    background,
    join_result=True,
    argument_values=(),
    creation_only=False,
    argument_types=(),
):
    from app.modules.action_timing.source_tasks import CLOCK, is_fresh, task_ids

    bindings.pop(RESULT, None)
    previous_tasks = task_ids(bindings.values())
    bound = capture(estimator.index, node, method, bindings)
    node = bound.node if isinstance(bound, BoundDelegate) else None
    start = len(estimator.stages)
    started = bindings.get(CLOCK, ZERO)
    if node is None:
        return UNKNOWN
    declaration = bound.closure.method
    marker = f"<delegate:{bound.method_key}:{node.start_byte}:{node.end_byte}>"
    if marker in stack or estimator.depth(stack) >= 7 or estimator.calls >= 120:
        estimator.truncated = True
        estimator.record(
            "unresolved", "回调达到展开边界", node, declaration, conditions, background
        )
        return UNKNOWN
    estimator.calls += 1
    if node.type in {"lambda_expression", "anonymous_method_expression"}:
        if len(closures.parameters(node)) != len(argument_values):
            return UNKNOWN
        callback_method, callback_scope = closures.enter(
            estimator, bound, node, bindings, argument_values, argument_types
        )
        is_async = any(text(part) == "async" for part in node.children)
        body = node.child_by_field_name("body")
        if is_async:
            from app.modules.action_timing import source_async

            cost, plan = source_async.execute(
                estimator, callback_method, callback_scope, (*stack, marker), conditions, background
            )
            bindings[RESULT] = plan if bound.returns_task else None
        elif body and body.type != "block":
            cost = estimator.expression(
                body,
                callback_method,
                callback_scope,
                (*stack, marker),
                conditions,
                background,
            )
            bindings[RESULT] = estimator.index.value(body, callback_method, callback_scope)
        else:
            flow = estimator.block(
                body,
                callback_method,
                callback_scope,
                (*stack, marker),
                conditions,
                background,
            )
            cost = flow.cost() if flow.live is not None or flow.returned is not None else UNKNOWN
            bindings[RESULT] = flow.states.get("returned", {}).get("<return-value>")
        state.transfer(bindings, callback_scope)
        from app.modules.action_timing.source_tasks import TaskPlan, join_stages, known_task

        plan = bindings.get(RESULT)
        if join_result and not creation_only and not bound.discards_result and known_task(plan):
            cost = cost.plus(plan.remaining(started.plus(cost)))
            join_stages(estimator, plan, background)
            if isinstance(plan, TaskPlan) and is_fresh(plan, previous_tasks):
                bindings.update(plan.effects)
                bindings[RESULT] = plan.result
        if bound.discards_result:
            bindings[RESULT] = None
    else:
        target = method_group(estimator.index, node, declaration, len(argument_values))
        if target is None or estimator.index.polymorphic(node, declaration, target):
            estimator.record(
                "unresolved",
                "委托方法或实际实例类型未绑定",
                node,
                declaration,
                conditions,
                background,
            )
            return UNKNOWN
        target_context = bindings
        cost = estimator.invoke(
            target,
            [],
            declaration,
            node,
            target_context,
            stack,
            conditions,
            background,
            receiver_id=bound.receiver_id,
            argument_values={
                name: value
                for (name, _, _), value in zip(target.parameters, argument_values, strict=True)
            },
        )
        bindings[RESULT] = target_context.get(
            call_args.return_key(node, declaration, target_context)
        )
        if bound.async_void:
            bindings[RESULT] = None
        from app.modules.action_timing.source_task_returns import task_method
        from app.modules.action_timing.source_tasks import TaskPlan, join_stages, known_task

        if task_method(estimator.index, target) and join_result and not creation_only:
            plan = bindings.get(RESULT)
            if known_task(plan):
                cost = cost.plus(plan.remaining(started.plus(cost)))
                join_stages(estimator, plan, background)
                if isinstance(plan, TaskPlan) and is_fresh(plan, previous_tasks):
                    bindings.update(plan.effects)
                bindings[RESULT] = getattr(plan, "result", None)
            else:
                cost = Cost(cost.lower, None)
    if any(
        stage["kind"] in {"motion", "wait", "call", "unresolved"}
        and not stage.get("resolved")
        and not stage["background"]
        for stage in estimator.stages[start:]
    ):
        cost = Cost(cost.lower, None)
    return cost


def capture(
    index,
    node,
    method,
    bindings,
    arity=0,
    returns_task=None,
    discards_result=False,
    signature_kind="",
):
    if isinstance(node, BoundDelegate) or node is NULL_DELEGATE:
        return node
    from app.modules.action_timing import source_dynamic

    kind = source_dynamic.explicit_signature(index, node, method) or signature_kind
    shape = source_dynamic.signature(index, kind, method) if kind else None
    explicit = explicit_return_kind(index, node, method)
    discards_result |= explicit is False
    if shape is not None:
        arity = len(shape[0])
        explicit = False if shape[1] == "void" else simple_type(shape[1]) == "Task"
        discards_result |= shape[1] == "void"
    if returns_task is None:
        returns_task = explicit
    node = unwrap(index, node, method, bindings)
    if isinstance(node, BoundDelegate):
        return node
    if node is NULL_DELEGATE or (node is not None and node.type == "null_literal"):
        return NULL_DELEGATE
    if node is None:
        return None
    if node.type in {"lambda_expression", "anonymous_method_expression"}:
        # 创建时冻结可见局部类型，包括外层条件中的模式变量；进入回调后
        # 词法父节点不再属于回调自己的方法体，不能仅靠祖先遍历恢复它们。
        captured_types = dict(method.types)
        for part in walk(node):
            if part.type == "identifier" and (kind_at_use := index.local_type(part, method)):
                captured_types[text(part)] = kind_at_use
        method = replace(method, types=captured_types)
        asynchronous = any(text(part) == "async" for part in node.children)
        return BoundDelegate(
            node,
            method.key,
            closure=closures.capture(method, bindings, node),
            arity=len(closures.parameters(node)),
            returns_task=asynchronous if returns_task is None else returns_task,
            async_void=asynchronous and returns_task is False,
            discards_result=discards_result,
            signature=kind,
        )
    target = method_group(index, node, method, arity)
    if target is None:
        return None
    receiver = state.receiver_for(index, target, node, method, bindings)
    return BoundDelegate(
        node,
        method.key,
        receiver,
        closures.Closure(method, bindings.get(state.THIS), ()),
        arity,
        simple_type(text(target.node.child_by_field_name("returns"))) == "Task",
        any(text(part) == "async" for part in target.node.children)
        and text(target.node.child_by_field_name("returns")) == "void",
        discards_result,
        kind,
    )


def explicit_return_kind(index, node, method):
    while node is not None and not isinstance(node, BoundDelegate):
        if node.type in {"argument", "parenthesized_expression"}:
            parts = children(node)
            node = parts[-1] if parts else None
            continue
        if node.type not in {"cast_expression", "object_creation_expression"}:
            break
        kind = text(node.child_by_field_name("type"))
        if simple_type(kind) == "Action" and index.lookup_type(kind, method) not in index.classes:
            return False
        break
    return None


def signature_arity(kind):
    if kind in {"MethodInvoker", "System.Windows.Forms.MethodInvoker"}:
        return 0
    if kind in {"SendOrPostCallback", "System.Threading.SendOrPostCallback"}:
        return 1
    base, separator, suffix = kind.replace("System.", "").partition("<")
    if base == "Action" and not separator:
        return 0
    if base not in {"Action", "Func"} or not separator:
        return None
    depth, count = 0, 1
    for char in suffix[:-1]:
        depth += (char == "<") - (char == ">")
        if char == "," and depth == 0:
            count += 1
    return count - (base == "Func")


def bind_arguments(index, target, arguments, caller, bindings, saved=None):
    result = {}
    slots = call_args.plan(target.parameters, arguments, variadic=target.variadic)
    sources = {slot: position for position, slot in enumerate(slots or ())}
    for slot, (name, kind, default) in enumerate(target.parameters):
        arity = signature_arity(kind)
        generic = kind in {
            "Delegate",
            "System.Delegate",
            "MulticastDelegate",
            "System.MulticastDelegate",
        }
        if (arity is None and not generic) or index.lookup_type(kind, target) in index.classes:
            continue
        position = sources.get(slot)
        value = arguments[position] if position is not None else default
        bound = (
            saved.callbacks[position]
            if saved is not None
            and position is not None
            and saved.callbacks[position] is not state.MISSING
            else capture(
                index,
                value,
                caller,
                bindings,
                arity or 0,
                returns_task=None
                if generic
                else "Task" in kind and kind.replace("System.", "").startswith("Func<"),
                discards_result=kind.replace("System.", "").split("<", 1)[0] == "Action",
                signature_kind=kind,
            )
            if value is not None
            else None
        )
        result[f"{DELEGATE_PREFIX}{name}>"] = (target.key, bound)
    return result


def stored(node, method, bindings, index=None):
    if node is None:
        return None
    if index is not None:
        if state.is_unstable(index, node, method, bindings):
            return None
        value = index.value(node, method, bindings)
        if isinstance(value, BoundDelegate) or value is NULL_DELEGATE:
            return value
        current = state.read(index, node, method, bindings)
        if current is not state.MISSING:
            return None
    record = bindings.get(f"{DELEGATE_PREFIX}{text(node)}>")
    return record[1] if record and record[0] == method.key else None


def invocation_receiver(index, node, method):
    function = node.child_by_field_name("function")
    if function is None:
        return None
    if function.type == "identifier":
        candidate = function
    elif function.type == "conditional_access_expression":
        name = next(iter(children(function, "member_binding_expression")), None)
        candidate = (
            function.child_by_field_name("condition")
            if text(name.child_by_field_name("name") if name else None) == "Invoke"
            else None
        )
    else:
        candidate = (
            function.child_by_field_name("expression")
            if text(function.child_by_field_name("name")) == "Invoke"
            else None
        )
    return candidate


def typed_invocation(index, node, method):
    receiver = invocation_receiver(index, node, method)
    if receiver is None:
        return False
    kind = index.infer(receiver, method)
    return kind not in index.classes and simple_type(kind) in {
        "Action",
        "Func",
        "MethodInvoker",
        "SendOrPostCallback",
    }


def invoke(estimator, node, method, bindings, stack, conditions, background):
    receiver = invocation_receiver(estimator.index, node, method)
    if receiver is None:
        return None
    saved = call_args.snapshot(node, method, bindings)
    bound = saved.receiver_value if saved is not None else state.MISSING
    if bound is state.MISSING:
        bound = (
            stored(receiver, method, bindings, estimator.index) if receiver is not None else None
        )
    if (
        not isinstance(bound, BoundDelegate)
        and bound is not NULL_DELEGATE
        and not typed_invocation(estimator.index, node, method)
    ):
        return None
    if not isinstance(bound, BoundDelegate):
        estimator.record(
            "unresolved", "委托目标为空或尚未绑定", node, method, conditions, background
        )
        return UNKNOWN
    arguments = children(node.child_by_field_name("arguments"), "argument")
    # Action/Func.Invoke的命名参数属于框架签名，不能用用户lambda的参数名猜测。
    if any(call_args.argument_name(arg) is not None for arg in arguments):
        estimator.record(
            "unresolved", "委托命名参数签名未绑定", node, method, conditions, background
        )
        return UNKNOWN
    values = call_args.values(estimator.index, node, method, bindings)
    return invoke_bound(
        estimator, node, bound, method, bindings, stack, conditions, background, values
    )


def invoke_bound(
    estimator, node, bound, method, bindings, stack, conditions, background, values, types=()
):
    from app.modules.action_timing.source_tasks import (
        CLOCK,
        TaskPlan,
        is_fresh,
        known_task,
        remember_plan,
        task_ids,
    )

    previous_tasks = task_ids(bindings.values())

    cost = execute(
        estimator,
        bound,
        method,
        bindings,
        stack,
        conditions,
        background,
        argument_values=values,
        argument_types=types,
        join_result=False,
        creation_only=bound.returns_task,
    )
    result = bindings.get(RESULT)
    if bound.returns_task or known_task(result):
        result = (
            result
            if known_task(result)
            else TaskPlan(bindings.get(CLOCK, ZERO).plus(cost), UNKNOWN)
        )
        remember_plan(node, method, bindings, result, fresh=is_fresh(result, previous_tasks))
    else:
        bindings[call_args.return_key(node, method, bindings)] = result
    estimator.record(
        "call",
        "调用任务回调的同步前段" if known_task(result) else "执行已绑定回调",
        node,
        method,
        conditions,
        background,
        resolved=cost.upper is not None,
        milliseconds=cost.lower if cost.lower == cost.upper else None,
    )
    return cost
