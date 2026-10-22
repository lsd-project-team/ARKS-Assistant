"""直接分析所属项目源码，页面打开即可得到模拟耗时依据。"""

import csv
import hashlib
import io
import threading
from collections import Counter

from app.modules.action_timing.catalog import CATALOG
from app.modules.action_timing.source_catalog import build_catalog
from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_hardware import bind_packages
from app.modules.action_timing.source_index import SourceIndex, description, text
from app.modules.action_timing.source_scope import load_scope

FIRST = {item["class_name"]: item for item in CATALOG}
ENTITY_NAMES = {
    "Carrier": "载具",
    "Transport": "载具",
    "Substrate": "基板",
    "Module": "基岛",
    "BondPosition": "焊点",
}
OPERATION_NAMES = {"Vision": "定位", "Identity": "身份识别", "MeasureHeight": "测高"}
DRY_METHODS = {
    "PickActionNode": "PickActionDryRun",
    "BondActionNode": "BondActionDryRun",
    "UpLookCorrectionActionNode": "UplookActionDryRun",
    "SubstrateCameraCorrectionActionNode": "SubstrateCameraCorrectionActionDryRun",
    "DipFluxActionNode": "DipFluxActionDryRun",
    "AfterBondCheckActionNode": "PostBondActionDryRun",
}
PURE_PREFIXES = (
    "Get",
    "Is",
    "Has",
    "Read",
    "Convert",
    "Check",
    "Find",
    "SetCurrent",
    "Calculate",
    "Edit",
)
WORKFLOWS = {
    "WaferSubSystemTask": {"ChangeTabletManual", "ChangeTabletAuto"},
    "BondTask": {"SendAway", "CloseDispenseCylinder"},
    "DispenseWorkTask": {"GetInputSignal"},
    "Block": {"NextDie"},
}
SCOPE = (
    "ZX2200全部编译方法按调用关系核对：动作节点、任务单轮、换料、初始化、"
    "手动/标定与子动作；依赖工程只作为计算依据，父子动作不相加为整机节拍"
)


def group(path):
    for folder, label in [
        ("DispenseSystem", "S1 点胶"),
        ("BondSystem", "S2 固晶"),
        ("WaferSubSystem", "晶圆与翻转"),
        ("TransportSystem", "输送与上下料"),
    ]:
        if folder in path.split("/"):
            return label
    return "公共动作"


def node_name(info, unit, declaration):
    if info.name in FIRST:
        return FIRST[info.name]["name"]
    # 部分旧注释把Carrier写成基板、把身份写成省份；显示名按节点身份区分。
    for entity, label in ENTITY_NAMES.items():
        for operation, action in OPERATION_NAMES.items():
            suffix = f"{entity}{operation}ActionNode"
            if info.name.endswith(suffix) and info.name[:2] in {"S1", "S2"}:
                return f"{info.name[:2]} {label}{action}"
    return description(unit.raw, declaration) or info.name


def discover(index):
    entries = []
    for info in index.classes.values():
        if not any(unit.role == "business" for unit, _ in info.declarations):
            continue
        if "ActionNode" in info.bases:
            methods = [method for method in info.methods if method.name == "DoWork"]
            dry = [method for method in info.methods if method.name == DRY_METHODS.get(info.name)]
            if methods:
                method = (dry or methods)[0]
                unit, declaration = info.declarations[0]
                name = node_name(info, unit, declaration)
                entries.append(
                    (method, name, "node", "空跑专用方法" if dry else "DoWork 中的 DryCycle 分支")
                )
            else:
                # 空壳节点没有自己的动作实现，不能把基类返回成功当成已执行动作。
                unit, declaration = info.declarations[0]
                entries.append(
                    (
                        None,
                        description(unit.raw, declaration) or info.name,
                        "placeholder",
                        (info, unit, declaration),
                    )
                )
        for method in info.methods:
            is_controller = (
                method.callable_kind in {"method", "constructor"}
                and "/Controllers/" in f"/{method.unit.path}"
                and "public"
                in [text(node) for node in method.node.children if node.type == "modifier"]
            )
            is_workflow = method.name in WORKFLOWS.get(info.name, set())
            if is_workflow or (
                is_controller and not method.name.startswith(PURE_PREFIXES) and method.body
            ):
                label = (
                    description(method.unit.raw, method.node).replace("描述：", "").strip()
                    or method.name
                )
                entries.append(
                    (
                        method,
                        label,
                        "workflow" if is_workflow else "controller",
                        "按 DryCycle 条件展开",
                    )
                )
    return entries


class SourceTiming:
    def __init__(self, workspace):
        self.workspace = workspace
        self.lock = threading.RLock()
        self.cached = None
        self.signature = None
        self.loaded_scope = None

    def _documents(self):
        self.loaded_scope = load_scope(self.workspace)
        return self.loaded_scope.documents

    def report(self):
        with self.lock:
            documents = self._documents()
            signature = self.loaded_scope.revision
            if signature != self.signature:
                index = SourceIndex(documents, self.loaded_scope.declarations)
                index.packages = bind_packages(self.loaded_scope.references)
                self.cached = self._build(index)
                self.signature = signature
            return self.cached

    def _build(self, index):
        rows = []
        entries, coverage = build_catalog(index, discover(index))
        for entry in entries:
            method, name, kind, branch = entry.method, entry.name, entry.kind, entry.branch
            if method is None:
                info, unit, node = branch
                row = {
                    "id": hashlib.sha256(
                        f"placeholder:{info.name}:{unit.path}".encode()
                    ).hexdigest()[:24],
                    "name": name,
                    "class_name": info.name,
                    "method": "无重写实现",
                    "kind": kind,
                    "group": group(unit.path),
                    "branch": "占位节点",
                    "entry": unit.evidence(node),
                    "known_delay_min_ms": None,
                    "known_delay_max_ms": None,
                    "total_ms": None,
                    "formula": "此节点无重写主体，不推算动作耗时",
                    "complete": False,
                    "truncated": False,
                    "stages": [],
                    "parameters": [],
                    "motion_count": 0,
                    "wait_count": 0,
                    "timeout_count": 0,
                }
            else:
                result = Estimator(index).estimate(method)
                row = {
                    "id": hashlib.sha256(method.key.encode()).hexdigest()[:24],
                    "name": name[:120],
                    "class_name": method.owner,
                    "method": method.name,
                    "kind": kind,
                    "group": group(method.unit.path),
                    "branch": branch,
                    "entry": method.unit.evidence(method.node),
                    **result,
                }
            row.update(
                category=entry.category, primary=entry.primary, analysis_unit=entry.analysis_unit
            )
            if entry.mode_note:
                row.update(
                    execution_status="skipped",
                    status_reason=entry.mode_note,
                    complete=False,
                    total_ms=None,
                    known_delay_min_ms=None,
                    known_delay_max_ms=None,
                    formula=entry.mode_note,
                )
            rows.append(row)
        order = {item["class_name"]: n for n, item in enumerate(CATALOG)}
        rows.sort(
            key=lambda row: (
                order.get(row["class_name"], 100),
                row["kind"] != "node",
                row["group"],
                row["class_name"],
                row["method"],
            )
        )
        return {
            "mode": "DryCycle",
            "basis": "source_defaults",
            "source_revision": hashlib.sha256(
                f"trunk-model-v12:{index.revision}:{self.loaded_scope.revision}".encode()
            ).hexdigest(),
            "source_files": len(index.units),
            "source_projects": self.loaded_scope.projects,
            "source_dependencies": self.loaded_scope.references,
            "package_contracts": index.packages,
            "source_coverage": dict(Counter(item["status"] for item in self.loaded_scope.files)),
            "action_coverage": coverage,
            "scope": SCOPE,
            "notes": index.notes,
            "assumptions": [
                "数值取C#源码显式初值，不读取现场配方；无初值的参数保持未知。",
                "以进入动作工作分支为前提；调度跳过和失败/人工处理时间不作为成功动作的固定耗时。",
                "模拟连续工作状态 MachineState=Working；"
                "空跑直接返回、源码抛异常与可执行动作分别标记。",
                "统计配置延时与动作调用关系，不把CPU执行开销估成设备动作时间。",
                "互斥分支分别计算范围；未定循环、信号等待、运动和未解析调用不填零总耗时。",
                "超时上限不计作必耗时；后台Task单独显示；并发轴不能逐项相加。",
                "任务单轮只展开服务循环的一次工作体；线程启动入口与子动作不会叠加为节拍。",
                "Task 模型只模拟源码显式耗时，假设可立即调度；不估算线程调度或CPU耗时。",
                "运动公式保留起点、目标、速度、加减速和驱动单位条件；"
                "未证明单位、平滑及到位稳定时，不编造运动毫秒数。",
            ],
            "rows": rows,
        }

    def summary(self):
        report = self.report()
        return {
            **report,
            "action_coverage": {
                key: value for key, value in report["action_coverage"].items() if key != "methods"
            },
            "rows": [
                {key: value for key, value in row.items() if key not in {"stages", "parameters"}}
                | {"stage_count": len(row["stages"]), "parameter_count": len(row["parameters"])}
                for row in report["rows"]
            ],
        }

    def coverage(self):
        with self.lock:
            report = self.report()
            return {
                "source_revision": report["source_revision"],
                "files": self.loaded_scope.files,
                **report["action_coverage"],
            }

    def detail(self, identifier):
        row = next((row for row in self.report()["rows"] if row["id"] == identifier), None)
        if row is None:
            raise FileNotFoundError("源码动作不存在或源码版本已变化，请刷新列表")
        return row

    def export_csv(self):
        report = self.report()
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(
            [
                "动作",
                "模块",
                "入口",
                "源码配置延时下界ms",
                "源码配置延时上界ms",
                "公式",
                "运动调用",
                "等待调用",
                "源码",
                "行",
                "源码指纹",
                "口径",
            ]
        )
        for row in report["rows"]:
            cells = [
                row["name"],
                row["group"],
                f"{row['class_name']}.{row['method']}",
                row["known_delay_min_ms"],
                row["known_delay_max_ms"],
                row["formula"],
                row["motion_count"],
                row["wait_count"],
                row["entry"]["path"],
                row["entry"]["line"],
                report["source_revision"],
                "源码默认值推算，非现场实测",
            ]
            writer.writerow(
                [
                    "'" + cell
                    if isinstance(cell, str) and cell.lstrip().startswith(("=", "+", "-", "@"))
                    else cell
                    for cell in cells
                ]
            )
        return "\ufeff" + output.getvalue()
