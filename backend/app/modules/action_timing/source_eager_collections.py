"""即时筛选与物化；保留回调成本、独立列表存储和共享元素引用。"""

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_collection_types import (
    control_result,
    framework_type,
    linq,
    parts,
)
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Flow
from app.modules.action_timing.source_index import text
from app.modules.action_timing.source_loops import (
    MAX_ITERATIONS,
    ForExecution,
)
from app.modules.action_timing.source_tasks import CLOCK

MAX_COPY_ITEMS = 4096


def invalidate_enumeration(index, method, data, bindings):
    """未知枚举器可影响其接收者图；不清空其他调用帧的局部参数与对象。"""
    from app.modules.action_timing.source_references import invalidate_values, self_value

    invalidate_values((data, self_value(index, method, bindings)), bindings)


def new_list(estimator, kind, values=None):
    estimator.allocations += 1
    return {
        "<collection>": "list",
        "<type>": f"System.Collections.Generic.List<{kind}>",
        "<element_type>": kind,
        "<ref>": f"list-copy:{estimator.allocations}",
        "<items>": tuple(values) if values is not None else None,
        "<length>": len(values) if values is not None else None,
    }


class FilterExecution(ForExecution):
    def __init__(
        self, estimator, node, method, bindings, stack, conditions, background, data, callback, kind
    ):
        super().__init__(estimator, node, method, bindings, stack, conditions, background)
        self.data, self.callback, self.element_type = data, callback, kind
        self.value, self.match = None, None
        self.values, self.uncertain = [], False
        self.kind = "List.FindAll"
        self.condition = node.child_by_field_name("function").child_by_field_name("expression")

    def body_flow(self, suffix):
        self.bindings[CLOCK] = self.started.plus(self.elapsed)
        cost = delegates.execute(
            self.estimator,
            self.callback,
            self.method,
            self.bindings,
            self.stack,
            (*self.conditions, suffix),
            self.background,
            join_result=False,
            argument_values=(self.value,),
            argument_types=(self.element_type,),
        )
        self.match = self.bindings.get(delegates.RESULT)
        if self.bindings.get(delegates.COMPLETION) is False:
            return Flow(None, None)
        return Flow(cost)

    def execute(self):
        position = 0
        while True:
            # FindAll与ForEach不同：条件读取当前_size，不使用版本快照抛异常。
            size = collections.length(self.data, self.bindings)
            if size is not None and position >= size:
                self.exit(self.elapsed, self.bindings)
                self.bounded = True
                break
            if size is None or self.count >= MAX_ITERATIONS or self.estimator.loop_limit_reached():
                if size is not None:
                    self.estimator.truncated = True
                self.value, self.uncertain = None, True
                self.summarize("输入数量或剩余筛选次数未定")
                break
            self.value = collections.item(self.data, position, self.bindings)
            if not self.run_body():
                self.uncertain = True
                self.estimator.record(
                    "unresolved",
                    "FindAll筛选回调没有正常完成路径",
                    self.node,
                    self.method,
                    self.conditions,
                    self.background,
                )
                self.result.live = self.elapsed.plus(UNKNOWN)
                break
            if self.match is True:
                # 参考实现是在match之后再次读取_items[i]，不能冻结成旧实参。
                self.values.append(collections.item(self.data, position, self.bindings))
            elif self.match is not False:
                self.uncertain = True
            position += 1
        flow = self.finish()
        return flow.cost(), new_list(
            self.estimator, self.element_type, None if self.uncertain else self.values
        )


def handle(estimator, node, method, bindings, stack, conditions, background):
    index = estimator.index
    receiver, name, _ = parts(node)
    if name not in {"FindAll", "ToList", "ToArray", "GetChildControls"} or index.has_source_call(
        node, method
    ):
        return None
    saved = arguments.snapshot(node, method, bindings)
    nodes = arguments.arguments(node)
    data = saved.receiver_value if saved is not None else index.value(receiver, method, bindings)
    result_key = arguments.return_key(node, method, bindings)
    control = control_result(index, node, method)
    if control:
        from app.modules.action_timing.source_array_values import element
        from app.modules.action_timing.source_references import invalidate_values

        invalidate_values((data, *arguments.values(index, node, method, bindings)), bindings)
        bindings[result_key] = new_list(estimator, element(control))
        estimator.record(
            "call",
            "控件集合内容与查询耗时未定",
            node,
            method,
            conditions,
            background,
            note="已核实同版本包的List返回类型；控件数量及运行时实现不补为固定数值",
        )
        return UNKNOWN
    if name in {"ToList", "ToArray"} and linq(index, node, method):
        from app.modules.action_timing.source_queries import Query, QueryExecution

        static = text(receiver) in {"Enumerable", "System.Linq.Enumerable"}
        valid = (
            len(nodes) == 1 and arguments.argument_name(nodes[0]) in {None, "source"}
            if static
            else not nodes
        )
        if static and valid:
            data = arguments.values(index, node, method, bindings)[0]
        if valid and isinstance(data, Query):
            execution = QueryExecution(
                estimator, node, method, bindings, stack, conditions, background, data
            )
            cost, values = execution.execute()
            bindings[result_key + ":normal"] = execution.result.live is not None
            result = new_list(estimator, data.element_type, values)
            if name == "ToArray":
                result.update(
                    {
                        "<collection>": "array",
                        "<type>": data.element_type + "[]",
                        "<shape>": (result["<length>"],),
                    }
                )
            bindings[result_key] = result
            return cost
        # List<T>.ToArray已有独立存储及维度处理；非查询接收者沿原实现。
        if name == "ToArray":
            return None
        size = collections.length(data, bindings)
        kind = (
            data.get("<element_type>", "var")
            if collections.known(data)
            else collections.element_type(index, nodes[0] if static and nodes else receiver, method)
        )
        if valid and size is not None and size <= MAX_COPY_ITEMS:
            bindings[result_key] = new_list(
                estimator, kind, [collections.item(data, i, bindings) for i in range(size)]
            )
            return ZERO
        bindings[result_key] = new_list(estimator, kind)
        source_node = nodes[0] if static and nodes else receiver
        source_kind = collections.raw_type(index, source_node, method)
        trusted = source_kind.endswith("[]") or framework_type(
            index, source_kind, method, "List", "System.Collections.Generic"
        )
        if not collections.known(data) and not trusted:
            invalidate_enumeration(index, method, data, bindings)
        estimator.record(
            "unresolved", "ToList输入枚举或复制内容未定", node, method, conditions, background
        )
        return UNKNOWN
    kind = collections.raw_type(index, receiver, method)
    if name != "FindAll" or not framework_type(
        index, kind, method, "List", "System.Collections.Generic"
    ):
        return None
    callback = (
        delegates.capture(index, nodes[0], method, bindings, arity=1, returns_task=False)
        if len(nodes) == 1 and arguments.argument_name(nodes[0]) in {None, "match"}
        else None
    )
    if not isinstance(callback, delegates.BoundDelegate) or callback.arity != 1:
        if collections.length(data, bindings) != 0:
            from app.modules.action_timing.source_parallel import invalidate_unexplored

            invalidate_unexplored(bindings)
        estimator.record(
            "unresolved", "FindAll的筛选回调未绑定或为空", node, method, conditions, background
        )
        bindings[result_key] = None
        return UNKNOWN
    element = (
        data.get("<element_type>")
        if collections.known(data)
        else collections.element_type(index, receiver, method)
    )
    cost, result = FilterExecution(
        estimator, node, method, bindings, stack, conditions, background, data, callback, element
    ).execute()
    bindings[result_key] = result
    return cost
