"""按源码分支合并配置延时；运动、信号和超时保持各自的物理含义。"""

import math
import re
from dataclasses import dataclass

from app.modules.action_timing.source_index import children, initializer, text, walk


@dataclass(frozen=True)
class Cost:
    lower: float = 0
    upper: float | None = 0

    def plus(self, other):
        return Cost(
            self.lower + other.lower,
            None if self.upper is None or other.upper is None else self.upper + other.upper,
        )


ZERO = Cost()
UNKNOWN = Cost(0, None)


def choice(left, right):
    if left is None:
        return right
    if right is None:
        return left
    return Cost(
        min(left.lower, right.lower),
        None if left.upper is None or right.upper is None else max(left.upper, right.upper),
    )


def add(left, right):
    return left.plus(right) if left is not None and right is not None else None


@dataclass
class Flow:
    live: Cost | None = ZERO
    returned: Cost | None = None

    def then(self, other):
        return Flow(
            add(self.live, other.live), choice(self.returned, add(self.live, other.returned))
        )

    def cost(self):
        return choice(self.live, self.returned) or ZERO


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
WAIT = re.compile(r"^(?:Wait|SpinUntil)|Signal\.(?:Wait|WaitOne)|\.WaitOne$", re.I)


class Estimator:
    def __init__(self, index):
        self.index = index
        self.stages = []
        self.parameters = {}
        self.calls = 0
        self.truncated = False

    def estimate(self, method):
        if method.unit.tree.root_node.has_error:
            self.truncated = True
        flow = self.block(method.body, method, {}, (), (), False)
        cost = flow.cost()
        has_success_path = flow.live is not None or flow.returned is not None
        unknown = any(
            row["kind"] in {"motion", "wait", "call", "unresolved"} and not row["background"]
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
        if node.type == "invocation_expression":
            return self.call(node, method, bindings, stack, conditions, background)
        if node.type == "binary_expression":
            left = node.child_by_field_name("left")
            op = text(node.child_by_field_name("operator"))
            value = self.index.value(left, method, bindings)
            if (op == "&&" and value is False) or (op == "||" and value is True):
                return self.expression(left, method, bindings, stack, conditions, background)
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
        name = (
            text(function.child_by_field_name("name"))
            if function.type != "identifier"
            else function_name
        )
        arguments = children(node.child_by_field_name("arguments"), "argument")
        if name in {"Start", "StartNew", "Restart", "Stop", "Reset"}:
            receiver = function.child_by_field_name("expression")
            if (
                text(receiver) in {"Stopwatch", "System.Diagnostics.Stopwatch"}
                or self.index.infer(receiver, method) == "Stopwatch"
            ):
                return ZERO
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
        if function_name in {"Task.Run", "Task.Factory.StartNew"}:
            self.record(
                "background", "后台分支，独立展示，不累加到同步耗时", node, method, conditions, True
            )
            for arg in arguments:
                for part in children(arg):
                    if part.type in {"lambda_expression", "anonymous_method_expression"}:
                        self.block(
                            part.child_by_field_name("body"),
                            method,
                            dict(bindings),
                            stack,
                            conditions,
                            True,
                        )
            return ZERO
        if name in PURE_NAMES or function_name.startswith(
            ("Math.", "System.Math.", "TimeSpan.", "DateTime.", "Guid.", "Enumerable.")
        ):
            return ZERO
        if name in {
            "WaitAxesArrival",
            "WaitAxisArrival",
            "WaitAll",
            "WhenAll",
            "WhenAny",
        } or WAIT.search(name):
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
        target = self.index.resolve(node, method)
        if target and target.body:
            if target.key in stack or len(stack) >= 7 or self.calls >= 120:
                self.truncated = True
                self.record(
                    "unresolved",
                    "调用链达到展开边界",
                    node,
                    method,
                    conditions,
                    background,
                    expression=text(node),
                )
                return UNKNOWN
            self.calls += 1
            values = {
                parameter[0]: self.index.value(arg, method, bindings)
                for parameter, arg in zip(target.parameters, arguments, strict=False)
            }
            for name, _, default in target.parameters[len(arguments) :]:
                values[name] = self.index.value(default, target, {})
            return self.block(
                target.body, target, values, (*stack, target.key), conditions, background
            ).cost()
        if MOTION.search(name):
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
                    "Remove",
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
        if kind in {"block", "switch_section"}:
            result = Flow()
            for child in children(node):
                if result.live is None:
                    break
                result = result.then(
                    self.block(child, method, bindings, stack, conditions, background)
                )
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
                result = Flow(
                    choice(result.live, branches[1].live),
                    choice(result.returned, branches[1].returned),
                )
            return Flow(add(before, result.live), add(before, result.returned))
        if kind == "return_statement":
            value = text(node)
            cost = self.expression(node, method, bindings, stack, conditions, background)
            if re.search(
                r"ExcuteResult\.(?:Abort|Fail|Alarm|Exception|Retry)|return\s+false\b", value
            ):
                return Flow(None, None)
            return Flow(None, cost)
        if kind == "throw_statement":
            return Flow(None, None)
        if kind == "try_statement":
            body = next(iter(children(node, "block")), None)
            result = self.block(body, method, bindings, stack, conditions, background)
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
                result = Flow(add(result.live, cost), add(result.returned, cost))
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
            value = self.index.value(condition, method, bindings)
            iterations = (
                self.iterations(node, method, bindings) if kind == "for_statement" else None
            )
            if (kind == "while_statement" and value is False) or iterations == 0:
                return Flow()
            label = f"循环：{text(node.child_by_field_name('condition')) or '次数依赖运行数据'}"
            start = len(self.stages)
            each = self.block(
                body, method, dict(bindings), stack, (*conditions, label), background
            ).cost()
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
                per_iteration_min_ms=each.lower,
                per_iteration_max_ms=each.upper,
            )
            self.expression(condition, method, bindings, stack, conditions, background)
            self._timeouts(node, method, conditions, background)
            if iterations is not None:
                return Flow(
                    Cost(
                        each.lower * iterations,
                        each.upper * iterations if each.upper is not None else None,
                    )
                )
            if kind == "do_statement" and value is False:
                return Flow(each)
            return Flow(live=UNKNOWN if each.upper != 0 else ZERO)
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
            for section in sections:
                labels = " ".join(text(part) for part in children(section, "constant_pattern"))
                branch = self.block(
                    section,
                    method,
                    dict(bindings),
                    stack,
                    (*conditions, labels or "switch 分支"),
                    background,
                )
                result = Flow(
                    choice(result.live, branch.live), choice(result.returned, branch.returned)
                )
            if not sections or (value is None and not defaults):
                result.live = choice(result.live, ZERO)
            return Flow(add(before, result.live), add(before, result.returned))
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
        if kind == "expression_statement":
            for assignment in children(node, "assignment_expression"):
                name = text(assignment.child_by_field_name("left"))
                right = self.index.value(assignment.child_by_field_name("right"), method, bindings)
                operator = text(assignment.child_by_field_name("operator"))
                current = bindings.get(name)
                if operator == "=":
                    bindings[name] = right
                elif (
                    operator == "+="
                    and isinstance(current, (int, float))
                    and isinstance(right, (int, float))
                ):
                    bindings[name] = current + right
                else:
                    bindings[name] = None
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
