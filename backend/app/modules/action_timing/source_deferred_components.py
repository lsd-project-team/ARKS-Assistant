"""任务回调的可算等待组成；不改变外层动作的执行结果或同步总时长。"""

from app.modules.action_timing import source_components, source_delegates
from app.modules.action_timing.source_entry_callbacks import callback_method
from app.modules.action_timing.source_index import children, text, walk


def task_waits(index, method):
    cache = index.__dict__.setdefault("deferred_wait_components", {})
    if method.key in cache:
        return cache[method.key]
    result = []
    for call in walk(method.body):
        if call.type != "invocation_expression":
            continue
        function = text(call.child_by_field_name("function")).removeprefix("global::")
        function = function.removeprefix("System.Threading.Tasks.")
        if function not in {"Task.Run", "Task.Factory.StartNew"}:
            continue
        if index.lookup_type("Task", method) in index.classes or index.resolve(call, method):
            continue
        conditions, _, _, _, possible = source_components.call_context(call, method)
        if not possible:
            continue
        args = children(call.child_by_field_name("arguments"), "argument")
        callback = source_delegates.unwrap(index, args[0], method) if args else None
        if callback is None or callback.type not in {
            "lambda_expression",
            "anonymous_method_expression",
        }:
            continue
        activation = [f"{function}的回调实际启动"]
        parent = call.parent
        while parent is not None and parent != method.node:
            if parent.type in {"lambda_expression", "anonymous_method_expression"}:
                activation.append("外层保存的回调实际被调用")
                break
            parent = parent.parent
        target = callback_method(callback, method, f"<task:{callback.start_byte}>")
        for fact in source_components.literal_waits(index, target):
            # 单次回调的组成可以保留；绝不按创建点数或展开记录数累加给启动者。
            result.append(
                {
                    **fact,
                    "conditions": list(
                        dict.fromkeys([*conditions, *activation, *fact["conditions"]])
                    ),
                    "deferred": True,
                    "note": "单次任务回调满足条件并正常执行时的等待组成；"
                    "触发次数、完成时刻和是否被外层等待另行核对，不与汇总重复相加。",
                }
            )
    cache[method.key] = result
    return result
