"""只对已证明无副作用的整数for延时正文精确求和，不猜测设备轨迹。"""

from dataclasses import dataclass

from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import Cost
from app.modules.action_timing.source_index import children, text, walk


@dataclass
class PureLoop:
    variable: object
    count: int
    final_value: int
    cost: Cost
    each: Cost
    sleeps: list


def depends_on(index, node, variable, method, bindings):
    slot = state.local_slot(variable, method, bindings) if variable is not None else None
    for part in walk(node):
        if part.type not in {"identifier", "member_access_expression"}:
            continue
        place = state.location(index, part, method, bindings)
        if text(part) == text(variable) or (
            slot is not None
            and (
                state.local_slot(part, method, bindings) == slot
                or (place is not None and state.key(place) == slot)
            )
        ):
            return True
    return False


def pure_value(index, node, method, bindings, variable=None):
    if variable is not None and depends_on(index, node, variable, method, bindings):
        return False
    for part in walk(node):
        if part.type in {
            "invocation_expression",
            "assignment_expression",
            "postfix_unary_expression",
        }:
            return False
        if part.type == "prefix_unary_expression" and any(op in text(part) for op in ("++", "--")):
            return False
        if part.type in {"identifier", "member_access_expression"}:
            getter = index.accessor(part, method, "get")
            if getter and getter.body is not None:
                return False
    return True


def counted_range(index, node, method, bindings):
    condition = node.child_by_field_name("condition")
    if condition is None or condition.type != "binary_expression":
        return None
    variable = condition.child_by_field_name("left")
    if variable.type != "identifier" or method.types.get(text(variable)) not in {"int", "var"}:
        return None
    updates = [
        part for i, part in enumerate(node.children) if node.field_name_for_child(i) == "update"
    ]
    if len(updates) != 1:
        return None
    update = updates[0]
    if update.type in {"prefix_unary_expression", "postfix_unary_expression"}:
        operand = children(update)[-1]
        step = 1 if "++" in text(update) else -1
    elif update.type == "assignment_expression":
        operand = update.child_by_field_name("left")
        operator = text(update.child_by_field_name("operator"))
        right = update.child_by_field_name("right")
        if operator not in {"+=", "-="} or not pure_value(index, right, method, bindings, variable):
            return None
        step = index.value(right, method, bindings)
        step = -step if isinstance(step, int) and operator == "-=" else step
    else:
        return None
    if text(operand) != text(variable):
        return None
    start = index.value(variable, method, bindings)
    right = condition.child_by_field_name("right")
    if not pure_value(index, right, method, bindings, variable):
        return None
    end = index.value(right, method, bindings)
    if not all(
        isinstance(value, int) and not isinstance(value, bool) for value in (start, end, step)
    ):
        return None
    operator = text(condition.child_by_field_name("operator"))
    if (operator in {"<", "<="} and step > 0) or (operator in {">", ">="} and step < 0):
        distance, stride = (end - start if step > 0 else start - end), abs(step)
        count = max(
            0,
            (distance + stride - 1) // stride if operator in {"<", ">"} else distance // stride + 1,
        )
    else:
        return None
    final = start + count * step
    if not all(-(2**31) <= value <= 2**31 - 1 for value in (start, final)):
        return None
    return variable, start, step, count, final


def sleep_calls(index, body, method, bindings):
    if body.type == "block":
        statements = [node for node in children(body) if node.type != "comment"]
    else:
        statements = [body]
    result = []
    for statement in statements:
        if statement.type == "empty_statement":
            continue
        if statement.type != "expression_statement":
            return None
        call = next(iter(children(statement)), None)
        if call is None or call.type != "invocation_expression":
            return None
        function = text(call.child_by_field_name("function"))
        if function not in {"Thread.Sleep", "System.Threading.Thread.Sleep"} or index.resolve(
            call, method
        ):
            return None
        if function == "Thread.Sleep" and (
            "Thread" in method.types
            or index.member_type(method.owner, "Thread")
            or index.lookup_type("Thread", method) in index.classes
        ):
            return None
        args = children(call.child_by_field_name("arguments"), "argument")
        if len(args) != 1:
            return None
        if not pure_value(index, args[0], method, bindings):
            return None
        result.append(args[0])
    return result


def pure_loop(estimator, node, method, bindings, minimum_count):
    # 数值探测不执行表达式，不能复用上一次进入该循环时保存的表达式结果。
    # 使用无实参/返回快照的投影副本；正常逐轮执行仍保留原来的求值时点。
    bindings = {
        name: value for name, value in bindings.items() if not name.startswith("<arguments:")
    }
    index = estimator.index
    limits = counted_range(index, node, method, bindings)
    if limits is None:
        return None
    variable, start, step, count, final = limits
    if not minimum_count < count <= 100_000:
        return None
    calls = sleep_calls(index, node.child_by_field_name("body"), method, bindings)
    if calls is None:
        return None
    constant = not any(depends_on(index, arg, variable, method, bindings) for arg in calls)
    probes = 1 if constant else count
    if estimator.numeric_loop_steps + probes > 100_000:
        return None
    estimator.numeric_loop_steps += probes
    stats = [{"min": None, "max": None, "sum": 0} for _ in calls]
    total, smallest, largest = 0, None, 0
    try:
        for i in range(probes):
            state.write(index, variable, method, bindings, start + i * step)
            subtotal = 0
            for arg, stat in zip(calls, stats, strict=True):
                value = index.value(arg, method, bindings)
                if (
                    not isinstance(value, int)
                    or isinstance(value, bool)
                    or not 0 <= value <= 2**31 - 1
                ):
                    return None
                stat["sum"] += value
                stat["min"] = value if stat["min"] is None else min(stat["min"], value)
                stat["max"] = value if stat["max"] is None else max(stat["max"], value)
                subtotal += value
            total += subtotal
            smallest = subtotal if smallest is None else min(smallest, subtotal)
            largest = max(largest, subtotal)
    finally:
        state.write(index, variable, method, bindings, start)
    if constant:
        total *= count
        for stat in stats:
            stat["sum"] *= count
    return PureLoop(variable, count, final, Cost(total, total), Cost(smallest or 0, largest), stats)
