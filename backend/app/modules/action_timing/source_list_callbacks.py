"""List.ForEach逐项顺序调用；未知数量只保留每项依据，不冒充执行了一项。"""

from dataclasses import replace

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_flow import UNKNOWN, Flow, choice
from app.modules.action_timing.source_index import text
from app.modules.action_timing.source_loops import (
    MAX_ACTION_ITERATIONS,
    MAX_ITERATIONS,
    ForExecution,
)
from app.modules.action_timing.source_tasks import CLOCK


def operation(index, node, method):
    function = node.child_by_field_name("function")
    if text(function.child_by_field_name("name")) != "ForEach" or index.has_source_call(
        node, method
    ):
        return False
    receiver = function.child_by_field_name("expression")
    kind = collections.raw_type(index, receiver, method)
    return (
        kind.split("<", 1)[0].split(".")[-1] == "List"
        and index.lookup_type(kind, method) not in index.classes
        and (
            kind.startswith("System.Collections.Generic.List<")
            or "System.Collections.Generic" in method.unit.namespaces
        )
    )


class ListExecution(ForExecution):
    def __init__(
        self, estimator, node, method, bindings, stack, conditions, background, data, bound, kind
    ):
        super().__init__(estimator, node, method, bindings, stack, conditions, background)
        self.data, self.bound, self.element_type = data, bound, kind
        self.kind = "List.ForEach"
        self.condition = node.child_by_field_name("function").child_by_field_name("expression")
        self.value = None

    def body_flow(self, suffix):
        self.bindings[CLOCK] = self.started.plus(self.elapsed)
        cost = delegates.execute(
            self.estimator,
            self.bound,
            self.method,
            self.bindings,
            self.stack,
            (*self.conditions, suffix),
            self.background,
            join_result=False,
            argument_values=(self.value,),
            argument_types=(self.element_type,),
        )
        # 回调中的return只结束本项；异常不能继续执行下一项。
        if self.bindings.get(delegates.COMPLETION) is False:
            return Flow(None, None)
        return Flow(cost)

    def unresolved(self, reason):
        self.estimator.record(
            "unresolved", reason, self.node, self.method, self.conditions, self.background
        )
        self.bindings[arguments.return_key(self.node, self.method, self.bindings) + ":normal"] = (
            False
        )
        self.result.live = self.elapsed.plus(UNKNOWN)
        self.bounded = True

    def execute(self):
        size = collections.length(self.data, self.bindings)
        version = collections.version(self.data, self.bindings)
        if size is None:
            self.summarize("集合数量未知；每项顺序执行，不按一项计入总耗时")
        else:
            for position in range(size):
                current = collections.version(self.data, self.bindings)
                if current != version and current is not None:
                    self.unresolved("List.ForEach执行期间集合被修改，不能正常完成")
                    break
                if (
                    current is None
                    or self.count >= MAX_ITERATIONS
                    or self.estimator.loop_steps >= MAX_ACTION_ITERATIONS
                ):
                    self.estimator.truncated = True
                    self.value = None
                    self.summarize("集合状态或剩余项数未定，或达到展开边界")
                    break
                self.value = collections.item(self.data, position, self.bindings)
                self.estimator.loop_steps += 1
                flow = self.body_flow(f"List.ForEach第{position + 1}项")
                self.count += 1
                self.each = choice(self.each, flow.cost())
                if flow.live is None:
                    self.unresolved("List.ForEach回调没有正常完成路径")
                    break
                self.elapsed = self.elapsed.plus(flow.live)
            else:
                # .NET List.ForEach在最后一项之后仍检查版本，单项集合也不能漏掉。
                if collections.version(self.data, self.bindings) != version:
                    self.unresolved("List.ForEach执行期间集合被修改，不能正常完成")
                else:
                    self.exit(self.elapsed, self.bindings)
                    self.bounded = True
        start = len(self.estimator.stages)
        result = self.finish()
        for loop in self.estimator.stages[start:]:
            if loop["kind"] != "loop":
                continue
            loop.update(element_type=self.element_type, collection_callback=True)
        return result.cost()


def handle(estimator, node, method, bindings, stack, conditions, background):
    if not operation(estimator.index, node, method):
        return None
    nodes = arguments.arguments(node)
    saved = arguments.snapshot(node, method, bindings)
    receiver = node.child_by_field_name("function").child_by_field_name("expression")
    data = (
        saved.receiver_value
        if saved is not None
        else estimator.index.value(receiver, method, bindings)
    )
    bound = (
        delegates.capture(
            estimator.index,
            nodes[0],
            method,
            bindings,
            arity=1,
            returns_task=False,
            discards_result=True,
        )
        if len(nodes) == 1 and arguments.argument_name(nodes[0]) in {None, "action"}
        else None
    )
    if not isinstance(bound, delegates.BoundDelegate) or bound.arity != 1:
        if collections.length(data, bindings) != 0:
            from app.modules.action_timing.source_parallel import invalidate_unexplored

            invalidate_unexplored(bindings)
        estimator.record(
            "unresolved", "List.ForEach的回调未绑定或为空", node, method, conditions, background
        )
        return UNKNOWN
    # 委托作为Action<T>使用。async lambda在首个未完成await后继续在后台执行。
    bound = replace(
        bound,
        returns_task=False,
        discards_result=True,
        async_void=bound.async_void
        or (
            bound.node.type in {"lambda_expression", "anonymous_method_expression"}
            and any(text(part) == "async" for part in bound.node.children)
        ),
    )
    kind = (
        data.get("<element_type>", "")
        if collections.known(data)
        else collections.element_type(estimator.index, receiver, method)
    )
    return ListExecution(
        estimator, node, method, bindings, stack, conditions, background, data, bound, kind
    ).execute()


def per_item_timing(stages):
    """摘要只携带未知数量的逐项耗时；不把单项样本计入动作总和。"""
    result = []
    for row in stages:
        if (
            row["kind"] == "loop"
            and row.get("collection_callback")
            and row.get("iterations") is None
            and row.get("expanded_iterations") == 0
            and not row["background"]
            and row.get("per_iteration_min_ms", 0) > 0
        ):
            item = {
                "element_type": row["element_type"],
                "min_ms": row["per_iteration_min_ms"],
                "max_ms": row.get("per_iteration_max_ms"),
            }
            if item not in result:
                result.append(item)
    return {"per_item_timing": result} if result else {}
