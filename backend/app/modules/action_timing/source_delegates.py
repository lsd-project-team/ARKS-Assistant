"""只展开源码已绑定的委托；创建、传递与执行是三个不同的时点。"""

from dataclasses import dataclass

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost
from app.modules.action_timing.source_index import children, simple_type, text, walk

DELEGATE_PREFIX = "<delegate-variable:"


@dataclass(frozen=True)
class BoundDelegate:
    node: object
    method_key: str
    receiver_id: object = state.MISSING


def unwrap(index, node, method, bindings=None):
    if isinstance(node, BoundDelegate):
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
                or simple_type(kind) not in {"Action", "Func"}
                or len(args) != 1
            ):
                return None
            node = args[0]
        else:
            break
    if node is not None and node.type in {"identifier", "member_access_expression"}:
        stored = (bindings or {}).get(f"{DELEGATE_PREFIX}{text(node)}>")
        if stored:
            source_method, value = stored
            return value if source_method == method.key else None
    return node


def method_group(index, node, caller):
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
            target for target in index.by_method.get((current, name), []) if not target.parameters
        ]
        if candidates:
            return candidates[0] if len(candidates) == 1 else None
        pending.extend(index.base_types(current))
    return None


def execute(estimator, node, method, bindings, stack, conditions, background, join_result=True):
    from app.modules.action_timing.source_tasks import CLOCK

    bound = capture(estimator.index, node, method, bindings)
    node = bound.node if bound else None
    start = len(estimator.stages)
    started = bindings.get(CLOCK, ZERO)
    if node is None:
        return UNKNOWN
    if node.type in {"lambda_expression", "anonymous_method_expression"}:
        parameters = node.child_by_field_name("parameters")
        if parameters is not None and children(parameters):
            return UNKNOWN
        if node.child_by_field_name("parameter") is not None:
            return UNKNOWN
        nested_async = not join_result and any(text(part) == "async" for part in node.children)
        body = node.child_by_field_name("body")
        if body and body.type != "block":
            cost = estimator.expression(
                body, method, bindings, stack, conditions, background or nested_async
            )
        else:
            flow = estimator.block(
                body, method, bindings, stack, conditions, background or nested_async
            )
            cost = flow.cost() if flow.live is not None or flow.returned is not None else UNKNOWN
        if join_result:
            cost = returned_task(body, method, bindings, cost, started)
        # StartNew(async ...)返回嵌套任务；没有Unwrap不能把整个异步体当作外层完成边界。
        if nested_async:
            estimator.record(
                "unresolved",
                "未展开异步委托的外层完成边界",
                node,
                method,
                conditions,
                background,
            )
            return UNKNOWN
    else:
        target = method_group(estimator.index, node, method)
        if target is None or estimator.index.polymorphic(node, method, target):
            estimator.record(
                "unresolved", "委托方法或实际实例类型未绑定", node, method, conditions, background
            )
            return UNKNOWN
        cost = estimator.invoke(
            target,
            [],
            method,
            node,
            bindings,
            stack,
            conditions,
            background,
            receiver_id=bound.receiver_id,
        )
        if simple_type(text(target.node.child_by_field_name("returns"))) == "Task":
            estimator.record(
                "unresolved", "委托返回任务的完成边界未绑定", node, method, conditions, background
            )
            cost = Cost(cost.lower, None) if join_result else UNKNOWN
    if any(
        stage["kind"] in {"motion", "wait", "call", "unresolved"} and not stage.get("resolved")
        for stage in estimator.stages[start:]
    ):
        cost = Cost(cost.lower, None)
    return cost


def returned_task(body, method, bindings, cost, started):
    from app.modules.action_timing.source_tasks import lookup

    if body is None:
        return cost
    expression = body
    if body.type == "block":
        returns = [part for part in walk(body) if part.type == "return_statement"]
        if not returns:
            return cost
        if len(returns) != 1 or children(body)[-1] != returns[0]:
            return Cost(cost.lower, None)
        expression = next(iter(children(returns[0])), None)
    plan = lookup(expression, method, bindings)
    if plan is None:
        return cost
    return cost.plus(plan.remaining(started.plus(cost)))


def capture(index, node, method, bindings):
    node = unwrap(index, node, method, bindings)
    if isinstance(node, BoundDelegate):
        return node if node.method_key == method.key else None
    if node is None:
        return None
    if node.type in {"lambda_expression", "anonymous_method_expression"}:
        return BoundDelegate(node, method.key)
    target = method_group(index, node, method)
    if target is None:
        return None
    receiver = state.receiver_for(index, target, node, method, bindings)
    return BoundDelegate(node, method.key, receiver)
