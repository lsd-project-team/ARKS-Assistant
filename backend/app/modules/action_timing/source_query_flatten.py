"""惰性SelectMany：每个外层项只取一次集合，再逐项执行结果投影与后续消费。"""

from dataclasses import dataclass, replace

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_array_values import element
from app.modules.action_timing.source_collection_types import framework_type, linq, parts
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Flow
from app.modules.action_timing.source_index import text, value_children
from app.modules.action_timing.source_queries import Query, QueryExecution, selected_type, sequence
from app.modules.action_timing.source_tasks import CLOCK

STOP = "<select-many-stop>"


@dataclass(frozen=True)
class Selectors:
    collection: object
    result: object
    has_result: bool
    inner_kind: str
    inner_type: str


def inputs(node):
    receiver, _, _ = parts(node)
    nodes = arguments.arguments(node)
    static = text(receiver) in {"Enumerable", "System.Linq.Enumerable"}
    count = len(nodes) - int(static)
    if count not in {1, 2}:
        return None
    names = (["source"] if static else []) + (
        ["selector"] if count == 1 else ["collectionSelector", "resultSelector"]
    )
    slots = arguments.plan([(name, "Func", None) for name in names], nodes)
    if slots is None:
        return None
    ordered = {slot: part for slot, part in zip(slots, nodes, strict=True)}
    start = int(static)
    return (
        receiver,
        nodes,
        slots,
        static,
        ordered[0] if static else receiver,
        ordered[start],
        ordered.get(start + 1),
    )


def types(index, selector, result, method, input_type, has_result=False):
    inner_kind = selected_type(index, selector, method, input_type)
    inner_type = element(inner_kind)
    output = (
        selected_type(index, result, method, input_type, inner_type) if has_result else inner_type
    )
    return inner_kind, inner_type, output


def result_type(index, node, method, seen):
    parsed = inputs(node)
    if parsed is None:
        return "var"
    _, _, _, _, source, selector, result = parsed
    selector = next(reversed(value_children(selector)), None)
    result = next(reversed(value_children(result)), None) if result is not None else None
    input_type = element(collections.raw_type(index, source, method, seen))
    return types(index, selector, result, method, input_type, result is not None)[-1]


def handle(estimator, node, method, bindings, stack, conditions, background):
    index = estimator.index
    parsed = inputs(node)
    if parsed is None or not linq(index, node, method):
        return None
    receiver, nodes, slots, static, source, selector, result = parsed
    saved = arguments.snapshot(node, method, bindings)
    values = arguments.values(index, node, method, bindings)
    data = (
        dict(zip(slots, values, strict=True))[0]
        if static
        else (
            saved.receiver_value if saved is not None else index.value(receiver, method, bindings)
        )
    )
    query = sequence(index, data, source, method)
    has_result = result is not None
    selector = delegates.capture(index, selector, method, bindings, arity=1, returns_task=False)
    result = (
        delegates.capture(index, result, method, bindings, arity=2, returns_task=False)
        if result is not None
        else None
    )
    key = arguments.return_key(node, method, bindings)
    if selector is delegates.NULL_DELEGATE or result is delegates.NULL_DELEGATE:
        estimator.record(
            "unresolved", "SelectMany回调为空，不能正常返回", node, method, conditions, background
        )
        bindings[key], bindings[key + ":normal"] = None, False
        return UNKNOWN
    inner_kind, inner_type, output = types(
        index, selector, result, method, query.element_type, has_result
    )
    step = (
        "SelectMany",
        Selectors(selector, result, has_result, inner_kind, inner_type),
        query.element_type,
        output,
    )
    bindings[key] = replace(query, element_type=output, steps=(*query.steps, step))
    return ZERO


def invoke(owner, callback, values, kinds, conditions):
    if not isinstance(callback, delegates.BoundDelegate) or callback.arity != len(values):
        from app.modules.action_timing.source_parallel import invalidate_unexplored

        invalidate_unexplored(owner.bindings)
        owner.completed = False
        return UNKNOWN, None, None
    cost = delegates.execute(
        owner.estimator,
        callback,
        owner.method,
        owner.bindings,
        owner.stack,
        conditions,
        owner.background,
        join_result=False,
        argument_values=values,
        argument_types=kinds,
        bounded_iteration=True,
    )
    normal = owner.bindings.get(delegates.COMPLETION)
    if normal is not True:
        owner.completed = False
    return cost, owner.bindings.get(delegates.RESULT), normal


def null_collection(index, selector):
    from app.modules.action_timing.source_local_functions import lexical_walk

    body = selector.node.child_by_field_name("body")
    if body is None:
        target = delegates.method_group(index, selector.node, selector.closure.method, arity=1)
        body = target.body if target else None
    values = (
        [
            value_children(part)[-1]
            for part in lexical_walk(body)
            if part.type == "return_statement" and value_children(part)
        ]
        if body is not None and body.type == "block"
        else [body]
    )

    def literal_null(node):
        while node is not None and node.type in {"parenthesized_expression", "cast_expression"}:
            node = next(reversed(value_children(node)), None)
        return node is not None and node.type == "null_literal"

    return bool(values) and all(literal_null(value) for value in values)


class InnerExecution(QueryExecution):
    def __init__(self, owner, position, outer, input_type, selectors, query, conditions):
        super().__init__(
            owner.estimator,
            owner.node,
            owner.method,
            owner.bindings,
            owner.stack,
            conditions,
            owner.background,
            query,
        )
        self.owner, self.position, self.outer = owner, position, outer
        self.input_type, self.selectors = input_type, selectors
        self.kind = "SelectMany内层输入"

    def projected(self, value, conditions):
        cost = ZERO
        if self.selectors.has_result:
            started = self.bindings.get(CLOCK, ZERO)
            cost, value, normal = invoke(
                self,
                self.selectors.result,
                (self.outer, value),
                (self.input_type, self.query.element_type),
                conditions,
            )
            if normal is not True:
                return Flow(None, None) if normal is False else Flow(UNKNOWN)
            self.bindings[CLOCK] = started.plus(cost)
        flow = self.owner.apply(self.position + 1, value, conditions).prefix(cost)
        if flow.broken is None:
            return flow
        stopped = Flow(None, None, jumps={STOP: flow.broken}).with_state(
            STOP, flow.states.get("broken", self.bindings)
        )
        return replace(
            flow, broken=None, states={k: v for k, v in flow.states.items() if k != "broken"}
        ).merge(stopped)


def apply(owner, position, value, conditions):
    _, selectors, input_type, _ = owner.query.steps[position]
    started = owner.bindings.get(CLOCK, ZERO)
    cost, data, normal = invoke(
        owner, selectors.collection, (value,), (input_type,), (*conditions, "SelectMany")
    )
    if normal is not True:
        return Flow(None, None) if normal is False else Flow(UNKNOWN)
    if data is None and null_collection(owner.estimator.index, selectors.collection):
        owner.completed = False
        owner.estimator.record(
            "unresolved",
            "SelectMany内层集合为空引用，不能枚举",
            owner.node,
            owner.method,
            conditions,
            owner.background,
        )
        return Flow(None, None)
    owner.bindings[CLOCK] = started.plus(cost)
    if isinstance(data, Query):
        query = data
    else:
        trusted = (
            collections.known(data)
            or selectors.inner_kind.endswith("]")
            or framework_type(
                owner.estimator.index,
                selectors.inner_kind,
                owner.method,
                "List",
                "System.Collections.Generic",
            )
        )
        item_type = (
            data.get("<element_type>", selectors.inner_type)
            if collections.known(data)
            else selectors.inner_type
        )
        query = Query(data, item_type, (), trusted)
    inner = InnerExecution(owner, position, value, input_type, selectors, query, conditions)
    flow = inner.run()
    owner.uncertain |= inner.uncertain
    owner.completed &= inner.completed
    if STOP in flow.jumps:
        stopped = Flow(None, None, broken=flow.jumps[STOP]).with_state(
            "broken", flow.states.get(STOP, owner.bindings)
        )
        flow = replace(
            flow,
            jumps={k: v for k, v in flow.jumps.items() if k != STOP},
            states={k: v for k, v in flow.states.items() if k != STOP},
        ).merge(stopped)
    return flow.prefix(cost)
