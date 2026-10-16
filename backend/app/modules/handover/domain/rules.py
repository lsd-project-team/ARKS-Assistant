"""引用校验、依赖闭环与人工确认门槛，不把 AI 推断当成验收。"""

LAYERS = ["source", "interface", "offline", "simulation", "bench", "device", "release"]


def linked_ids(payload):
    result = {item["record_id"] for item in payload.get("evidence", [])}
    result.update(item["record_id"] for item in payload.get("records", []))
    for key in ("task_id", "baseline_id", "source_id", "package_id", "supersedes"):
        if payload.get(key):
            result.add(payload[key])
    for key in ("dependencies", "constraints", "task_ids", "record_ids"):
        result.update(payload.get(key, []))
    return result


def validate_links(kind, payload, records, revision):
    for identifier in linked_ids(payload):
        if identifier not in records or records[identifier]["state"] == "archived":
            raise ValueError("引用必须属于当前项目且未归档")
    expected = {
        "supersedes": "source",
        "task_id": "task",
        "baseline_id": "baseline",
        "source_id": "source",
        "package_id": "package",
    }
    for field, target in expected.items():
        identifier = payload.get(field)
        if identifier and records[identifier]["kind"] != target:
            raise ValueError(f"{field} 必须引用 {target}")
    for field, target in (
        ("dependencies", "task"),
        ("task_ids", "task"),
        ("constraints", "constraint"),
    ):
        if any(records[item]["kind"] != target for item in payload.get(field, [])):
            raise ValueError(f"{field} 的引用类型不正确")
    for evidence in payload.get("evidence", []) + payload.get("records", []):
        old = revision(evidence["record_id"], evidence["version"])
        quote = evidence.get("quote", "")
        # 引文必须来自固定版本正文，模型不能编造来源或从新版本冒充旧引文。
        source = old["payload"]
        if old["kind"] in {"source", "interview"}:
            content = [source.get("content", source.get("transcript", ""))]
        else:
            content = [value for value in source.values() if isinstance(value, str)]
        if quote and not any(quote in value for value in content):
            raise ValueError("引文与来源版本不一致，请重新选择原文")
    if kind == "receipt" and payload["package_id"]:
        revision(payload["package_id"], payload["package_version"])


def dependency_cycle(identifier, payload, records):
    visiting, visited = set(), set()

    def visit(node):
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        dependencies = (
            payload["dependencies"]
            if node == identifier
            else records[node]["payload"].get("dependencies", [])
        )
        if any(visit(child) for child in dependencies):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    if visit(identifier):
        raise ValueError("工作项依赖形成循环，请先解除循环")


def task_blocks(task, records):
    payload, identifier = task["payload"], task["id"]
    blocks = []
    for dependency in payload["dependencies"]:
        row = records.get(dependency)
        if not row or row["state"] != "confirmed" or row["payload"]["work_status"] != "accepted":
            blocks.append(f"依赖工作未验收：{row['title'] if row else dependency}")
    constraints = set(payload["constraints"])
    if any(key not in records or records[key]["state"] == "archived" for key in constraints):
        blocks.append("相关约束已归档或不存在，请重新复核适用范围")
    for row in records.values():
        if row["state"] == "archived":
            continue
        value = row["payload"]
        if row["kind"] == "issue" and (value["status"] == "open" or row["state"] != "confirmed"):
            applies = not value["task_id"] or value["task_id"] == identifier
            if applies and (
                value["risk"] in {"high", "critical"}
                or value["category"] in {"blocker", "conflict"}
            ):
                blocks.append(f"未解决的问题：{row['title']}")
        if row["kind"] == "constraint":
            applies = (
                row["id"] in constraints
                or (not value["task_ids"] and value["category"] == "safety")
                or identifier in value["task_ids"]
            )
            if applies and row["state"] != "confirmed":
                blocks.append(f"约束待确认：{row['title']}")
    baseline = records.get(payload["baseline_id"])
    if not baseline or baseline["state"] != "confirmed" or baseline["payload"]["missing"].strip():
        blocks.append("源码基线或接收环境尚未确认")
    return blocks


def required(payload, fields):
    missing = [label for field, label in fields if not str(payload.get(field, "")).strip()]
    if missing:
        raise ValueError("确认前请补齐：" + "、".join(missing))


def confirmation_gate(record, records):
    kind, payload = record["kind"], record["payload"]
    if kind in {"candidate", "job"}:
        raise ValueError("AI 候选须审核后合并，运行记录不能人工确认")
    if kind == "task":
        required(payload, [("goal", "目标"), ("acceptance", "验收标准"), ("owner", "负责人")])
        if payload["work_status"] == "accepted":
            blocks = task_blocks(record, records)
            matching = [
                row
                for row in records.values()
                if row["kind"] == "verification"
                and row["state"] == "confirmed"
                and row["payload"]["task_id"] == record["id"]
                and row["payload"]["baseline_id"] == payload["baseline_id"]
                and row["payload"]["result"] == "pass"
                and row["payload"]["layer"] == payload["required_layer"]
            ]
            if not matching:
                blocks.append("缺少对应基线与验证层级的已确认通过记录")
            attempts = [
                row
                for row in records.values()
                if row["kind"] == "verification"
                and row["state"] != "archived"
                and row["payload"]["task_id"] == record["id"]
                and row["payload"]["baseline_id"] == payload["baseline_id"]
                and row["payload"]["layer"] == payload["required_layer"]
            ]
            latest = max(attempts, key=lambda row: row["created_at"], default=None)
            if latest and (latest["state"] != "confirmed" or latest["payload"]["result"] != "pass"):
                blocks.append("最新相关验证尚未确认通过，请先处理失败或待复核的结果")
            if blocks:
                raise ValueError("暂不能验收：" + "；".join(blocks))
    elif kind == "plan":
        task = records.get(payload["task_id"])
        if not task or not payload["steps"]:
            raise ValueError("接续计划须关联工作项并包含步骤")
        blocks = task_blocks(task, records)
        if task["state"] != "confirmed":
            blocks.append("工作项目标与现状尚未人工确认")
        if payload["baseline_id"] != task["payload"]["baseline_id"]:
            blocks.append("计划基线与工作项不一致")
        if payload["unresolved"].strip():
            blocks.append("计划仍有待解决条件")
        for number, step in enumerate(payload["steps"], 1):
            if any(
                not step[field].strip()
                for field in (
                    "action",
                    "prerequisite",
                    "output",
                    "verification",
                    "stop",
                    "rollback",
                    "owner",
                )
            ):
                blocks.append(f"步骤 {number} 缺少执行、验证、停止或回退条件")
        if blocks:
            raise ValueError("计划暂不能确认：" + "；".join(blocks))
    elif kind == "verification":
        required(
            payload,
            [
                ("task_id", "工作项"),
                ("baseline_id", "基线"),
                ("tester", "验证人"),
                ("date", "日期"),
                ("environment", "环境"),
                ("method", "验证方法"),
                ("observed", "实际结果"),
                ("report", "报告或证据位置"),
            ],
        )
        if payload["result"] == "pending":
            raise ValueError("尚未执行的验证不能确认")
    elif kind == "constraint":
        required(
            payload,
            [("condition", "约束条件"), ("consequence", "影响"), ("authority", "依据或确认职责")],
        )
        if payload["category"] == "safety":
            required(payload, [("stop_condition", "停止条件")])
    elif kind == "baseline":
        required(
            payload,
            [
                ("source_id", "固定源码资料"),
                ("source_scope", "源码覆盖范围"),
                ("software_version", "软件版本"),
                ("device", "设备"),
                ("build", "构建前提"),
                ("environment", "接收环境"),
                ("firmware", "固件版本或不适用说明"),
                ("sdk", "SDK 版本或不适用说明"),
                ("recipe", "配方版本或不适用说明"),
                ("calibration", "标定版本或不适用说明"),
                ("configuration", "配置版本或不适用说明"),
            ],
        )
        if payload["missing"].strip():
            raise ValueError("接收环境仍有缺项，不能确认基线")
        for key in ("firmware", "sdk", "recipe", "calibration", "configuration"):
            value = payload[key].strip().casefold()
            if value.startswith(("未知", "待确认", "未提供", "不清楚", "unknown")):
                raise ValueError("基线仍有未知设备条件；不适用的项目也应明确记录后再确认")
        source = records[payload["source_id"]]
        if source["payload"]["format"] not in {"source", "zip", "cs", "cpp", "c", "h"}:
            raise ValueError("基线须关联固定源码文件或源码 ZIP，说明文档不能代替源码基线")
    elif kind == "interview":
        required(payload, [("author", "原作者"), ("date", "访谈日期"), ("transcript", "访谈原文")])
    elif kind == "issue" and payload["status"] == "resolved":
        required(payload, [("owner", "处理人"), ("answer", "处理结论"), ("closure", "关闭依据")])
        if not payload["evidence"]:
            raise ValueError("关闭问题必须附上来源或验证证据")
    elif kind == "source":
        if any(
            row["kind"] == "source"
            and row["state"] != "archived"
            and row["payload"].get("supersedes") == record["id"]
            for row in records.values()
        ):
            raise ValueError("资料已有替代版本，请复核并确认新版本")
        # 添加表单已简化；原件名称、哈希与系统修订足以标识固定资料。
        required(payload, [("filename", "资料名称"), ("sha256", "原文标识")])
        if payload["parse_status"] != "readable":
            raise ValueError("资料存在未解析内容，请补充可读版本后确认")
    elif kind == "framework":
        required(
            payload,
            [
                ("scope", "覆盖范围"),
                ("entrypoints", "入口"),
                ("layers", "分层职责"),
                ("flow", "关键链路"),
                ("coverage", "覆盖情况"),
            ],
        )
    elif kind == "training":
        required(
            payload,
            [
                ("conditions", "运行条件"),
                ("operation", "操作流程"),
                ("timing", "时序"),
                ("failure", "异常"),
                ("recovery", "恢复"),
                ("exercise", "练习"),
            ],
        )
    elif kind == "decision":
        required(
            payload,
            [("intent", "设计意图"), ("alternatives", "备选方案"), ("rejected", "舍弃理由")],
        )
    elif kind == "receipt":
        required(
            payload,
            [
                ("package_id", "交接包版本"),
                ("receiver", "接收人"),
                ("date", "日期"),
                ("understanding", "复述理解"),
                ("demonstration", "演示或实操结果"),
            ],
        )
    elif kind == "package" and not payload["records"]:
        raise ValueError("交接包尚未包含任何固定版本记录")
