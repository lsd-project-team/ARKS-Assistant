"""按程序集指纹绑定已静态核实的包契约；未知配置保持参数化。"""

import json
import math
from pathlib import Path

from app.modules.action_timing.source_flow import UNKNOWN, ZERO, Cost
from app.modules.action_timing.source_index import children, simple_type, text

CONTRACT_ROOT = Path(__file__).with_name("contracts")
HARDWARE = json.loads((CONTRACT_ROOT / "logic-hardware.json").read_text(encoding="utf-8"))
DRIVE = json.loads((CONTRACT_ROOT / "drive.json").read_text(encoding="utf-8"))
ALIASES = {"System.Boolean": "bool", "System.Double": "double", "System.Int32": "int"}


def bind_packages(references):
    hashes = {}
    for item in references:
        if item["kind"] == "assembly" and item.get("sha256"):
            hashes.setdefault(item["name"], set()).add(item["sha256"])
    return {
        name: {
            "sha256": next(iter(hashes[name])) if len(hashes.get(name, set())) == 1 else None,
            "verified": hashes.get(name) == {expected},
        }
        for name, expected in {
            "AKRS.Galaxy2.LogicHardware": HARDWARE["artifact"]["sha256"],
            "AKRS.Galaxy2.Drive": DRIVE["artifact_bindings"]["drive"]["sha256"],
        }.items()
    }


def contract_for(index, node, method):
    bound = getattr(index, "packages", {}).get("AKRS.Galaxy2.LogicHardware", {})
    if not bound.get("verified"):
        return None
    function = node.child_by_field_name("function")
    receiver = function.child_by_field_name("expression")
    owner = index.infer(receiver, method)
    if owner in index.classes:
        return None
    name = text(function.child_by_field_name("name"))
    args = children(node.child_by_field_name("arguments"), "argument")
    candidates = []
    for contract in HARDWARE["contracts"]:
        full_type = contract["declaringType"]
        if contract["method"] != name or simple_type(full_type) != simple_type(owner):
            continue
        namespace = full_type.rsplit(".", 1)[0]
        if owner != full_type and f"using {namespace};" not in method.unit.raw.decode("utf-8"):
            continue
        params = contract["parameterTypes"]
        optional = len(contract.get("optionalDefaults", {}))
        if not len(params) - optional <= len(args) <= len(params):
            continue
        score = 0
        for arg, parameter in zip(args, params, strict=False):
            parts = children(arg)
            if any(child.type in {"name_colon", "name_equals"} for child in parts):
                break
            actual = simple_type(index.infer(arg, method))
            parameter = parameter.rstrip("&")
            expected = simple_type(ALIASES.get(parameter, parameter))
            if actual == expected:
                score += 2
            elif actual == "int" and expected == "double":
                score += 1
            elif actual and actual not in {"", expected}:
                break
        else:
            candidates.append((score, contract))
    if not candidates:
        return None
    score = max(item[0] for item in candidates)
    matches = [contract for rank, contract in candidates if rank == score]
    return matches[0] if len(matches) == 1 else None


def numeric(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def motion_model(contract, expressions, values, receiver):
    """给出可代入的运动参数和公式，不把跨驱动未证明的时间单位转换成毫秒。"""
    relative = "Relative" in contract["method"]
    first = values[0] if values else None
    move_para = first if isinstance(first, dict) else {}
    target = move_para.get("TargetPosition", first)
    distance = abs(target) if relative and numeric(target) else None
    velocity_index = 1 if relative else 2
    velocity = move_para.get(
        "Vel", values[velocity_index] if len(values) > velocity_index else None
    )
    behavior = contract["behavior"]
    return {
        "kind": "relative" if relative else "absolute",
        "distance": distance,
        "target": target
        if numeric(target)
        else expressions[0]
        if expressions
        else "MovePara.TargetPosition",
        "velocity": velocity if numeric(velocity) and velocity >= 0 else None,
        "velocity_expression": expressions[velocity_index]
        if len(expressions) > velocity_index
        else f"{receiver}.AxisMovePara.AbsoluteMoveSpeed",
        "acceleration_expression": f"{receiver}.AxisMovePara.ACC",
        "deceleration_expression": f"{receiver}.AxisMovePara.DEC",
        "acceleration": move_para.get("Acc"),
        "deceleration": move_para.get("Dec"),
        "jerk": move_para.get("Jerk"),
        "start_position": None,
        "source_fixed_wait_ms": behavior.get("fixedSleepMs", 0),
        "time_unit": "unproven",
        "duration_ms": None,
        "formula": "d=|目标-起点|；d=0时t=0；vp=min(v,√(2d/(1/a+1/b)))；"
        "t=vp/a+vp/b+max(0,d-vp²/(2a)-vp²/(2b))/vp",
        "conditions": "仅适用于v、a、b>0、已确认单位、零起终速且无平滑的梯形/三角速度模型；"
        "Jerk、CamAxis、插补和到位稳定需按具体驱动处理",
        "completion": behavior.get("composition", "发送后按精确重载的到位模式等待"),
        "unresolved": [
            "实际起点/目标与保存的轴配置",
            "驱动时间单位与速度曲线",
            "初始化门禁、实际派生类型和到位稳定时间",
        ],
    }


def hardware_call(estimator, node, method, bindings, conditions, background):
    contract = contract_for(estimator.index, node, method)
    if contract is None:
        return None
    behavior = contract["behavior"]
    owner = simple_type(contract["declaringType"])
    name = contract["method"]
    args = children(node.child_by_field_name("arguments"), "argument")
    expressions = [text(arg) for arg in args]
    values = [estimator.index.value(arg, method, bindings) for arg in args]
    evidence = {
        key: contract[key] for key in ("symbol", "publicToken", "bodyToken", "bodyIlSha256")
    }
    evidence["artifact_sha256"] = HARDWARE["artifact"]["sha256"]
    if behavior.get("doesNotStartMotion"):
        estimator.record(
            "call",
            "当前包的此方法没有动作实现",
            node,
            method,
            conditions,
            background,
            contract=evidence,
            resolved=True,
            note="已核实方法体仅返回，没有发出运动指令；不能当作同步轴已完成",
        )
        return ZERO
    if owner in {"Axis", "CamAxis", "MotionService"}:
        moving = "Move" in name and "Wait" not in name
        note = "false 参数只控制额外位置校验；到位等待由 AccuracyMode 决定。"
        if owner == "MotionService":
            note = "多轴命令先发出，再等待完成边界；名称 Asyn 的等待仍会阻塞调用者。"
        if behavior.get("fixedSleepOverlapsStartedMotion"):
            note += "包内固定等待与已发出的运动重叠，不能再加一遍完整运动时间。"
        estimator.record(
            "motion" if moving else "wait",
            "包内运动/到位契约",
            node,
            method,
            conditions,
            background,
            milliseconds=None,
            arguments=expressions,
            argument_values=values,
            contract=evidence,
            note=note,
            motion_model=motion_model(
                contract,
                expressions,
                values,
                text(node.child_by_field_name("function").child_by_field_name("expression")),
            ),
        )
        return ZERO
    if name == "CheckStateForNums" and owner in {"Sensor", "Electric"}:
        count = values[1] if len(values) > 1 else 1
        interval = values[2] if len(values) > 2 else 80
        bound = (
            max(count - 1, 0) * max(interval, 30) if numeric(count) and numeric(interval) else None
        )
        estimator.record(
            "wait",
            "连续检测：首读不符立即返回，成功读之间才延时",
            node,
            method,
            conditions,
            background,
            contract=evidence,
            milliseconds=None,
            note=f"成功路径显式等待 {bound:g} ms；IO 读取时间未定"
            if bound is not None
            else "检测次数/间隔未知；间隔至少30 ms",
        )
        return Cost(0, bound)
    if name == "WaitSignal" and owner == "Sensor":
        estimator.record(
            "wait",
            "传感器条件等待",
            node,
            method,
            conditions,
            background,
            contract=evidence,
            milliseconds=None,
            note="先检测，未满足时按80 ms轮询；timeout是失败保护，可提前完成",
        )
        if len(values) > 1 and numeric(values[1]) and values[1] >= 0:
            estimator.record(
                "timeout",
                "传感器等待超时保护，不作固定耗时",
                node,
                method,
                conditions,
                background,
                milliseconds=values[1],
            )
        return UNKNOWN
    estimator.record(
        "call",
        "包内输出/相机调用",
        node,
        method,
        conditions,
        background,
        contract=evidence,
        milliseconds=None,
        note="只设置参数/输出不代表机构或曝光完成；相机按触发、缓存和重试分支等待，"
        "不把事件超时或曝光设置值作为固定总耗时",
    )
    return ZERO
