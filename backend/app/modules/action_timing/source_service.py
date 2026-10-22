"""直接分析所属项目源码，页面打开即可得到模拟耗时依据。"""

import csv
import hashlib
import io
import threading

from app.modules.action_timing.catalog import CATALOG
from app.modules.action_timing.source_estimator import Estimator
from app.modules.action_timing.source_index import SourceIndex, description, text

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
    "ActionNode节点（含测试/占位）、Controllers公开执行入口及换料/放行子流程；"
    "控制器子动作单独列出，不相加为整机节拍"
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
            is_controller = "/Controllers/" in f"/{method.unit.path}" and "public" in [
                text(node) for node in method.node.children if node.type == "modifier"
            ]
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

    def _documents(self):
        documents, total = [], 0
        files = sorted(self.workspace.files())
        projects = [
            self.workspace.relative(path) for path in files if path.name == "AKRS.ZX2200.csproj"
        ]
        preferred = [
            "AKRS.ZX2200.csproj",
            "AKRS.ZX2200/AKRS.ZX2200.csproj",
            "trunk/AKRS.ZX2200/AKRS.ZX2200.csproj",
        ]
        project = next((path for path in preferred if path in projects), None)
        if project is None and projects:
            primary = [
                path
                for path in projects
                if not path.startswith("@sources/") and "output" not in path.split("/")
            ]
            candidates = primary or projects
            if len(candidates) != 1:
                raise ValueError("关联了多份ZX2200源码，请在单一源码版本所属项目查看，避免混算")
            project = candidates[0]
        prefix = project.rsplit("/", 1)[0] + "/" if project and "/" in project else ""
        for path in files:
            relative = self.workspace.relative(path)
            if project is not None and not relative.startswith(prefix):
                continue
            if (
                project is not None
                and not project.startswith("@sources/")
                and relative.startswith("@sources/")
            ):
                continue
            parts = relative.split("/")
            if path.suffix.lower() != ".cs" or any(
                part in {"Controls", "Forms", "CalibSystem", "Test", "Tests"} for part in parts
            ):
                continue
            if path.name.lower().endswith((".designer.cs", ".g.cs")) or "Experiment" in parts:
                continue
            # 同一解决方案的其他工程不是ZX2200生产动作；不跨项目猜测设备SDK实现。
            projects = [part for part in parts if part.startswith("AKRS.")]
            if projects and "AKRS.ZX2200" not in projects:
                continue
            document = self.workspace.read(relative)
            total += len(document["content"].encode("utf-8"))
            if len(documents) >= 4000 or total > 80_000_000:
                raise ValueError("源码范围超过分析上限，请选择ZX2200源码目录")
            documents.append(document)
        return documents

    def report(self):
        with self.lock:
            documents = self._documents()
            signature = tuple((item["path"], item["version"]) for item in documents)
            if signature != self.signature:
                self.cached = self._build(SourceIndex(documents))
                self.signature = signature
            return self.cached

    def _build(self, index):
        rows = []
        for method, name, kind, branch in discover(index):
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
            "source_revision": index.revision,
            "source_files": len(index.units),
            "scope": SCOPE,
            "notes": index.notes,
            "assumptions": [
                "数值取C#源码显式初值，不读取现场配方；无初值的参数保持未知。",
                "以进入动作工作分支为前提；调度跳过和失败/人工处理时间不作为成功动作的固定耗时。",
                "统计配置延时与动作调用关系，不把CPU执行开销估成设备动作时间。",
                "互斥分支分别计算范围；未定循环、信号等待、运动和未解析调用不填零总耗时。",
                "超时上限不计作必耗时；后台Task单独显示；并发轴不能逐项相加。",
            ],
            "rows": rows,
        }

    def summary(self):
        report = self.report()
        return {
            **report,
            "rows": [
                {key: value for key, value in row.items() if key not in {"stages", "parameters"}}
                | {"stage_count": len(row["stages"]), "parameter_count": len(row["parameters"])}
                for row in report["rows"]
            ],
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
