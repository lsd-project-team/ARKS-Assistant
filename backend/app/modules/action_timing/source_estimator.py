"""按源码分支合并配置延时；运动、信号和超时保持各自的物理含义。"""

import math
import re

from app.modules.action_timing.source_construction import constructor_body, create_object
from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost, Flow, add, choice
from app.modules.action_timing.source_hardware import hardware_call
from app.modules.action_timing.source_index import children, initializer, simple_type, text, walk
from app.modules.action_timing.source_properties import (
    assign_property,
    increment_property,
    read_property,
)
from app.modules.action_timing.source_tasks import CLOCK, handle_tasks, lookup

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

    def estimate(self, method):
        if method.unit.tree.root_node.has_error:
            self.truncated = True
        self.root_method = method.key
        bindings = {
            **self.context,
            **{
                name: self.index.value(default, method, self.context)
                for name, _, default in method.parameters
            },
        }
        flow = self.execute_body(method, bindings, (method.key,), (), False)
        cost = flow.cost()
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
            formula = f"{cost.lower:g}–{cost.upper:g} ms 已知延时（分支相关）"
        if unknown:
            formula += " + 运动/信号/未解析调用"
        if not has_success_path:
            formula = "未发现正常完成路径，不推算成功动作耗时"
        return {
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
                    "value": self.index.value(part, method, bindings),
                    "expression": text(initializer),
                    **unit.evidence(initializer),
                }

    def expression(self, node, method, bindings, stack, conditions, background):
        if node is None:
            return ZERO
        if node.type in {
            "lambda_expression",
            "anonymous_method_expression",
            "typeof_expression",
            "sizeof_expression",
            "default_expression",
        }:
            return ZERO
        if node.type == "argument":
            parts = children(node)
            if not parts:
                if not re.fullmatch(r"out\s+_", text(node).strip()):
                    self.truncated = True
                    self.record(
                        "unresolved", "参数表达式未解析", node, method, conditions, background
                    )
                return ZERO
            return self.expression(parts[-1], method, bindings, stack, conditions, background)
        if node.type == "cast_expression":
            return self.expression(
                node.child_by_field_name("value"), method, bindings, stack, conditions, background
            )
        if node.type == "as_expression":
            return self.expression(
                node.child_by_field_name("left"), method, bindings, stack, conditions, background
            )
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
            return read_property(self, node, method, bindings, stack, conditions, background)
        if node.type == "object_creation_expression":
            return create_object(self, node, method, bindings, stack, conditions, background)
        if node.type == "await_expression":
            operand = children(node)[-1]
            plan = lookup(operand, method, bindings)
            if plan and operand.type != "invocation_expression":
                cost = plan.remaining(bindings.get(CLOCK, ZERO))
                self.record(
                    "wait",
                    "等待任务完成",
                    node,
                    method,
                    conditions,
                    background,
                    resolved=cost.upper is not None,
                )
                return cost
        if node.type == "invocation_expression":
            if text(node.child_by_field_name("function")) == "nameof":
                return ZERO
            before = ZERO
            started = bindings.get(CLOCK, ZERO)
            function = node.child_by_field_name("function")
            if function.type == "conditional_access_expression":
                return self.conditional_access(
                    function, node, method, bindings, stack, conditions, background
                )
            if function is not None and function.type == "member_access_expression":
                receiver = function.child_by_field_name("expression")
                target = self.index.resolve(node, method)
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
            for argument in children(node.child_by_field_name("arguments"), "argument"):
                bindings[CLOCK] = started.plus(before)
                before = before.plus(
                    self.expression(argument, method, bindings, stack, conditions, background)
                )
            bindings[CLOCK] = started.plus(before)
            result = before.plus(self.call(node, method, bindings, stack, conditions, background))
            bindings[CLOCK] = started
            return result
        if node.type == "binary_expression":
            left = node.child_by_field_name("left")
            op = text(node.child_by_field_name("operator"))
            value = self.index.value(left, method, bindings)
            if op in {"&&", "||"}:
                before = self.expression(left, method, bindings, stack, conditions, background)
                if (op == "&&" and value is False) or (op == "||" and value is True):
                    return before
                after = self.expression(
                    node.child_by_field_name("right"),
                    method,
                    bindings,
                    stack,
                    conditions,
                    background,
                )
                return before.plus(choice(ZERO, after) if value is None else after)
        if node.type == "conditional_expression":
            condition = node.child_by_field_name("condition")
            before = self.expression(condition, method, bindings, stack, conditions, background)
            value = self.index.value(condition, method, bindings)
            costs = [
                self.expression(
                    node.child_by_field_name(field), method, bindings, stack, conditions, background
                )
                for flag, field in [(True, "consequence"), (False, "alternative")]
                if not isinstance(value, bool) or flag == value
            ]
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
        if function_name.endswith(("Thread.Sleep", "DelayHelper.Delay")):
            arg = arguments[0] if arguments else None
            value = self.index.value(arg, method, bindings)
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
        if name in PURE_NAMES or function_name.startswith(
            ("Math.", "System.Math.", "TimeSpan.", "DateTime.", "Guid.", "Enumerable.")
        ):
            return ZERO
        target = self.index.resolve(node, method)
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
    ):
        metadata = target.callable_kind in {"property_get", "property_set", "initializer"}
        if target.key in stack or (not metadata and (self.depth(stack) >= 7 or self.calls >= 120)):
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
            return UNKNOWN
        if target.callable_kind in {"method", "constructor"}:
            self.calls += 1
        values = {
            **self.context,
            CLOCK: bindings.get(CLOCK, ZERO),
            **{
                parameter[0]: self.index.value(argument, caller, bindings)
                for parameter, argument in zip(target.parameters, arguments, strict=False)
            },
        }
        values.update(argument_values or {})
        for name, _, default in target.parameters[len(arguments) :]:
            if name not in values:
                values[name] = self.index.value(default, target, {})
        for name, kind, _ in target.parameters:
            if (
                kind in {"double", "float", "decimal"}
                and isinstance(values.get(name), (int, float))
                and not isinstance(values.get(name), bool)
            ):
                values[name] = float(values[name])
        flow = self.execute_body(target, values, (*stack, target.key), conditions, background)
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
        return flow.cost()

    def execute_body(self, method, bindings, stack, conditions, background):
        if method.callable_kind == "constructor":
            return constructor_body(self, method, bindings, stack, conditions, background)
        if method.callable_kind == "initializer":
            return Flow(
                self.expression(method.body, method, bindings, stack, conditions, background)
            )
        return self.block(method.body, method, bindings, stack, conditions, background)

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
        present = isinstance(value, dict) and "<type>" in value
        started = bindings.get(CLOCK, ZERO)
        bindings[CLOCK] = started.plus(before)
        labels = (*conditions, f"{text(receiver)} 非空")
        cost = ZERO
        if invocation:
            for arg in children(invocation.child_by_field_name("arguments"), "argument"):
                bindings[CLOCK] = started.plus(before).plus(cost)
                cost = cost.plus(self.expression(arg, method, bindings, stack, labels, background))
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
        if node is None:
            return Flow()
        kind = node.type
        if kind == "arrow_expression_clause":
            return Flow(
                None, self.expression(node, method, bindings, stack, conditions, background)
            )
        if kind in {"block", "switch_section"}:
            result = Flow()
            for child in children(node):
                if result.live is None:
                    break
                started = bindings.get(CLOCK, ZERO)
                part = self.block(child, method, bindings, stack, conditions, background)
                bindings[CLOCK] = started.plus(part.live) if part.live is not None else UNKNOWN
                result = result.then(part)
            return result
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
                keys = set().union(*(state.keys() for state in continuing_bindings))
                for key in keys:
                    values = [state.get(key) for state in continuing_bindings]
                    bindings[key] = (
                        values[0] if all(value == values[0] for value in values) else None
                    )
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
            return Flow(None, cost)
        if kind == "break_statement":
            return Flow(None, broken=ZERO)
        if kind == "continue_statement":
            return Flow(None, continued=ZERO)
        if kind == "throw_statement":
            self.failure_reasons.append(text(node).removeprefix("throw ").removesuffix(";")[:180])
            return Flow(None, None)
        if kind == "try_statement":
            body = next(iter(children(node, "block")), None)
            result = self.block(body, method, bindings, stack, conditions, background)
            for caught in children(node, "catch_clause"):
                handler = self.block(
                    next(iter(children(caught, "block")), None),
                    method,
                    dict(bindings),
                    stack,
                    (*conditions, "异常恢复分支"),
                    background,
                )
                if handler.live is not None or handler.returned is not None:
                    # 异常发生点不确定，恢复不能被当作无成本的顺序正常路径。
                    result = result.merge(handler.prefix(UNKNOWN))
                    self.record(
                        "unresolved", "异常恢复路径耗时未定", caught, method, conditions, background
                    )
            final = next(iter(children(node, "finally_clause")), None)
            if final:
                cost = self.block(
                    next(iter(children(final, "block")), None),
                    method,
                    bindings,
                    stack,
                    conditions,
                    background,
                ).cost()
                result = result.prefix(cost)
            return result
        if kind in {
            "while_statement",
            "do_statement",
            "for_statement",
            "for_each_statement",
            "foreach_statement",
        }:
            body = node.child_by_field_name("body")
            condition = node.child_by_field_name("condition")
            condition_cost = self.expression(
                condition, method, bindings, stack, conditions, background
            )
            value = self.index.value(condition, method, bindings)
            iterations = (
                self.iterations(node, method, bindings) if kind == "for_statement" else None
            )
            if (kind == "while_statement" and value is False) or iterations == 0:
                return Flow(condition_cost)
            label = f"循环：{text(node.child_by_field_name('condition')) or '次数依赖运行数据'}"
            start = len(self.stages)
            body_flow = self.block(
                body, method, dict(bindings), stack, (*conditions, label), background
            )
            for changed in walk(body):
                if changed.type == "assignment_expression":
                    assigned = text(changed.child_by_field_name("left"))
                    if assigned in bindings:
                        bindings[assigned] = None
            each = body_flow.cost()
            for stage in self.stages[start:]:
                stage["repeat"] = True
            self.record(
                "loop",
                f"固定循环 {iterations} 次"
                if iterations is not None
                else "循环次数未定，不把每轮延时当作单次总耗时",
                node,
                method,
                conditions,
                background,
                iterations=iterations,
                bounded=(kind == "do_statement" and value is False)
                or (body_flow.live is None and body_flow.continued is None),
                per_iteration_min_ms=each.lower,
                per_iteration_max_ms=each.upper,
            )
            self._timeouts(node, method, conditions, background)
            # break/continue 只终止其所属控制结构；不能继续计入不可达的后续语句。
            if body_flow.live is None and body_flow.continued is None:
                exited = Flow(body_flow.broken, body_flow.returned)
                if kind != "do_statement":
                    exited = exited.prefix(condition_cost)
                if kind != "do_statement" and value is not True:
                    exited.live = choice(condition_cost, exited.live)
                return exited
            if iterations is not None:
                return Flow(
                    Cost(
                        each.lower * iterations + condition_cost.lower * (iterations + 1),
                        each.upper * iterations + condition_cost.upper * (iterations + 1)
                        if each.upper is not None and condition_cost.upper is not None
                        else None,
                    )
                )
            if kind == "do_statement" and value is False:
                return Flow(
                    choice(
                        add(choice(body_flow.live, body_flow.continued), condition_cost),
                        body_flow.broken,
                    ),
                    body_flow.returned,
                )
            return Flow(
                live=Cost(
                    (each.lower if kind == "do_statement" else 0) + condition_cost.lower, None
                )
                if each.upper != 0 or condition_cost.upper != 0
                else ZERO
            )
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
                for key in set().union(*(state.keys() for state in continuing_bindings)):
                    values = [state.get(key) for state in continuing_bindings]
                    bindings[key] = values[0] if all(item == values[0] for item in values) else None
            return result.prefix(before)
        if kind == "local_declaration_statement":
            for declaration in children(node, "variable_declaration"):
                for variable in children(declaration, "variable_declarator"):
                    value = self.index.value(initializer(variable), method, bindings)
                    if text(declaration.child_by_field_name("type")) in {
                        "double",
                        "float",
                        "decimal",
                    } and isinstance(value, (int, float)):
                        value = float(value)
                    bindings[text(variable.child_by_field_name("name"))] = value
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
            self.truncated = True
            self.record(
                "unresolved",
                "含标签跳转，顺序总时长保持未定",
                node,
                method,
                conditions,
                background,
                expression=text(node)[:180],
            )
            return Flow(UNKNOWN)
        if kind == "goto_statement":
            self.truncated = True
            return Flow(UNKNOWN)
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

    def iterations(self, node, method, bindings):
        # 只计算明确的非负整数字面量/已知参数上界、步长为1的for；其余保留公式。
        source = text(node)
        if any(
            part.type
            in {"break_statement", "continue_statement", "return_statement", "goto_statement"}
            for part in walk(node.child_by_field_name("body"))
        ):
            return None
        match = re.match(
            r"for\s*\(\s*(?:int\s+)?(\w+)\s*=\s*(\d+)\s*;\s*\1\s*(<|<=)\s*([\w.]+)\s*;\s*(?:\1\+\+|\+\+\1)\s*\)",
            source,
        )
        if not match:
            return None
        end = float(match[4]) if match[4].isdigit() else bindings.get(match[4])
        if not isinstance(end, (int, float)) or isinstance(end, bool) or not math.isfinite(end):
            return None
        if end != int(end) or abs(end) > 1_000_000:
            return None
        if 0 <= int(match[2]) <= 1_000_000:
            return max(0, int(end) - int(match[2]) + (match[3] == "<="))
        return None

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
