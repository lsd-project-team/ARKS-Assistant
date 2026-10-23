"""保存集合表达式在C#求值时点的值，避免后续写入改变已求得的接收者或元素。"""

from app.modules.action_timing import source_arguments as call_args
from app.modules.action_timing import source_array_values as arrays
from app.modules.action_timing import source_collections as collections
from app.modules.action_timing import source_state as state
from app.modules.action_timing.source_flow import ZERO
from app.modules.action_timing.source_index import children, value_children
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
    place = (
        (data, arrays.offset(data, values, collections.length(data, bindings)))
        if collections.known(data)
        else None
    )
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


def initializer_values(
    estimator, node, method, bindings, stack, conditions, background, parts=None
):
    started, cost, values = bindings.get(CLOCK, ZERO), ZERO, []
    for part in value_children(node) if parts is None else parts:
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
    cost, dimensions = ZERO, []
    for expression in arrays.dimensions(node):
        bindings[CLOCK] = started.plus(cost)
        cost = cost.plus(
            estimator.expression(expression, method, bindings, stack, conditions, background)
        )
        dimensions.append(estimator.index.value(expression, method, bindings))
    shape, leaves = arrays.shape(estimator.index, node, method, bindings, tuple(dimensions))
    initial = arrays.initial(node)
    bindings[CLOCK] = started.plus(cost)
    extra, values = initializer_values(
        estimator, initial, method, bindings, stack, conditions, background, parts=leaves
    )
    estimator.allocations += 1
    bindings[f"<allocation:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}>"] = (
        f"collection:{bindings.get(state.FRAME)}:{method.unit.path}:{node.start_byte}"
        f":{estimator.allocations}"
    )
    data = collections.created(estimator.index, node, method, bindings)
    data["<shape>"], data["<length>"] = shape, arrays.length(shape)
    if initial is not None and shape is not None:
        data["<items>"] = values
        if data.get("<element_type>") in {"object", "System.Object"}:
            for position, part in enumerate(leaves[:256]):
                bindings[collections.key(data, f"type:{position}")] = collections.raw_type(
                    estimator.index, part, method
                ) or estimator.index.infer(part, method)
    bindings[result_key] = data
    bindings[CLOCK] = started
    return cost.plus(extra)
