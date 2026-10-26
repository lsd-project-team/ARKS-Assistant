"""逐阶段说明未知项来自输入、反馈、SDK还是分析边界。"""

from app.modules.action_timing.source_components import number


def stage_requirements(stage):
    if stage.get("resolved"):
        return None
    kind, code = stage["kind"], stage["code"]
    call = " ".join(code.split("{", 1)[0].split())[:200]
    limit = stage.get("analysis_limit")
    if limit:
        reason = {
            "recursion": "递归返回路径仍需分析",
            "call_depth": "分析调用深度保护",
            "call_budget": "分析调用数量保护",
            "loop_iterations": "分析循环展开保护",
            "control_graph": "分析控制流展开保护",
            "jump_budget": "分析标签跳转数量保护",
        }.get(limit["kind"], "分析展开资源保护")
        return "analysis", [
            f"{reason}：{call}",
            f"源码目标：{limit.get('target', stage['method'])}",
            *(
                [f"已分析{limit['used']}，分析上限{limit['limit']}；这个上限不是动作执行次数。"]
                if "limit" in limit
                else []
            ),
            "这是尚未完成的源码分析，不是缺少运行参数，也不表示源码算不出来。",
        ]
    explicit = stage.get("missing_inputs")
    if explicit:
        return "sdk" if stage.get("label") == "直接设备SDK调用" else "runtime", explicit
    model = stage.get("motion_model")
    if model:
        required = []
        if model.get("start_position") is None:
            receiver = call.split("(", 1)[0]
            required.append(f"{receiver} 的实际运动起点及规划/编码器位置关系")
        if not number(model.get("target")) and not number(model.get("distance")):
            required.append(f"目标或位移：{model.get('target', '请求点位')}")
        for field, label in (
            ("velocity", "有效速度"),
            ("acceleration", "加速度"),
            ("deceleration", "减速度"),
        ):
            if not number(model.get(field)):
                required.append(f"{label}：{model.get(field + '_expression', '轴运动配置')}")
        if model.get("time_unit") == "unproven":
            required.append("实际驱动/脉冲当量、速度曲线单位与平滑规则")
        required.append("初始化门禁、实际轴派生类型及到位稳定反馈")
        return "motion", required
    if kind == "delay" and stage.get("milliseconds") is None:
        return "input", [f"延时表达式的当前值：{stage.get('expression') or code}"]
    if kind == "motion":
        return "sdk", [f"该运动重载的有效参数与内部完成规则：{call}"]
    if kind == "wait":
        if code.lstrip().startswith("lock"):
            return "runtime", ["锁的实际占用与释放时间"]
        return "feedback", [f"实际满足/完成时刻：{call}", stage.get("note") or stage["label"]]
    if kind == "loop" and stage.get("iterations") is None and not stage.get("bounded"):
        return "input", [f"实际循环次数/退出条件：{code.split('{', 1)[0].strip()}"]
    if kind == "call" and stage["label"] == "包内输出/相机调用":
        return "sdk", [
            f"该包调用的实际输出/曝光及完成反馈：{call}",
            stage.get("note") or stage["label"],
        ]
    if kind == "call" and stage["label"] == "调用耗时不能由当前源码确定":
        return "external", [f"外部调用的内部耗时或返回/完成约定：{call}"]
    if kind in {"call", "unresolved"}:
        return "analysis", [
            f"需绑定参数/返回值或继续展开：{call}",
            stage.get("note") or stage["label"],
        ]
    return None


def attach(result):
    missing, seen = [], set()
    for stage in [*result["stages"], *result.get("supplementary_stages", [])]:
        requirement = stage_requirements(stage)
        if requirement is None:
            continue
        category, values = requirement
        if stage.get("motion_model"):
            stage["motion_model"]["unresolved"] = values
        # 保留具体位置与表达式，不把所有未知项统称为缺Hardware.json。
        key = (category, stage["path"], stage["line"], tuple(values), stage["background"])
        if key in seen:
            continue
        seen.add(key)
        missing.append(
            {
                "category": category,
                "required": values,
                "background": stage["background"],
                "path": stage["path"],
                "line": stage["line"],
                "method": stage["method"],
            }
        )
    for component in result.get("source_components", []):
        if not component.get("deferred") or not component["sources"]:
            continue
        source = component["sources"][0]
        required = ["任务回调是否实际触发、分支当前值及完成/等待关系"]
        required.extend(f"实际{factor}" for factor in component["factors"])
        key = (source["path"], source["line"], tuple(required))
        if key in seen:
            continue
        seen.add(key)
        missing.append(
            {
                "category": "input" if component["factors"] else "runtime",
                "required": required,
                "background": True,
                "path": source["path"],
                "line": source["line"],
                "method": component["method"],
            }
        )
    audit = result.get("continuation_audit", {})
    for target in audit.get("pending_targets", []):
        missing.append(
            {
                "category": "analysis",
                "background": False,
                **target,
                "required": [
                    f"补充源码核对仍有{audit['pending_contexts']}个上下文未展开：{target['method']}",
                    "这是分析资源限制，不是缺少运行参数或源码算不出来。",
                ],
            }
        )
    priority = {
        "motion": 0,
        "input": 1,
        "feedback": 2,
        "runtime": 3,
        "sdk": 4,
        "external": 5,
        "analysis": 6,
    }
    missing.sort(key=lambda r: (r["background"], priority[r["category"]]))
    result["missing_requirements"] = missing
    result["missing_categories"] = sorted({r["category"] for r in missing if not r["background"]})
