"""同版业务UI封装的派发契约；回调与控件/互斥门禁分开表示。"""

from app.modules.action_timing import source_arguments as arguments
from app.modules.action_timing import source_closures, source_collections, source_delegates
from app.modules.action_timing.source_flow import UNKNOWN, ZERO
from app.modules.action_timing.source_index import children, text
from app.modules.action_timing.source_tasks import (
    CLOCK,
    TaskPlan,
    remember_plan,
    run_delegate,
)

NAMESPACE = "AKRS.ZX2200.Infrastructure.Service"
SOURCE_SHA256 = "a6cc7a8a89a2f09c76d4442246e14a807804fa8f662a474f31597fe512de147f"


def callback(index, node, method):
    function = node.child_by_field_name("function")
    if text(function.child_by_field_name("name")).split("<", 1)[0] != "UIActionAsync":
        return None
    owner = index.lookup_type("ControlService", method)
    info = index.classes.get(owner)
    if not info or info.namespace != NAMESPACE:
        return None
    if not any(unit.version == SOURCE_SHA256 for unit, _ in info.declarations):
        return None  # 封装源码改变后必须重新核对；不按同名方法直接套用契约。
    receiver = text(function.child_by_field_name("expression"))
    static = receiver in {"ControlService", f"{NAMESPACE}.ControlService"}
    if not static and NAMESPACE not in method.unit.namespaces:
        return None
    target = index.resolve(node, method)
    if target is not None and target.owner != info.name:
        return None
    args = children(node.child_by_field_name("arguments"), "argument")
    named = next((arg for arg in args if arguments.argument_name(arg) == "action"), None)
    position = 1 if static else 0
    return named if named is not None else args[position] if len(args) > position else None


def callback_arguments(index, node, action, method, bindings):
    args = children(node.child_by_field_name("arguments"), "argument")
    position = args.index(action)
    values = arguments.values(index, node, method, bindings)
    supplied = {}
    kinds = {}
    for i, arg in enumerate(args):
        name = arguments.argument_name(arg)
        if name in {"controlObject", "action", "controls"}:
            continue
        if name is None and i <= position + 1:
            continue  # 紧随委托的可选参数是关联控件，不是回调实参。
        if name == "objects":
            size = source_collections.length(values[i], bindings)
            if size is None or size > 256:
                return None
            return (
                tuple(source_collections.item(values[i], n, bindings) for n in range(size)),
                tuple(source_collections.item_type(values[i], n, bindings) for n in range(size)),
            )
        if name == "param":
            slot = 0
        elif name and name.startswith("param") and name[5:].isdigit():
            slot = int(name[5:]) - 1
        else:
            slot = i - position - 2
        if slot >= 0:
            supplied[slot] = values[i]
            kinds[slot] = index.infer(arg, method)
    callback_node = source_delegates.unwrap(index, action, method, bindings)
    arity = (
        len(source_closures.parameters(callback_node))
        if getattr(callback_node, "type", "")
        in {"lambda_expression", "anonymous_method_expression"}
        else max(supplied, default=-1) + 1
    )
    return tuple(supplied.get(i) for i in range(arity)), tuple(
        kinds.get(i, "") for i in range(arity)
    )


def handle(estimator, node, method, bindings, stack, conditions, background):
    action = callback(estimator.index, node, method)
    if action is None:
        return None
    condition = "控件为Control/BarItem、互斥允许且用户操作实际派发"
    supplied = callback_arguments(estimator.index, node, action, method, bindings)
    if supplied is None:
        estimator.record(
            "unresolved",
            "控件回调参数数组未绑定",
            node,
            method,
            conditions,
            background,
            missing_inputs=["UIActionAsync传入回调的参数数组内容、数量和类型"],
        )
        return UNKNOWN
    values, kinds = supplied
    plan = run_delegate(
        estimator,
        action,
        method,
        bindings,
        stack,
        (*conditions, condition),
        background,
        waiting=False,
        argument_values=values,
        argument_types=kinds,
    )
    estimator.record(
        "wait",
        "控件操作派发/互斥条件",
        node,
        method,
        conditions,
        background,
        milliseconds=None,
        missing_inputs=["实际触发控件类型", "操作互斥门禁/队列释放时间"],
        note="回调内已知等待另列为条件后台组成；控件无效或已有操作时可以直接返回。",
    )
    # 分支是否派发及排队时间未定，不能将回调的已知等待强加给所有调用。
    remember_plan(
        node,
        method,
        bindings,
        TaskPlan(
            bindings.get(CLOCK, ZERO),
            UNKNOWN,
            stage_ids=plan.stage_ids,
        ),
    )
    return ZERO
