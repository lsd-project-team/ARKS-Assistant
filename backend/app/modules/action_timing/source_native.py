"""识别直接SDK读写；只确认调用存在，不推造通讯或机构完成时间。"""

import re

from app.modules.action_timing.source_flow import ZERO
from app.modules.action_timing.source_index import simple_type, text


def operation(index, node, method):
    function = node.child_by_field_name("function")
    source = re.sub(r"\s+", "", text(function)).removeprefix("global::")
    if re.fullmatch(r"GTN\.mc\.GTN_\w+", source):
        if index.lookup_type("GTN.mc", method) not in index.classes:
            return source
    receiver = function.child_by_field_name("expression") if function else None
    owner = index.infer(receiver, method)
    if owner in index.classes or simple_type(owner) not in {"DsaDrive", "DsaDriveGroup"}:
        return None
    if owner.startswith("ch.etel.edi.dsa.") or any(
        namespace.startswith("ch.etel.edi.dsa.") for namespace in method.unit.namespaces
    ):
        return source
    return None


def handle(estimator, node, method, conditions, background):
    name = operation(estimator.index, node, method)
    if not name:
        return None
    missing = [f"{name} 的设备通信及调用返回时间"]
    if "MappingDownload" in name:
        missing += ["实际补偿文件内容/大小", "驱动下载完成反馈"]
    elif "Stop" in name:
        missing.append("控制器/轴实际停止完成反馈")
    estimator.record(
        "call",
        "直接设备SDK调用",
        node,
        method,
        conditions,
        background,
        expression=text(node),
        milliseconds=None,
        missing_inputs=missing,
        note="已识别此SDK操作；源码没有固定耗时，不能将读取/设置或发出停止指令当作零毫秒完成。",
    )
    return ZERO
