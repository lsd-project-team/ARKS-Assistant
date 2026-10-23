"""按消费规则执行查询；短路出口保留各自的结果、状态和耗时。"""

from dataclasses import replace

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_collection_types import linq, parts
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Flow
from app.modules.action_timing.source_index import text
from app.modules.action_timing.source_queries import QueryExecution, sequence

NAMES = {"Count", "LongCount", "Any", "All", "First", "FirstOrDefault", "Last", "LastOrDefault"}


def default_element(kind):
    return (
        False
        if kind in {"bool", "System.Boolean"}
        else (
            0
            if kind in {"int", "long", "short", "byte", "uint", "ulong", "ushort", "sbyte"}
            else 0.0
            if kind in {"double", "float", "decimal"}
            else None
        )
    )


class ConsumerExecution(QueryExecution):
    def __init__(self, *args, name, predicate=None):
        super().__init__(*args)
        self.operation, self.predicate = name, predicate
        self.kind = "LINQ." + name + "输入"
        self.result_key = arguments.return_key(self.node, self.method, self.bindings)
        self.found_key = self.result_key + ":found"
        self.bindings[self.found_key] = False
        self.bindings[self.result_key] = (
            0
            if name in {"Count", "LongCount"}
            else name == "All"
            if name in {"Any", "All"}
            else default_element(self.query.element_type)
        )

    def stop(self, value):
        self.bindings[self.result_key] = value
        return Flow(None, broken=ZERO).with_state("broken", self.bindings)

    def projected(self, value, conditions):
        self.bindings[self.found_key] = True
        if self.operation in {"Count", "LongCount"}:
            count = self.bindings.get(self.result_key)
            self.bindings[self.result_key] = count + 1 if isinstance(count, int) else None
            return Flow()
        if self.operation == "Any":
            return self.stop(True)
        if self.operation == "All":
            return self.all_item(value, conditions)
        self.bindings[self.result_key] = value
        return self.stop(value) if self.operation.startswith("First") else Flow()

    def all_item(self, value, conditions):
        cost = delegates.execute(
            self.estimator,
            self.predicate,
            self.method,
            self.bindings,
            self.stack,
            conditions,
            self.background,
            join_result=False,
            argument_values=(value,),
            argument_types=(self.query.element_type,),
            bounded_iteration=True,
        )
        if self.bindings.get(delegates.COMPLETION) is False:
            return Flow(None, None)
        decision = self.bindings.get(delegates.RESULT)
        if decision is True:
            return Flow(cost)
        if decision is False:
            return self.stop(False).prefix(cost)
        # 未知谓词可能返回false并短路，也可能继续；不能让退出分支污染继续状态。
        continuing = dict(self.bindings)
        failed = self.stop(False)
        self.bindings.clear()
        self.bindings.update(continuing)
        return Flow().merge(failed).prefix(cost)

    def complete_sequence(self):
        if not self.completed:
            # 未展开的回调可能产出元素；不能把未访问projected误算成0项或空结果。
            self.bindings[self.result_key] = None
            self.bindings[self.found_key] = None
        if self.operation in {"First", "Last"} and self.bindings.get(self.found_key) is False:
            self.failed(self.operation + "没有匹配元素，不能正常返回")
            return
        super().complete_sequence()


def inputs(index, node, method, bindings):
    receiver, _, _ = parts(node)
    nodes = arguments.arguments(node)
    static = text(receiver) in {"Enumerable", "System.Linq.Enumerable"}
    parameters = (
        [("source", "IEnumerable", None), ("predicate", "Func", None)]
        if static
        else [("predicate", "Func", None)]
    )
    slots = arguments.plan(parameters[: len(nodes)], nodes)
    if slots is None or len(nodes) not in ({1, 2} if static else {0, 1}):
        return None
    ordered = {
        slot: (part, value)
        for slot, part, value in zip(
            slots, nodes, arguments.values(index, node, method, bindings), strict=True
        )
    }
    saved = arguments.snapshot(node, method, bindings)
    data = (
        ordered[0][1]
        if static
        else (
            saved.receiver_value if saved is not None else index.value(receiver, method, bindings)
        )
    )
    source = ordered[0][0] if static else receiver
    predicate = ordered.get(1 if static else 0, (None, None))[0]
    return data, source, predicate


def handle(estimator, node, method, bindings, stack, conditions, background):
    index = estimator.index
    _, name, _ = parts(node)
    if name not in NAMES or not linq(index, node, method):
        return None
    parsed = inputs(index, node, method, bindings)
    if parsed is None:
        return None
    data, source, predicate_node = parsed
    result_key = arguments.return_key(node, method, bindings)
    predicate = (
        delegates.capture(index, predicate_node, method, bindings, arity=1, returns_task=False)
        if predicate_node is not None
        else None
    )
    if (name == "All" and predicate_node is None) or (
        predicate_node is not None
        and (not isinstance(predicate, delegates.BoundDelegate) or predicate.arity != 1)
    ):
        estimator.record(
            "unresolved", name + "的谓词未绑定或为空", node, method, conditions, background
        )
        bindings[result_key] = None
        if predicate is delegates.NULL_DELEGATE:
            bindings[result_key + ":normal"] = False
        return UNKNOWN
    size = collections.length(data, bindings)
    if name in {"Count", "LongCount"} and predicate_node is None and size is not None:
        bindings[result_key] = size
        return ZERO
    query = sequence(index, data, source, method)
    if predicate_node is not None and name != "All":
        query = replace(
            query,
            steps=(*query.steps, ("Where", predicate, query.element_type, query.element_type)),
        )
    execution = ConsumerExecution(
        estimator,
        node,
        method,
        bindings,
        stack,
        conditions,
        background,
        query,
        name=name,
        predicate=predicate,
    )
    flow = execution.run()
    bindings[result_key + ":normal"] = flow.live is not None
    return flow.cost()
