"""全工程动作目录与覆盖账本；包内方法作为依据，不冒充设备工序。"""

import re
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, replace

from app.modules.action_timing import source_apm, source_dispatch, source_dynamic, source_parallel
from app.modules.action_timing import source_delegates as delegates
from app.modules.action_timing.source_hardware import hardware_operation
from app.modules.action_timing.source_index import children, description, text, walk

TIMED = re.compile(
    r"Sleep|Delay|Move|Interpolation|Wait|GoHome|SearchBelt|MapBelt|"
    r"Trigger|Grab|Snap|Capture|Vacuum|Cylinder|Clamp|Release|"
    r"SetOutputValue|GetInputValue|GetOutputValue|CheckStateForNums|"
    r"ServoOn|ServoOff|SetExposureTime",
    re.I,
)
COLLECTION_OPERATIONS = {"Remove", "RemoveAt", "RemoveAll", "RemoveRange", "MoveNext"}


def timed_operation(name):
    return name not in COLLECTION_OPERATIONS and TIMED.search(name) is not None


OPERATIONS = re.compile(r"^(?:Init|Reset|Home|Start|Stop|Open|Close|Calib|Execute|DoWork|Dowork)")
TASK_NAMES = {
    "BondTask": "固晶单轮流程",
    "DispenseWorkTask": "点胶单轮流程",
    "FlipTask": "翻转单轮流程",
    "WaferSubSystemTask": "晶圆单轮流程",
    "SlideFluxerTask": "刮胶单轮流程",
    "LoaderTask": "上料任务",
    "UnloaderTask": "下料任务",
}


@dataclass
class ActionEntry:
    method: object
    name: str
    kind: str
    branch: object
    category: str = "子动作"
    primary: bool = False
    analysis_unit: str = "method"
    mode_note: str = ""


def category(method):
    path = method.unit.path
    if "/Experiment/" in path or "Test" in method.owner:
        return "测试动作"
    if "/CalibSystem/" in path:
        return "标定动作"
    if method.name.startswith(("Init", "Reset", "GoHome", "Home", ".ctor", ".cctor")):
        return "初始化与复位"
    if any(part in path for part in ("/Controls/", "/Views/", "/Forms/")):
        return "界面与手动操作"
    if "/Tasks/" in path:
        return "任务流程"
    return "子动作"


def service_loops(method):
    """仅拆服务循环的单轮，内部重试/信号轮询仍保留原循环语义。"""
    if "/Tasks/" not in method.unit.path or method.name not in {
        "DoWork",
        "Dowork",
        "Start",
        "StartDryRun",
    }:
        return []
    if method.owner in {"LoaderTask", "UnloaderTask"} and method.name == "Start":
        # 这两个入口在启动委托之前即跳过 DryCycle，委托体不是可执行空跑动作。
        return []
    found = []
    for node in walk(method.body):
        if node.type != "while_statement":
            continue
        condition = text(node.child_by_field_name("condition"))
        if not re.search(r"WaitStart\(|IsWorking\(|^true$", condition):
            continue
        parent = node.parent
        nested = False
        while parent is not None and parent != method.body:
            if parent.type in {"while_statement", "for_statement", "do_statement"}:
                nested = True
                break
            parent = parent.parent
        if not nested:
            found.append(node)
    return found


def cycle_name(method, loop, number):
    if method.name in {"DoWork", "Dowork"} and method.owner in TASK_NAMES:
        return TASK_NAMES[method.owner]
    scope = loop.parent
    while scope.parent is not None and scope.type not in {
        "lambda_expression",
        "method_declaration",
    }:
        scope = scope.parent
    thread = re.search(r'SetCurrentThreadName\("([^"]+)"\)', text(scope))
    if thread:
        label = thread[1].replace("线程", "")
        return f"{label}（单轮）"
    label = TASK_NAMES.get(method.owner, description(method.unit.raw, method.node) or method.name)
    return label if number == 1 else f"{label} {number}"


def build_catalog(index, legacy):
    methods = {method.key: method for info in index.classes.values() for method in info.methods}
    callers = defaultdict(set)
    edges = defaultdict(set)
    direct = set()

    def constructor_targets(owner, seen=None):
        seen = set() if seen is None else seen
        if owner in seen or owner not in index.classes:
            return []
        seen.add(owner)
        info = index.classes[owner]
        return [
            *index.by_method.get((owner, ".ctor"), []),
            *(method for method in info.initializers if not method.is_static),
            *(
                method
                for base in index.base_types(owner)
                for method in constructor_targets(base, seen)
            ),
        ]

    for method in methods.values():
        roots = [method.body]
        if method.callable_kind == "constructor":
            roots.extend(children(method.node, "constructor_initializer"))
            targets = (
                [part for part in index.classes[method.owner].initializers if part.is_static]
                if method.is_static
                else constructor_targets(method.owner)
            )
            for target in targets:
                if target.key != method.key:
                    edges[method.key].add(target.key)
                    callers[target.key].add(method.key)
        for call in (part for root in roots for part in walk(root)):
            function = text(call.child_by_field_name("function"))
            task = call.type == "invocation_expression" and function.removeprefix(
                "System.Threading.Tasks."
            ) in {"Task.Run", "Task.Factory.StartNew"}
            creation = call.type == "object_creation_expression" and text(
                call.child_by_field_name("type")
            ).split("<", 1)[0] in {"Task", "System.Threading.Tasks.Task"}
            if task or creation:
                arguments = children(call.child_by_field_name("arguments"), "argument")
                delegate = delegates.unwrap(index, arguments[0], method) if arguments else None
                target = delegates.method_group(index, delegate, method)
                if target:
                    edges[method.key].add(target.key)
                    callers[target.key].add(method.key)
            if call.type == "object_creation_expression":
                owner = index.lookup_type(text(call.child_by_field_name("type")), method)
                for target in constructor_targets(owner):
                    edges[method.key].add(target.key)
                    callers[target.key].add(method.key)
                continue
            if call.type == "assignment_expression":
                left = call.child_by_field_name("left")
                owner = None
                ancestor = call.parent
                if ancestor and ancestor.type == "initializer_expression":
                    creation = ancestor.parent
                    if creation and creation.type == "object_creation_expression":
                        owner = index.lookup_type(
                            text(creation.child_by_field_name("type")), method
                        )
                target = index.accessor(left, method, "set", owner)
                if target:
                    edges[method.key].add(target.key)
                    callers[target.key].add(method.key)
            if call.type in {"identifier", "member_access_expression"}:
                parent = call.parent
                selector = (
                    parent
                    and parent.type == "member_access_expression"
                    and parent.child_by_field_name("name") == call
                )
                assigned = (
                    parent
                    and parent.type == "assignment_expression"
                    and parent.child_by_field_name("left") == call
                    and text(parent.child_by_field_name("operator")) == "="
                )
                target = None if selector or assigned else index.accessor(call, method, "get")
                if target:
                    edges[method.key].add(target.key)
                    callers[target.key].add(method.key)
            if call.type != "invocation_expression":
                continue
            function = text(call.child_by_field_name("function"))
            target = index.resolve(call, method)
            if (
                timed_operation(function.split(".")[-1])
                or hardware_operation(index, call, method)
                or delegates.typed_invocation(index, call, method)
                or source_dynamic.operation(index, call, method)
                or source_apm.operation(index, call, method)
                or source_dispatch.receiver_kind(index, call, method)
                or source_parallel.operation(index, call, method)
            ) and not (target and target.body):
                direct.add(method.key)
            if target:
                edges[method.key].add(target.key)
                callers[target.key].add(method.key)
    timed = set(direct)
    queue = deque(direct)
    while queue:
        for caller in callers[queue.popleft()]:
            if caller not in timed:
                timed.add(caller)
                queue.append(caller)

    entries = []
    represented = {}
    for method, name, kind, branch in legacy:
        entry = ActionEntry(
            method,
            name,
            kind,
            branch,
            "动作节点" if kind == "node" else category(method) if method else "子动作",
            kind == "node",
        )
        entries.append(entry)
        if method:
            represented[method.key] = entry
            # 专用空跑方法已代表同一节点，不重复列出 DoWork 包装。
            if kind == "node":
                for wrapper in index.by_method[(method.owner, "DoWork")]:
                    represented[wrapper.key] = entry

    for method in methods.values():
        if method.unit.role != "business":
            continue
        public = any(text(mod) == "public" for mod in children(method.node, "modifier"))
        task = method.owner in TASK_NAMES and method.name in {"DoWork", "Dowork", "Start"}
        extra = method.key in timed or (public and OPERATIONS.search(method.name)) or task
        if extra and method.key not in represented:
            label = description(method.unit.raw, method.node).replace("描述：", "").strip()
            owner_name = index.classes[method.owner].short_name
            if method.callable_kind == "constructor":
                label = label or f"{owner_name} 初始化"
            elif method.callable_kind == "initializer":
                label = f"{owner_name} 字段初始化：{method.name.removeprefix('.initialize_')}"
            elif method.callable_kind.startswith("property_"):
                operation = "读取" if method.callable_kind == "property_get" else "设置"
                label = f"{operation} {method.name.split('_', 1)[-1]}"
            entry = ActionEntry(
                method,
                label or method.name,
                "workflow",
                "按 DryCycle 条件展开",
                category(method),
                task and method.name != "Start",
            )
            if method.owner in {"LoaderTask", "UnloaderTask"} and method.name == "Start":
                entry.name = TASK_NAMES[method.owner]
                entry.primary = True
            if method.owner == "TransportTask" and method.name == "Start":
                entry.mode_note = "DryCycle 使用 StartDryRun，此入口用于正常生产"
            entries.append(entry)
            represented[method.key] = entry
        if method.key not in represented:
            continue
        original = represented[method.key]
        for number, loop in enumerate(service_loops(method), 1):
            cycle = replace(method, body_override=loop.child_by_field_name("body"))
            entry = ActionEntry(
                cycle,
                cycle_name(method, loop, number),
                "workflow",
                "服务循环单轮，不含线程启动和下一轮等待",
                "任务单轮",
                original.mode_note == "" and "/Tasks/" in method.unit.path,
                "single_cycle",
                original.mode_note,
            )
            entries.append(entry)
            original.primary = False
    # 每个编译方法都有去向；“未发现耗时路径”不等于方法不是业务动作。
    ledger = []
    for key, method in methods.items():
        status = (
            "dependency"
            if method.unit.role != "business"
            else ("catalogued" if key in represented else "no_recognized_timing_path")
        )
        ledger.append(
            {
                "key": key,
                "path": method.unit.path,
                "line": method.node.start_point[0] + 1,
                "method": f"{method.owner}.{method.name}",
                "status": status,
                "category": category(method),
                "direct_timing": key in direct,
                "callable_kind": method.callable_kind,
                "timed_callees": len(edges[key] & timed),
            }
        )
    return entries, {
        "methods": ledger,
        "counts": dict(Counter(row["status"] for row in ledger)),
        "direct_timing_methods": len(direct),
        "uncatalogued_timing_methods": sum(
            key in timed and method.unit.role == "business" and key not in represented
            for key, method in methods.items()
        ),
    }
