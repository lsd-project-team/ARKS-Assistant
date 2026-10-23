"""按源码分支合并配置延时；运动、信号和超时保持各自的物理含义。"""

import math
import re

from app.modules.action_timing import (
    source_apm,
    source_dispatch,
    source_dynamic,
    source_finally,
    source_list_callbacks,
    source_parallel,
)
from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing import source_jumps as jumps
from app.modules.action_timing import source_state as state
from app.modules.action_timing import source_task_returns as task_returns
from app.modules.action_timing.source_condition_loops import execute_condition_loop
from app.modules.action_timing.source_construction import constructor_body, create_object
from app.modules.action_timing.source_delay_reachability import possible as delay_possible
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost, Flow, choice
from app.modules.action_timing.source_foreach import execute_foreach
from app.modules.action_timing.source_hardware import hardware_call
from app.modules.action_timing.source_index import (
    children,
    initializer,
    simple_type,
    text,
    value_children,
    walk,
)
from app.modules.action_timing.source_loops import execute_for
from app.modules.action_timing.source_numbers import binary_value
from app.modules.action_timing.source_properties import (
    assign_property,
    increment_property,
    read_property,
)
from app.modules.action_timing.source_scopes import declarations, local_scope, restore
from app.modules.action_timing.source_tasks import CLOCK, handle_tasks, track_binding

PURE_NAMES = {
    "GetInstance",
    "RecordTime",
    "Post",
    "WriteLine",
    "Refresh",
    "SetCurrentThreadName",
    "ToString",
    "RefreshMap",
    "S1FinishedStep",
    "S2FinishedStep",
    "ReFreshSystem1TuAction",
    "ReFreshSystem2TuAction",
    "RefreshDispenseStatistics",
    "RefreshBondStatistics",
    "Dispose",
}
MOTION = re.compile(
    r"(?:Move|Interpolation|SearchBelt|MapBelt|HomeWait|GoHome|WaitAxesArrival|WaitAxisArrival|WaitArrive)",
    re.I,
)
COLLECTION_OPERATIONS = {"Remove", "RemoveAt", "RemoveAll", "RemoveRange", "MoveNext"}
WAIT = re.compile(r"^(?:Wait|SpinUntil)|Signal\.(?:Wait|WaitOne)|\.WaitOne$", re.I)


class Estimator:
    def __init__(self, index):
        self.index = index
        self.stages = []
        self.parameters = {}
        self.calls = 0
        self.truncated = False
        self.context = {"MachineStateModel.MachineState": "Working"}
        self.root_method = None
        self.skip_conditions = []
        self.failure_reasons = []
        self.frames = 0
        self.loop_steps = 0
        self.numeric_loop_steps = 0
        self.scope_frames = 0
        self.allocations = 0
        self.jump_steps = 0
        self.apm_calls = 0

    def estimate(self, method):
        if method.unit.tree.root_node.has_error:
            self.truncated = True
        self.root_method = method.key
        bindings = {
            **self.context,
            state.THIS: None if method.is_static else f"root:{method.owner}",
            state.FRAME: "root",
            **{
                name: self.index.value(default, method, self.context)
                for name, _, default in method.parameters
            },
        }
        bindings.update(delegates.bind_arguments(self.index, method, [], method, bindings))
        if method.callable_kind == "constructor" and not method.is_static:
            from app.modules.action_timing.source_multicast import initialize_instance

            initialize_instance(self.index, method.owner, bindings, bindings[state.THIS])
        flow = self.execute_body(method, bindings, (method.key,), (), False)
        cost = flow.cost()
        if task_returns.task_method(self.index, method) and not task_returns.async_method(method):
            from app.modules.action_timing.source_tasks import join_stages, known_task

            plan = flow.states.get("returned", {}).get("<return-value>")
            cost = cost.plus(plan.remaining(cost) if known_task(plan) else UNKNOWN)
            join_stages(self, plan, False)
        has_success_path = any(
            value is not None for value in (flow.live, flow.returned, flow.broken, flow.continued)
        )
        unknown = any(
            (
                (
                    row["kind"] in {"motion", "wait", "call", "unresolved"}
                    and not row.get("resolved", False)
                )
                or (
                    row["kind"] == "loop"
                    and row.get("iterations") is None
                    and not row.get("bounded", False)
                )
            )
            and not row["background"]
            for row in self.stages
        )
        if cost.upper is None:
            formula = (
                f"至少 {cost.lower:g} ms 已知延时 + " if cost.lower else ""
            ) + "未定次数/未解析延时"
        elif cost.lower == cost.upper == 0:
            formula = "未发现显式固定延时"
        elif cost.lower == cost.upper:
            formula = f"{cost.lower:g} ms 已知延时"
        else:
            reason = (
                "并行/分支条件相关"
                if any(row.get("parallel") and not row["background"] for row in self.stages)
                else "分支相关"
            )
            formula = f"{cost.lower:g}–{cost.upper:g} ms 已知延时（{reason}）"
        if unknown:
            formula += " + 运动/信号/未解析调用"
        if not has_success_path:
            formula = "未发现正常完成路径，不推算成功动作耗时"
        return {
            **source_list_callbacks.per_item_timing(self.stages),
            "execution_status": "unavailable"
            if not has_success_path
            else "skipped"
            if self.skip_conditions and not self.stages and cost == ZERO
            else "complete"
            if not unknown and cost.upper is not None and not self.truncated
            else "partial",
            "status_reason": (
                self.failure_reasons[0] if self.failure_reasons else "源码中没有正常完成路径"
            )
            if not has_success_path
            else "空跑分支直接返回，不执行动作"
            if self.skip_conditions and not self.stages and cost == ZERO
            else "",
            "known_delay_min_ms": cost.lower if has_success_path else None,
            "known_delay_max_ms": cost.upper if has_success_path else None,
            "total_ms": cost.lower
            if has_success_path and cost.lower == cost.upper and not unknown and not self.truncated
            else None,
            "formula": formula,
            "complete": has_success_path
            and not unknown
            and cost.upper is not None
            and not self.truncated,
            "truncated": self.truncated,
            "stages": self.stages,
            "parameters": list(self.parameters.values()),
            "motion_count": len(
                {
                    (row["path"], row["line"], row["code"])
                    for row in self.stages
                    if row["kind"] == "motion" and not row["background"]
                }
            ),
            "wait_count": len(
                {
                    (row["path"], row["line"], row["code"])
                    for row in self.stages
                    if row["kind"] == "wait" and not row["background"]
                }
            ),
            "timeout_count": sum(row["kind"] == "timeout" for row in self.stages),
        }

    def record(self, kind, label, node, method, conditions, background, **data):
        if kind == "timeout" and any(
            row["kind"] == kind
            and row["path"] == method.unit.path
            and row["line"] == node.start_point[0] + 1
            for row in self.stages
        ):
            return
        self.stages.append(
            {
                "kind": kind,
                "label": label,
                "conditions": list(conditions),
                "background": background,
                "method": f"{method.owner}.{method.name}",
                **method.unit.evidence(node),
                **data,
            }
        )

    def defaults(self, node, method, bindings):
        from app.modules.action_timing.source_tasks import public_value

        for part in walk(node):
            if part.type != "member_access_expression":
                continue
            owner = self.index.infer(part.child_by_field_name("expression"), method)
            name = text(part.child_by_field_name("name"))
            info = self.index.classes.get(owner)
            if info and name in info.defaults:
                unit, initializer = info.defaults[name]
                self.parameters[(owner, name)] = {
                    "name": f"{owner}.{name}",
                    "value": public_value(self.index.value(part, method, bindings)),
                    "expression": text(initializer),
                    **unit.evidence(initializer),
                }

    def expression(self, node, method, bindings, stack, conditions, background):
        if node is None:
            return ZERO
        if node.type in {"this", "this_expression"}:
            from app.modules.action_timing.source_references import leaf_cost

            return leaf_cost(self, node, method, bindings, conditions, background)
        if node.type in {
            "lambda_expression",
            "anonymous_method_expression",
            "typeof_expression",
            "sizeof_expression",
            "default_expression",
            "declaration_expression",
            "local_function_statement",
            "local_function_declaration",
        }:
            return ZERO
        if node.type in {
            "argument",
            "parenthesized_expression",
            "arrow_expression_clause",
            "return_statement",
        }:
            parts = value_children(node)
            if not parts:
                if node.type == "argument" and not re.fullmatch(r"out\s+_", text(node).strip()):
                    self.truncated = True
                    self.record(
                        "unresolved", "参数表达式未解析", node, method, conditions, background
                    )
                return ZERO
            return self.expression(parts[-1], method, bindings, stack, conditions, background)
        if node.type in {"cast_expression", "as_expression"}:
            from app.modules.action_timing.source_references import cast_value

            operand = node.child_by_field_name("value") or node.child_by_field_name("left")
            before = self.expression(operand, method, bindings, stack, conditions, background)
            reference = cast_value(
                self.index,
                node,
                method,
                self.index.value(operand, method, bindings),
            )
            if reference is None:
                source_parallel.invalidate_unexplored(bindings)
                self.record(
                    "unresolved",
                    "this引用转换的运行时类型未确定",
                    node,
                    method,
                    conditions,
                    background,
                )
                return before.plus(UNKNOWN)
            return before
        if node.type == "is_pattern_expression":
            result = source_dynamic.pattern(
                self, node, method, bindings, stack, conditions, background
            )
            if result is not None:
                return result
        if node.type == "conditional_access_expression":
            return self.conditional_access(
                node, None, method, bindings, stack, conditions, background
            )
        if node.type == "assignment_expression":
            return assign_property(self, node, method, bindings, stack, conditions, background)
        if node.type in {"prefix_unary_expression", "postfix_unary_expression"} and (
            "++" in text(node) or "--" in text(node)
        ):
            return increment_property(self, node, method, bindings, stack, conditions, background)
        if node.type in {"member_access_expression", "identifier"}:
            if task_returns.completed_property(self, node, method, bindings):
                return ZERO
            result = task_returns.result_property(
                self, node, method, bindings, stack, conditions, background
            )
            if result is not None:
                return result
            return read_property(self, node, method, bindings, stack, conditions, background)
        if node.type == "element_access_expression":
            from app.modules.action_timing.source_collection_expressions import read_element

            return read_element(self, node, method, bindings, stack, conditions, background)
        if node.type in collections.ARRAYS:
            from app.modules.action_timing.source_collection_expressions import create_array

            return create_array(self, node, method, bindings, stack, conditions, background)
        if node.type == "object_creation_expression":
            return create_object(self, node, method, bindings, stack, conditions, background)
        if node.type == "variable_declarator":
            right = initializer(node)
            cost = self.expression(right, method, bindings, stack, conditions, background)
            left = node.child_by_field_name("name") or next(
                iter(children(node, "tuple_pattern")), None
            )
            if left is not None and left.type == "identifier":
                value = self.index.value(right, method, bindings)
                if method.types.get(text(left)) in {"double", "float", "decimal"} and isinstance(
                    value, (int, float)
                ):
                    value = float(value)
                state.write(self.index, left, method, bindings, value)
            track_binding(self.index, left, right, method, bindings)
            return cost
        if node.type == "await_expression":
            return task_returns.await_task(
                self, node, method, bindings, stack, conditions, background
            )
        if node.type == "invocation_expression":
            if text(node.child_by_field_name("function")) == "nameof":
                return ZERO
            before = ZERO
            started = bindings.get(CLOCK, ZERO)
            function = node.child_by_field_name("function")
            target = self.index.resolve(node, method)
            if function.type == "conditional_access_expression":
                return self.conditional_access(
                    function, node, method, bindings, stack, conditions, background
                )
            callback_receiver = delegates.invocation_receiver(self.index, node, method)
            if callback_receiver == function and function.type == "member_access_expression":
                before = self.expression(function, method, bindings, stack, conditions, background)
            elif function is not None and function.type == "member_access_expression":
                receiver = function.child_by_field_name("expression")
                static_receiver = self.index.lookup_type(
                    text(receiver), method
                ) in self.index.classes and (
                    text(function.child_by_field_name("name")) == "GetInstance"
                    or (target and target.is_static)
                )
                before = (
                    ZERO
                    if static_receiver
                    else self.expression(
                        receiver,
                        method,
                        bindings,
                        stack,
                        conditions,
                        background,
                    )
                )
            elif function is not None and function.type in {
                "element_access_expression",
                "invocation_expression",
                "parenthesized_expression",
                "cast_expression",
            }:
                before = self.expression(function, method, bindings, stack, conditions, background)
            receiver_id = (
                state.receiver_for(self.index, target, node, method, bindings)
                if target is not None
                else state.MISSING
            )
            receiver_value = (
                self.index.value(function.child_by_field_name("expression"), method, bindings)
                if function.type == "member_access_expression"
                else state.MISSING
            )
            if function.type in {
                "element_access_expression",
                "invocation_expression",
                "parenthesized_expression",
                "cast_expression",
            }:
                receiver_value = self.index.value(function, method, bindings)
            if function.type in {
                "identifier",
                "member_access_expression",
            } and delegates.typed_invocation(self.index, node, method):
                receiver_value = self.index.value(callback_receiver, method, bindings)
            before = call_args.evaluate(
                self,
                node,
                method,
                bindings,
                stack,
                conditions,
                background,
                target=target,
                prefix=before,
                receiver=receiver_id,
                receiver_value=receiver_value,
            )
            bindings[CLOCK] = started.plus(before)
            result = before.plus(self.call(node, method, bindings, stack, conditions, background))
            bindings[CLOCK] = started
            return result
        if node.type == "binary_expression":
            left = node.child_by_field_name("left")
            op = text(node.child_by_field_name("operator"))
            started = bindings.get(CLOCK, ZERO)
            result_key = call_args.return_key(node, method, bindings)
            bindings.pop(result_key, None)
            before = self.expression(left, method, bindings, stack, conditions, background)
            value = self.index.value(left, method, bindings)
            if op in {"&&", "||"}:
                if (op == "&&" and value is False) or (op == "||" and value is True):
                    bindings[result_key] = value
                    return before
                branch_bindings = dict(bindings)
                branch_bindings[CLOCK] = started.plus(before)
                after = self.expression(
                    node.child_by_field_name("right"),
                    method,
                    branch_bindings,
                    stack,
                    conditions,
                    background,
                )
                right = self.index.value(node.child_by_field_name("right"), method, branch_bindings)
                branch_bindings[CLOCK] = started
                state.merge(
                    bindings, [bindings, branch_bindings] if value is None else [branch_bindings]
                )
                bindings[result_key] = binary_value(op, value, right)
                return before.plus(choice(ZERO, after) if value is None else after)
            bindings[CLOCK] = started.plus(before)
            after = self.expression(
                node.child_by_field_name("right"), method, bindings, stack, conditions, background
            )
            right = self.index.value(node.child_by_field_name("right"), method, bindings)
            null_comparison = source_dynamic.null_comparison(node, value, right)
            from app.modules.action_timing.source_references import equality

            handled, comparison, opaque = equality(self.index, node, method, value, right)
            from app.modules.action_timing.source_multicast import binary

            combined = binary(self.index, node, method, bindings, value, right)
            bindings[result_key] = (
                combined
                if combined is not state.MISSING
                else comparison
                if handled or combined is not state.MISSING
                else (
                    binary_value(op, value, right) if null_comparison is None else null_comparison
                )
            )
            bindings[CLOCK] = started
            if opaque:
                from app.modules.action_timing.source_references import invalidate_values

                if opaque == "source":
                    source_parallel.invalidate_unexplored(bindings)
                else:
                    invalidate_values((value, right), bindings)
                self.record(
                    "unresolved",
                    "自定义或外部相等运算的正文未展开",
                    node,
                    method,
                    conditions,
                    background,
                )
                return before.plus(after).plus(UNKNOWN if opaque == "source" else ZERO)
            return before.plus(after)
        if node.type == "conditional_expression":
            condition = node.child_by_field_name("condition")
            before = self.expression(condition, method, bindings, stack, conditions, background)
            value = self.index.value(condition, method, bindings)
            costs, branches, values = [], [], []
            for flag, field in [(True, "consequence"), (False, "alternative")]:
                if isinstance(value, bool) and flag != value:
                    continue
                branch = dict(bindings)
                costs.append(
                    self.expression(
                        node.child_by_field_name(field),
                        method,
                        branch,
                        stack,
                        conditions,
                        background,
                    )
                )
                values.append(self.index.value(node.child_by_field_name(field), method, branch))
                branches.append(branch)
            state.merge(bindings, branches)
            bindings[call_args.return_key(node, method, bindings)] = (
                values[0] if all(value == values[0] for value in values) else None
            )
            return before.plus(choice(costs[0], costs[1]) if len(costs) == 2 else costs[0])
        result = ZERO
        for child in children(node):
            # lambda只在明确的Task.Run处处理；不把未执行的委托内容加到当前调用。
            if child.type not in {"lambda_expression", "anonymous_method_expression"}:
                result = result.plus(
                    self.expression(child, method, bindings, stack, conditions, background)
                )
        return result

    def call(self, node, method, bindings, stack, conditions, background):
        from app.modules.action_timing import source_local_functions

        local_cost = source_local_functions.call(
            self, node, method, bindings, stack, conditions, background
        )
        if local_cost is not None:
            return local_cost
        function = node.child_by_field_name("function")
        function_name = text(function)
        binding = next(iter(children(function, "member_binding_expression")), None)
        name = (
            text(binding.child_by_field_name("name"))
            if binding
            else (
                text(function.child_by_field_name("name"))
                if function.type != "identifier"
                else function_name
            )
        )
        arguments = children(node.child_by_field_name("arguments"), "argument")
        parallel_cost = source_parallel.handle(
            self, node, method, bindings, stack, conditions, background
        )
        if parallel_cost is not None:
            return parallel_cost
        control_cost = source_parallel.control(self, node, method, bindings, conditions, background)
        if control_cost is not None:
            return control_cost
        list_cost = source_list_callbacks.handle(
            self, node, method, bindings, stack, conditions, background
        )
        if list_cost is not None:
            return list_cost
        if collections.call(self, node, method, bindings):
            return ZERO
        if name in {"Start", "StartNew", "Restart", "Stop", "Reset"}:
            receiver = function.child_by_field_name("expression")
            if (
                text(receiver) in {"Stopwatch", "System.Diagnostics.Stopwatch"}
                or self.index.infer(receiver, method) == "Stopwatch"
            ):
                return ZERO
        task_cost = handle_tasks(self, node, method, bindings, stack, conditions, background)
        if task_cost is not None:
            return task_cost
        apm_cost = source_apm.handle(self, node, method, bindings, stack, conditions, background)
        if apm_cost is not None:
            return apm_cost
        dynamic_cost = source_dynamic.invoke(
            self, node, method, bindings, stack, conditions, background
        )
        if dynamic_cost is not None:
            return dynamic_cost
        dispatch_cost = source_dispatch.handle(
            self, node, method, bindings, stack, conditions, background
        )
        if dispatch_cost is not None:
            return dispatch_cost
        callback_cost = delegates.invoke(
            self, node, method, bindings, stack, conditions, background
        )
        if callback_cost is not None:
            return callback_cost
        if function_name.endswith(("Thread.Sleep", "DelayHelper.Delay")):
            arg = arguments[0] if arguments else None
            values = call_args.values(self.index, node, method, bindings)
            value = values[0] if values else None
            if arg:
                self.defaults(arg, method, bindings)
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value >= 0
            )
            self.record(
                "delay",
                "配置/固定延时",
                node,
                method,
                conditions,
                background,
                expression=text(arg),
                milliseconds=value if valid else None,
            )
            return Cost(value, value) if valid else UNKNOWN
        target = self.index.resolve(node, method)
        if target is None:
            from app.modules.action_timing.source_references import escape_this

            if escape_this(self.index, node, method, bindings):
                self.record(
                    "unresolved",
                    "this对象传给未解析调用，后续成员保持未定",
                    node,
                    method,
                    conditions,
                    background,
                )
            collections.invalidate_arguments(self.index, node, method, bindings)
        if name in PURE_NAMES or function_name.startswith(
            ("Math.", "System.Math.", "TimeSpan.", "DateTime.", "Guid.", "Enumerable.")
        ):
            return ZERO
        if target is None:
            state.invalidate_byref(self.index, node, method, bindings)
            if self.index.has_source_call(node, method):
                self.record(
                    "unresolved", "源码调用重载或参数未绑定", node, method, conditions, background
                )
                # 该阶段使动作总耗时未定；已知延时栏只汇总实际展开的延时组成，
                # 与未绑定的运动、SDK调用保持同一口径，不能据此宣称总耗时为零。
                return ZERO
        if target and self.index.polymorphic(node, method, target):
            self.record(
                "unresolved",
                "实际动作类型由运行时选择",
                node,
                method,
                conditions,
                background,
                expression=text(node),
                note="保留动态派发，未把基类实现当成实际动作；各具体动作另行计算",
            )
            return UNKNOWN
        if not target:
            package_cost = hardware_call(self, node, method, bindings, conditions, background)
            if package_cost is not None:
                return package_cost
        if not (target and target.body) and (
            name
            in {
                "WaitAxesArrival",
                "WaitAxisArrival",
                "WaitAll",
                "WhenAll",
                "WhenAny",
            }
            or WAIT.search(name)
        ):
            self.record(
                "wait",
                "到位/信号等待，实际时间由条件决定",
                node,
                method,
                conditions,
                background,
                expression=text(node),
                milliseconds=None,
                note="参数若为超时，只是失败保护上限，不计为必耗时；并发等待取完成边界，不逐轴相加",
            )
            if name in {"Wait", "WaitOne"} and arguments:
                bound = self.index.value(arguments[0], method, bindings)
                if isinstance(bound, (int, float)) and not isinstance(bound, bool) and bound >= 0:
                    self.record(
                        "timeout",
                        "等待超时上限，不计入动作耗时",
                        node,
                        method,
                        conditions,
                        background,
                        milliseconds=bound,
                        expression=text(node),
                    )
            return ZERO
        if target and target.body:
            return self.invoke(
                target, arguments, method, node, bindings, stack, conditions, background
            )
        if name in COLLECTION_OPERATIONS:
            receiver_type = simple_type(
                self.index.infer(function.child_by_field_name("expression"), method)
            )
            if receiver_type in {
                "List",
                "HashSet",
                "Dictionary",
                "BindingList",
                "LinkedList",
                "ObservableCollection",
                "IEnumerator",
                "Enumerator",
            }:
                return ZERO
        if MOTION.search(name) and name not in COLLECTION_OPERATIONS:
            self.record(
                "motion",
                "运动调用",
                node,
                method,
                conditions,
                background,
                expression=text(node),
                arguments=[text(arg) for arg in arguments],
                milliseconds=None,
                argument_values=[self.index.value(arg, method, bindings) for arg in arguments],
                definitions=self.motion_definitions(node, method),
                note=(
                    "需起始/目标位置、速度、加减速与同步关系；"
                    "恒速下界为 |Δ位置|/速度×1000，同动轴取最大值，顺序段相加"
                ),
            )
        elif not (
            name.startswith(
                (
                    "Get",
                    "Is",
                    "Has",
                    "To",
                    "Convert",
                    "Find",
                    "Clone",
                    "Select",
                    "Add",
                    "Clear",
                    "Contains",
                    "Count",
                    "Save",
                )
            )
            or (name in {"Set", "Reset"} and "Signal" in function_name)
        ):
            self.record(
                "call",
                "调用耗时不能由当前源码确定",
                node,
                method,
                conditions,
                background,
                expression=text(node),
                milliseconds=None,
            )
        return ZERO

    def invoke(
        self,
        target,
        arguments,
        caller,
        node,
        bindings,
        stack,
        conditions,
        background,
        argument_values=None,
        receiver_id=state.MISSING,
        captures=None,
    ):
        bindings.pop(call_args.return_key(node, caller, bindings), None)
        bindings.pop(call_args.return_key(node, caller, bindings) + ":normal", None)
        metadata = target.callable_kind in {"property_get", "property_set", "initializer"}
        if target.key in stack or (not metadata and (self.depth(stack) >= 7 or self.calls >= 120)):
            from app.modules.action_timing.source_references import escape_this

            escape_this(self.index, node, caller, bindings)
            self.truncated = True
            self.record(
                "unresolved",
                "调用链达到展开边界",
                node,
                caller,
                conditions,
                background,
                expression=text(node),
            )
            return UNKNOWN if delay_possible(self.index, target) else ZERO
        if target.callable_kind in {"method", "constructor"}:
            self.calls += 1
        self.frames += 1
        slots = call_args.plan(
            target.parameters, arguments, provided=argument_values or {}, variadic=target.variadic
        )
        if slots is None:
            self.record("unresolved", "源码调用参数未绑定", node, caller, conditions, background)
            return UNKNOWN
        saved = call_args.snapshot(node, caller, bindings)
        scalars = (
            saved.values
            if saved is not None and len(saved.values) == len(arguments)
            else tuple(self.index.value(arg, caller, bindings) for arg in arguments)
        )
        callbacks = delegates.bind_arguments(
            self.index, target, arguments, caller, bindings, saved=saved
        )
        supplied = call_args.bound_values(self, target, arguments, slots, scalars, caller, bindings)
        if supplied is None:
            self.record("unresolved", "源码参数数组未绑定", node, caller, conditions, background)
            return UNKNOWN
        refs = {
            target.parameters[slots[position]][0]: slot
            for position, argument in state.byref_arguments(node)
            if position < len(slots)
            and (
                slot := saved.references[position]
                if saved is not None and position < len(saved.references)
                else state.capture_ref(self.index, argument, caller, bindings)
            )
            is not None
        }
        uncertain_refs = any(
            position < len(slots)
            and target.parameters[slots[position]][0] not in refs
            and state.argument_target(argument) is not None
            and not state.discard_argument(self.index, argument, caller)
            for position, argument in state.byref_arguments(node)
        )
        stage_start = len(self.stages)
        if uncertain_refs:
            self.record(
                "unresolved", "引用参数的实例或存储位置未绑定", node, caller, conditions, background
            )
        if receiver_id is state.MISSING:
            receiver_id = saved.receiver if saved is not None else state.MISSING
        values = {
            **self.context,
            **state.context(bindings),
            **(captures or {}),
            state.THIS: state.receiver_for(self.index, target, node, caller, bindings)
            if receiver_id is state.MISSING
            else receiver_id,
            state.FRAME: str(self.frames),
            CLOCK: bindings.get(CLOCK, ZERO),
            **supplied,
        }
        values.update(callbacks)
        for name, _, _ in target.parameters:
            bound = callbacks.get(f"{delegates.DELEGATE_PREFIX}{name}>")
            if bound and (
                isinstance(bound[1], delegates.BoundDelegate) or bound[1] is delegates.NULL_DELEGATE
            ):
                values[name] = bound[1]
        values.update(argument_values or {})
        for name, slot in refs.items():
            values[f"{state.LOCAL_ALIAS}{name}>"] = slot
            values[name] = bindings.get(slot)
        for name, _, default in target.parameters:
            if name not in values:
                values[name] = self.index.value(default, target, {})
        for name, kind, _ in target.parameters:
            if (
                kind in {"double", "float", "decimal"}
                and isinstance(values.get(name), (int, float))
                and not isinstance(values.get(name), bool)
            ):
                values[name] = float(values[name])
        if task_returns.async_method(target) and (
            task_returns.task_method(self.index, target) or target.return_type == "void"
        ):
            from app.modules.action_timing import source_async
            from app.modules.action_timing.source_tasks import remember_plan

            cost, plan = source_async.execute(
                self, target, values, (*stack, target.key), conditions, background
            )
            state.transfer(bindings, values)
            bindings[call_args.return_key(node, caller, bindings) + ":normal"] = True
            if task_returns.task_method(self.index, target):
                remember_plan(node, caller, bindings, plan, fresh=True)
            else:
                # async void没有可供调用者join的任务，续体保留后台归属。
                bindings[call_args.return_key(node, caller, bindings)] = None
            return cost
        returned_task = task_returns.task_method(self.index, target)
        if returned_task:
            from app.modules.action_timing.source_tasks import task_ids

            existing_tasks = task_ids(values.values())
        flow = self.execute_body(target, values, (*stack, target.key), conditions, background)
        bindings[call_args.return_key(node, caller, bindings) + ":normal"] = (
            flow.live is not None or flow.returned is not None
        )
        state.transfer(bindings, values, uncertain=uncertain_refs)
        for position, argument in state.byref_arguments(node):
            if position < len(slots) and target.parameters[slots[position]][0] in refs:
                continue
            assigned = state.argument_target(argument)
            if assigned is not None and text(assigned) != "_":
                value = (
                    values.get(target.parameters[slots[position]][0])
                    if position < len(slots)
                    else None
                )
                state.write(
                    self.index, assigned, caller, bindings, None if uncertain_refs else value
                )
        if uncertain_refs:
            # 未证明两个ref是否别名时，方法内赋值后的数值也不作为已知停留。
            for stage in self.stages[stage_start:]:
                stage["conditions"].append("引用参数别名未确定，不推算该段数值")
                if "milliseconds" in stage:
                    stage["milliseconds"] = None
                if "resolved" in stage:
                    stage["resolved"] = False
            return UNKNOWN
        if flow.live is None and flow.returned is None:
            self.record(
                "unresolved",
                "被调方法无法正常返回",
                node,
                caller,
                conditions,
                background,
                expression=text(node),
            )
            return UNKNOWN
        returned = flow.states.get("returned", {})
        if "<return-value>" in returned:
            bindings[call_args.return_key(node, caller, bindings)] = returned["<return-value>"]
        if returned_task:
            from app.modules.action_timing.source_tasks import (
                TaskPlan,
                is_fresh,
                known_task,
                remember_plan,
            )

            value = returned.get("<return-value>")
            task = (
                value
                if known_task(value)
                else TaskPlan(bindings.get(CLOCK, ZERO).plus(flow.cost()), UNKNOWN)
            )
            remember_plan(node, caller, bindings, task, fresh=is_fresh(task, existing_tasks))
        return flow.cost()

    def execute_body(self, method, bindings, stack, conditions, background):
        if (
            method.callable_kind == "delegate"
            and method.body is not None
            and method.body.type != "block"
        ):
            cost = self.expression(method.body, method, bindings, stack, conditions, background)
            bindings["<return-value>"] = self.index.value(method.body, method, bindings)
            return Flow(None, cost).with_state("returned", bindings)
        if method.callable_kind == "constructor":
            return constructor_body(self, method, bindings, stack, conditions, background)
        if method.callable_kind == "initializer":
            cost = self.expression(method.body, method, bindings, stack, conditions, background)
            from app.modules.action_timing.source_multicast import initialize_value

            initialize_value(self.index, method, bindings)
            return Flow(cost)
        flow = self.block(method.body, method, bindings, stack, conditions, background)
        from app.modules.action_timing.source_async import SUSPENDED

        if any(key != SUSPENDED for key in flow.jumps):
            self.truncated = True
            self.record(
                "unresolved", "跳转超出当前分析执行体", method.body, method, conditions, background
            )
            flow.live = choice(flow.live, UNKNOWN)
        return flow

    def depth(self, stack):
        return sum(
            self.index.method_kinds.get(key) not in {"property_get", "property_set", "initializer"}
            for key in stack
        )

    def conditional_access(
        self, access, invocation, method, bindings, stack, conditions, background
    ):
        receiver = access.child_by_field_name("condition")
        before = self.expression(receiver, method, bindings, stack, conditions, background)
        if text(receiver) == "null":
            return before
        value = self.index.value(receiver, method, bindings)
        callback = delegates.stored(receiver, method, bindings, self.index)
        if callback is delegates.NULL_DELEGATE:
            return before
        present = (
            isinstance(value, dict) and bool({"<type>", "<ref>"} & value.keys())
        ) or isinstance(callback, delegates.BoundDelegate)
        started = bindings.get(CLOCK, ZERO)
        original = dict(bindings)
        bindings[CLOCK] = started.plus(before)
        labels = (*conditions, f"{text(receiver)} 非空")
        cost = ZERO
        if invocation:
            target = self.index.resolve(invocation, method)
            receiver_id = (
                state.receiver_for(self.index, target, invocation, method, bindings)
                if target is not None
                else state.MISSING
            )
            cost = call_args.evaluate(
                self,
                invocation,
                method,
                bindings,
                stack,
                labels,
                background,
                target=target,
                receiver=receiver_id,
                receiver_value=value,
            )
            cost = cost.plus(self.call(invocation, method, bindings, stack, labels, background))
        else:
            binding = next(iter(children(access, "member_binding_expression")), None)
            owner = self.index.infer(receiver, method)
            target = (
                self.index.property_method(owner, text(binding.child_by_field_name("name")), "get")
                if binding
                else None
            )
            if target and target.body:
                if self.index.polymorphic(access, method, target):
                    self.record(
                        "unresolved",
                        "空条件属性的实际访问器未确定",
                        access,
                        method,
                        labels,
                        background,
                    )
                else:
                    cost = self.invoke(
                        target, [], method, access, bindings, stack, labels, background
                    )
            elif target is None:
                self.record(
                    "unresolved", "空条件属性访问未绑定", access, method, labels, background
                )
        bindings[CLOCK] = started
        if not present:
            state.merge(bindings, [original, dict(bindings)])
        return before.plus(cost if present else choice(ZERO, cost))

    def motion_definitions(self, node, method):
        identifiers = {text(part) for part in walk(node) if part.type == "identifier"}
        return [
            method.unit.evidence(part)
            for part in walk(method.node)
            if part.type == "variable_declarator"
            and text(part.child_by_field_name("name")) in identifiers
            and initializer(part) is not None
        ][:12]

    def block(self, node, method, bindings, stack, conditions, background):
        from app.modules.action_timing.source_scopes import embedded, inline_names

        names = inline_names(node, self.index) if embedded(node) else []
        if names:
            with local_scope(self, names, bindings) as before:
                flow = self._block(node, method, bindings, stack, conditions, background)
                for snapshot in flow.states.values():
                    restore(snapshot, before)
                return flow
        return self._block(node, method, bindings, stack, conditions, background)

    def _block(self, node, method, bindings, stack, conditions, background):
        if node is None:
            return Flow()
        kind = node.type
        if kind in {"local_function_statement", "local_function_declaration"}:
            return Flow()
        if kind == "arrow_expression_clause":
            from app.modules.action_timing.source_closures import returned

            cost = self.expression(node, method, bindings, stack, conditions, background)
            bindings["<return-value>"] = returned(self.index, node, method, bindings)
            return Flow(None, cost).with_state("returned", bindings)
        if kind in {"block", "switch_section"}:
            from app.modules.action_timing import source_local_functions

            with (
                local_scope(self, declarations(node, self.index), bindings) as before,
                source_local_functions.scope(self, node, method, bindings) as previous_functions,
            ):
                flow = self.sequence(node, method, bindings, stack, conditions, background)
                for snapshot in flow.states.values():
                    restore(snapshot, before)
                    source_local_functions.restore(snapshot, previous_functions)
                return flow
        if kind == "if_statement":
            condition = node.child_by_field_name("condition")
            before = self.expression(condition, method, bindings, stack, conditions, background)
            value = self.index.value(condition, method, bindings)
            branches = []
            continuing_bindings = []
            for flag, field in [(True, "consequence"), (False, "alternative")]:
                if isinstance(value, bool) and value != flag:
                    continue
                label = text(condition) if flag else f"非({text(condition)})"
                branch_bindings = dict(bindings)
                branch = self.block(
                    node.child_by_field_name(field),
                    method,
                    branch_bindings,
                    stack,
                    (*conditions, label),
                    background,
                )
                branches.append(branch)
                if branch.live is not None:
                    continuing_bindings.append(branch_bindings)
            if continuing_bindings:
                state.merge(bindings, continuing_bindings)
            result = branches[0]
            if len(branches) == 2:
                result = result.merge(branches[1])
            return result.prefix(before)
        if kind == "return_statement":
            value = text(node)
            cost = self.expression(node, method, bindings, stack, conditions, background)
            if method.body_override is not None:
                # 服务循环内部 return 结束线程，并非该轮动作正常完成。
                return Flow(None, None)
            if method.key == self.root_method and any(
                "DryCycle" in condition for condition in conditions
            ):
                self.skip_conditions.extend(conditions)
            if re.search(r"ExcuteResult\.(?:Abort|Fail|Alarm|Exception|Retry)", value):
                return Flow(None, None)
            # Wait 的 false 表示等待中止；普通布尔查询返回 false 仍是正常完成。
            if (method.key == self.root_method or WAIT.search(method.name)) and re.search(
                r"return\s+false\b", value
            ):
                return Flow(None, None)
            expression = next(iter(value_children(node)), None)
            from app.modules.action_timing.source_closures import returned

            bindings["<return-value>"] = returned(self.index, expression, method, bindings)
            return Flow(None, cost).with_state("returned", bindings)
        if kind == "break_statement":
            return Flow(None, broken=ZERO).with_state("broken", bindings)
        if kind == "continue_statement":
            return Flow(None, continued=ZERO).with_state("continued", bindings)
        if kind == "throw_statement":
            self.failure_reasons.append(text(node).removeprefix("throw ").removesuffix(";")[:180])
            return Flow(None, None)
        if kind == "try_statement":
            started = bindings.get(CLOCK, ZERO)
            body = next(iter(children(node, "block")), None)
            result = self.block(body, method, bindings, stack, conditions, background)
            bindings[CLOCK] = started
            continuing = [dict(bindings)] if result.live is not None else []
            for caught in children(node, "catch_clause"):
                handler_bindings = dict(bindings)
                handler_bindings[CLOCK] = started
                handler = self.block(
                    next(iter(children(caught, "block")), None),
                    method,
                    handler_bindings,
                    stack,
                    (*conditions, "异常恢复分支"),
                    background,
                )
                if (
                    any(
                        cost is not None
                        for cost in (
                            handler.live,
                            handler.returned,
                            handler.broken,
                            handler.continued,
                        )
                    )
                    or handler.jumps
                ):
                    # 异常发生点不确定，恢复不能被当作无成本的顺序正常路径。
                    result = result.merge(handler.prefix(UNKNOWN))
                    self.record(
                        "unresolved", "异常恢复路径耗时未定", caught, method, conditions, background
                    )
                if handler.live is not None:
                    continuing.append(handler_bindings)
            if continuing:
                state.merge(bindings, continuing)
            bindings[CLOCK] = started
            final = next(iter(children(node, "finally_clause")), None)
            if final:
                result = source_finally.execute(
                    self,
                    final,
                    result,
                    method,
                    bindings,
                    stack,
                    conditions,
                    background,
                )
            return result
        if kind == "for_statement":
            return execute_for(self, node, method, bindings, stack, conditions, background)
        if kind in {"while_statement", "do_statement"}:
            return execute_condition_loop(
                self, node, method, bindings, stack, conditions, background
            )
        if kind in {
            "for_each_statement",
            "foreach_statement",
        }:
            return execute_foreach(self, node, method, bindings, stack, conditions, background)
        if kind == "switch_statement":
            body = node.child_by_field_name("body")
            value_node = node.child_by_field_name("value")
            value = self.index.value(value_node, method, bindings)
            before = self.expression(value_node, method, bindings, stack, conditions, background)
            sections = children(body, "switch_section")
            defaults = [
                section
                for section in sections
                if any(child.type == "default" for child in section.children)
            ]
            if value is not None:
                matches = [
                    section
                    for section in sections
                    if any(
                        self.index.value(pattern, method, bindings) == value
                        for pattern in children(section, "constant_pattern")
                    )
                ]
                sections = matches or defaults
            result = Flow(None, None)
            continuing_bindings = []
            for section in sections:
                labels = " ".join(text(part) for part in children(section, "constant_pattern"))
                branch_bindings = dict(bindings)
                branch = self.block(
                    section,
                    method,
                    branch_bindings,
                    stack,
                    (*conditions, labels or "switch 分支"),
                    background,
                )
                branch.live = choice(branch.live, branch.broken)
                branch.broken = None
                result = result.merge(branch)
                if branch.live is not None:
                    continuing_bindings.append(branch_bindings)
            if not sections or (value is None and not defaults):
                result.live = choice(result.live, ZERO)
                continuing_bindings.append(dict(bindings))
            if continuing_bindings:
                state.merge(bindings, continuing_bindings)
            return result.prefix(before)
        if kind in {"expression_statement", "local_declaration_statement"}:
            return Flow(self.expression(node, method, bindings, stack, conditions, background))
        if kind in {
            "using_statement",
            "lock_statement",
            "checked_statement",
            "unsafe_statement",
            "fixed_statement",
        }:
            if kind == "lock_statement":
                self.record(
                    "wait",
                    "锁等待时间未定",
                    node,
                    method,
                    conditions,
                    background,
                    milliseconds=None,
                )
            return self.block(
                node.child_by_field_name("body") or next(iter(children(node, "block")), None),
                method,
                bindings,
                stack,
                conditions,
                background,
            )
        if kind == "labeled_statement":
            return self.block(
                jumps.labeled_body(node), method, bindings, stack, conditions, background
            )
        if kind == "goto_statement":
            return jumps.transfer(self, node, method, bindings, conditions, background)
        if kind.endswith("_statement") and kind not in {
            "break_statement",
            "continue_statement",
            "empty_statement",
        }:
            self.truncated = True
            self.record(
                "unresolved",
                "未支持的控制流，保留未定耗时",
                node,
                method,
                conditions,
                background,
                expression=text(node)[:200],
            )
            return Flow(UNKNOWN)
        return Flow()

    def sequence(self, node, method, bindings, stack, conditions, background):
        if jumps.labels(node, method):
            return jumps.sequence(self, node, method, bindings, stack, conditions, background)
        result = Flow()
        for child in children(node):
            if result.live is None:
                break
            started = bindings.get(CLOCK, ZERO)
            part = self.block(child, method, bindings, stack, conditions, background)
            bindings[CLOCK] = started.plus(part.live) if part.live is not None else UNKNOWN
            result = result.then(part)
        return result

    def _timeouts(self, node, method, conditions, background):
        for part in walk(node):
            if part.type != "binary_expression":
                continue
            source = text(part)
            match = re.search(
                r"\.Elapsed\.Total(Seconds|Milliseconds)\s*[><]=?\s*(\d+(?:\.\d+)?)", source
            )
            if match:
                value = float(match[2]) * (1000 if match[1] == "Seconds" else 1)
                self.record(
                    "timeout",
                    "超时保护上限，不计入动作耗时",
                    part,
                    method,
                    conditions,
                    background,
                    milliseconds=value,
                    expression=source,
                )
            elif "DateTime" in source or ".Elapsed" in source:
                span = re.search(
                    r"TimeSpan\.From(Seconds|Milliseconds)\(\s*(\d+(?:\.\d+)?)\s*\)", source
                )
                if span and text(part.child_by_field_name("operator")) in {">", ">=", "<", "<="}:
                    value = float(span[2]) * (1000 if span[1] == "Seconds" else 1)
                    self.record(
                        "timeout",
                        "超时保护上限，不计入动作耗时",
                        part,
                        method,
                        conditions,
                        background,
                        milliseconds=value,
                        expression=source,
                    )
