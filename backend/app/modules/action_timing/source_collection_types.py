"""框架集合返回类型与按精确程序集绑定的外部控件列表类型。"""

from app.modules.action_timing.source_index import children, simple_type, text

INFRASTRUCTURE = "AKRS.Galaxy2.Infrastructure"
INFRASTRUCTURE_SHA256 = "f75452133ba809255061210eafc861b576c0fe8b553a983575934fe3d19892eb"
# 静态元数据/原IL核对：MVID 44b31760-0343-4ed2-b0a1-c3f9976b6b63，
# GetChildControls两个重载为0x06000128/0x06000129；只恢复返回类型，不绑定运行数量。
CONTROL_SERVICE = "AKRS.Galaxy2.Infrastructure.ControlServices.ControlOperationService"


def declared_type(index, kind, context, unit):
    """调用文件无需using返回类型；List的归属以声明文件为准。"""
    for name in ("List", "IEnumerable", "IList", "ICollection"):
        if kind.startswith(name + "<") and framework_type(
            index, kind, context, name, "System.Collections.Generic", unit=unit
        ):
            return "System.Collections.Generic." + kind
    return kind


def framework_type(index, kind, method, name, namespace, unit=None):
    unit = unit or method.unit
    return (
        kind.split("<", 1)[0].split(".")[-1] == name
        and index.lookup_type(kind, method, unit=unit) not in index.classes
        and (kind.startswith(namespace + ".") or namespace in unit.namespaces)
    )


def parts(node):
    function = node.child_by_field_name("function")
    name = function.child_by_field_name("name") if function is not None else None
    return function.child_by_field_name("expression"), text(name).split("<", 1)[0], name


def linq(index, node, method):
    receiver, _, _ = parts(node)
    return not index.has_source_call(node, method) and (
        text(receiver) == "System.Linq.Enumerable"
        or (
            "System.Linq" in method.unit.namespaces
            and index.lookup_type(text(receiver), method) not in index.classes
        )
    )


def control_receiver(index, receiver, method):
    from app.modules.action_timing.source_dispatch import CONTROL_TYPES

    pending, seen = [(index.infer(receiver, method), method.unit)], set()
    while pending:
        owner, unit = pending.pop()
        if (owner, unit.path) in seen:
            continue
        seen.add((owner, unit.path))
        info = index.classes.get(owner)
        if info is not None:
            pending.extend(
                (base, u) for base in index.base_types(owner) for u, _ in info.declarations
            )
        elif any(
            owner == kind
            or (owner == simple_type(kind) and kind.rsplit(".", 1)[0] in unit.namespaces)
            for kind in CONTROL_TYPES
        ):
            return True
    return False


def control_result(index, node, method):
    receiver, name, member = parts(node)
    bound = getattr(index, "packages", {}).get(INFRASTRUCTURE, {})
    if (
        name != "GetChildControls"
        or not bound.get("verified")
        or bound.get("sha256") != INFRASTRUCTURE_SHA256
    ):
        return ""
    namespace = CONTROL_SERVICE.rsplit(".", 1)[0]
    static = text(receiver) in {CONTROL_SERVICE, "ControlOperationService"}
    if index.lookup_type(text(receiver), method) in index.classes or index.has_source_call(
        node, method
    ):
        return ""
    if not (text(receiver) == CONTROL_SERVICE or namespace in method.unit.namespaces):
        return ""
    if not static and (
        not control_receiver(index, receiver, method)
        or index.member_type(index.infer(receiver, method), name)
    ):
        return ""
    arguments = children(node.child_by_field_name("arguments"), "argument")
    if len(arguments) != (1 if static else 0):
        return ""
    type_list = next(iter(children(member, "type_argument_list")), None)
    kinds = children(type_list)
    if type_list is not None and len(kinds) != 1:
        return ""
    element = text(kinds[0]) if kinds else "System.Windows.Forms.Control"
    return f"System.Collections.Generic.List<{element}>"


def result_type(index, node, method, seen):
    from app.modules.action_timing import source_collections as collections
    from app.modules.action_timing.source_arguments import arguments
    from app.modules.action_timing.source_array_values import element

    receiver, name, _ = parts(node)
    if index.has_source_call(node, method):
        return ""
    control = control_result(index, node, method)
    if control:
        return control
    if name == "FindAll":
        kind = collections.raw_type(index, receiver, method, seen)
        if framework_type(index, kind, method, "List", "System.Collections.Generic"):
            return f"System.Collections.Generic.List<{element(kind)}>"
    if name in {"Where", "Select", "ToList", "ToArray"} and linq(index, node, method):
        args = arguments(node)
        static = text(receiver) in {"Enumerable", "System.Linq.Enumerable"}
        source = args[0] if static and args else receiver
        kind = collections.raw_type(index, source, method, seen)
        item_type = element(kind) or "var"
        if name == "Select" and args:
            from app.modules.action_timing.source_index import value_children
            from app.modules.action_timing.source_queries import selected_type

            callback = value_children(args[-1])
            item_type = selected_type(index, callback[-1] if callback else None, method, item_type)
        if name == "ToArray":
            return item_type + "[]"
        container = "List" if name == "ToList" else "IEnumerable"
        return f"System.Collections.Generic.{container}<{item_type}>"
    return ""
