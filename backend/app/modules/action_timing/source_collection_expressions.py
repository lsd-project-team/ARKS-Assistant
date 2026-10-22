"""保存集合表达式在C#求值时点的值，避免后续写入改变已求得的接收者或元素。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO
from app.modules.action_timing.source_index import children
from app.modules.action_timing.source_tasks import CLOCK


def evaluate_location(estimator, node, method, bindings, stack, conditions, background):
    started = bindings.get(CLOCK, ZERO)
    bindings.pop(call_args.return_key(node, method, bindings), None)
    saved_key = call_args.snapshot_key(node, method, bindings) + ":element"
    bindings.pop(saved_key, None)
    receiver = node.child_by_field_name("expression")
    cost = estimator.expression(receiver, method, bindings, stack, conditions, background)
    data = estimator.index.value(receiver, method, bindings)
    listing = node.child_by_field_name("subscript") or next(
        iter(children(node, "bracketed_argument_list")), None
    )
    values = []
    for argument in children(listing, "argument"):
        bindings[CLOCK] = started.plus(cost)
        cost = cost.plus(
            estimator.expression(argument, method, bindings, stack, conditions, background)
        )
        values.append(estimator.index.value(argument, method, bindings))
    place = (data, values[0] if len(values) == 1 else None) if collections.known(data) else None
    if place is not None:
        bindings[saved_key] = place
    bindings[CLOCK] = started
    return cost, place


def read_element(estimator, node, method, bindings, stack, conditions, background):
    cost, place = evaluate_location(
        estimator, node, method, bindings, stack, conditions, background
    )
    bindings[call_args.return_key(node, method, bindings)] = (
        collections.item(*place, bindings) if place is not None else None
    )
    return cost


def initializer_values(estimator, node, method, bindings, stack, conditions, background):
    started, cost, values = bindings.get(CLOCK, ZERO), ZERO, []
    for part in children(node):
        if part.type == "comment":
            continue
        bindings[CLOCK] = started.plus(cost)
        cost = cost.plus(
            estimator.expression(part, method, bindings, stack, conditions, background)
        )
        values.append(estimator.index.value(part, method, bindings))
    bindings[CLOCK] = started
    return cost, tuple(values)


def create_array(estimator, node, method, bindings, stack, conditions, background):
    started = bindings.get(CLOCK, ZERO)
    result_key = call_args.return_key(node, method, bindings)
    bindings.pop(result_key, None)
    # 数组维度先求值，初始化器从左到右保存每个值，而非最后重新投影变量。
    cost = estimator.expression(
        node.child_by_field_name("type"), method, bindings, stack, conditions, background
    )
    initial = node.child_by_field_name("initializer") or next(
        iter(children(node, "initializer_expression")), None
    )
    bindings[CLOCK] = started.plus(cost)
    extra, values = initializer_values(
        estimator, initial, method, bindings, stack, conditions, background
    )
    estimator.allocations += 1
    bindings[f"<allocation:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}>"] = (
        f"collection:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}"
        f":{estimator.allocations}"
    )
    data = collections.created(estimator.index, node, method, bindings)
    if initial is not None:
        data["<items>"], data["<length>"] = values, len(values)
    bindings[result_key] = data
    bindings[CLOCK] = started
    return cost.plus(extra)
