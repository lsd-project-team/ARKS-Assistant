"""只传播已经证明没有正常返回的表达式；未执行的lambda正文不参与判断。"""

from app.modules.action_timing.source_arguments import return_key
from app.modules.action_timing.source_index import children


def expressions(node):
    pending = [node] if node is not None else []
    while pending:
        part = pending.pop()
        if part.type in {"lambda_expression", "anonymous_method_expression"}:
            continue
        yield part
        pending.extend(children(part))


def failed(node, method, bindings):
    return any(
        bindings.get(return_key(part, method, bindings) + ":normal") is False
        for part in expressions(node)
    )


def clear(node, method, bindings):
    # 重试中本轮可能短路跳过一个上轮失败的子调用，旧标志必须在求值前清除。
    for part in expressions(node):
        bindings.pop(return_key(part, method, bindings) + ":normal", None)
