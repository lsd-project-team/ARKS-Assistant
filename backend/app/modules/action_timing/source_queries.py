"""保存惰性查询，物化时逐项执行筛选和投影；不运行目标枚举器。"""

from dataclasses import dataclass, replace

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_closures as closures
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_collection_types import framework_type, linq, parts
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Flow, choice
from app.modules.action_timing.source_index import text, walk
from app.modules.action_timing.source_loops import (
    MAX_ACTION_ITERATIONS,
    MAX_ITERATIONS,
    ForExecution,
)
from app.modules.action_timing.source_tasks import CLOCK


@dataclass(frozen=True)
class Query:
    source: object
    element_type: str
    steps: tuple
    trusted_source: bool


def selected_type(index, callback, method, input_type):
    """以输入类型推断投影返回类型，不求值lambda正文。"""
    if callback is None or callback is delegates.NULL_DELEGATE:
        return "var"
    if isinstance(callback, delegates.BoundDelegate):
        method, callback = callback.closure.method, callback.node
    if callback.type not in {"lambda_expression", "anonymous_method_expression"}:
        target = delegates.method_group(index, callback, method, arity=1)
        return target.return_type if target else "var"
    parameters = closures.parameters(callback)
    if len(parameters) != 1:
        return "var"
    name, kind, _ = parameters[0]
    kind = input_type if kind == "var" else kind
    # 推断使用lambda自己的词法边界，避免把参数追溯为外层查询的初值，
    # 也避免重复追加上下文绕过SourceIndex的递归保护。
    context = replace(
        method,
        name=f"<query-type:{callback.start_byte}>",
        node=callback,
        callable_kind="delegate",
        parameters=[(name, kind, None)],
        types={**method.types, name: kind},
        type_scope=(*method.type_scope, (callback.start_byte, input_type)),
    )
    body = callback.child_by_field_name("body")
    if body is not None and body.type == "block":
        returns = [part for part in walk(body) if part.type == "return_statement"]
        from app.modules.action_timing.source_index import value_children

        values = [value_children(part) for part in returns]
        kinds = {index.infer(parts[-1], context) for parts in values if parts}
        return kinds.pop() if len(kinds) == 1 else "var"
    return index.infer(body, context) or "var"


def handle(estimator, node, method, bindings, stack, conditions, background):
    index = estimator.index
    receiver, name, _ = parts(node)
    if name not in {"Where", "Select"} or not linq(index, node, method):
        return None
    nodes = arguments.arguments(node)
    static = text(receiver) in {"Enumerable", "System.Linq.Enumerable"}
    if len(nodes) != (2 if static else 1):
        return None
    saved = arguments.snapshot(node, method, bindings)
    data = (
        arguments.values(index, node, method, bindings)[0]
        if static
        else (
            saved.receiver_value if saved is not None else index.value(receiver, method, bindings)
        )
    )
    source_node = nodes[0] if static else receiver
    source_kind = collections.raw_type(index, source_node, method)
    input_type = (
        data.element_type
        if isinstance(data, Query)
        else (
            data.get("<element_type>", "var")
            if collections.known(data)
            else collections.element_type(index, source_node, method)
        )
    )
    callback = delegates.capture(index, nodes[-1], method, bindings, arity=1, returns_task=False)
    output_type = (
        selected_type(index, callback, method, input_type) if name == "Select" else input_type
    )
    step = (name, callback, input_type, output_type)
    if isinstance(data, Query):
        result = replace(data, element_type=output_type, steps=(*data.steps, step))
    else:
        trusted = (
            collections.known(data)
            or source_kind.endswith("[]")
            or framework_type(index, source_kind, method, "List", "System.Collections.Generic")
        )
        result = Query(data, output_type, (step,), trusted)
    bindings[arguments.return_key(node, method, bindings)] = result
    return ZERO


class QueryExecution(ForExecution):
    def __init__(self, estimator, node, method, bindings, stack, conditions, background, query):
        super().__init__(estimator, node, method, bindings, stack, conditions, background)
        self.query, self.value = query, None
        self.values, self.uncertain, self.completed = [], False, True
        self.selected, self.output = None, None
        self.kind = "LINQ物化"

    def apply(self, position, value, conditions):
        if position >= len(self.query.steps):
            return ZERO, True, value
        name, callback, input_type, _ = self.query.steps[position]
        if not isinstance(callback, delegates.BoundDelegate) or callback.arity != 1:
            from app.modules.action_timing.source_parallel import invalidate_unexplored

            invalidate_unexplored(self.bindings)
            self.completed = False
            return UNKNOWN, None, None
        started = self.bindings.get(CLOCK, ZERO)
        cost = delegates.execute(
            self.estimator,
            callback,
            self.method,
            self.bindings,
            self.stack,
            (*conditions, name),
            self.background,
            join_result=False,
            argument_values=(value,),
            argument_types=(input_type,),
            bounded_iteration=True,
        )
        result = self.bindings.get(delegates.RESULT)
        if self.bindings.get(delegates.COMPLETION) is not True:
            self.completed = False
        self.bindings[CLOCK] = started.plus(cost)
        if name == "Where" and result is False:
            return cost, False, None
        maybe = name == "Where" and result is not True
        skipped = dict(self.bindings) if maybe else None
        tail, selected, output = self.apply(
            position + 1,
            result if name == "Select" else value,
            (*conditions, "筛选结果未定") if maybe else conditions,
        )
        if maybe:
            state.merge(self.bindings, [skipped, dict(self.bindings)])
            return cost.plus(choice(ZERO, tail)), False if selected is False else None, output
        return cost.plus(tail), selected, output

    def body_flow(self, suffix):
        self.bindings[CLOCK] = self.started.plus(self.elapsed)
        cost, self.selected, self.output = self.apply(0, self.value, (*self.conditions, suffix))
        return Flow(cost)

    def execute(self):
        data = self.query.source
        if not self.query.trusted_source:
            from app.modules.action_timing.source_eager_collections import invalidate_enumeration

            invalidate_enumeration(self.estimator.index, self.method, data, self.bindings)
            self.elapsed = UNKNOWN
        size, version = (
            collections.length(data, self.bindings),
            collections.version(data, self.bindings),
        )
        if size is None:
            self.uncertain = True
            self.summarize("源集合数量未定，回调写入按未知次数合并")
        else:
            for position in range(size):
                current = collections.version(data, self.bindings)
                if current != version:
                    self.uncertain = True
                    self.estimator.record(
                        "unresolved",
                        "查询枚举期间源集合发生变化",
                        self.node,
                        self.method,
                        self.conditions,
                        self.background,
                    )
                    self.exit(self.elapsed.plus(UNKNOWN), self.bindings)
                    break
                if (
                    self.count >= MAX_ITERATIONS
                    or self.estimator.loop_steps >= MAX_ACTION_ITERATIONS
                ):
                    self.estimator.truncated = True
                    self.uncertain, self.value = True, None
                    self.summarize("达到查询展开边界")
                    break
                self.value = collections.item(data, position, self.bindings)
                if not self.run_body():
                    self.uncertain = True
                    break
                if self.selected is True:
                    self.values.append(self.output)
                elif self.selected is not False:
                    self.uncertain = True
            else:
                if collections.version(data, self.bindings) != version:
                    self.uncertain = True
                    self.exit(self.elapsed.plus(UNKNOWN), self.bindings)
                else:
                    self.bounded = True
                    self.exit(self.elapsed, self.bindings)
        flow = self.finish()
        values = None if self.uncertain or not self.completed else self.values
        return flow.cost(), values
