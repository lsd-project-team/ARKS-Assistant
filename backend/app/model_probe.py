"""使用真实模型协议逐项检测；工具测试只回传固定字符串，不访问源码。"""

from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, ToolMessage

from app import provider

CHECKS = [
    ("reply", "普通回复"),
    ("streaming", "流式输出"),
    ("tools", "工具往返"),
    ("summary", "压缩模型"),
]
TOOL = {
    "name": "connection_check",
    "description": "仅返回固定验收字符串，不产生任何副作用。",
    "parameters": {
        "type": "object",
        "properties": {"value": {"type": "string", "enum": ["ok"]}},
        "required": ["value"],
    },
}


async def check_reply(model):
    reply = await model.ainvoke("请仅回复：连接成功")
    if not reply.text.strip():
        raise ValueError("模型返回了空回复")
    return reply.text


async def check_streaming(model):
    parts = []
    async for chunk in model.astream("请简短回复：流式连接成功"):
        if chunk.text:
            parts.append(chunk.text)
    if not parts:
        raise ValueError("流式接口没有返回文本")
    return f"收到 {len(parts)} 个文本片段"


async def check_tools(model):
    bound = model.bind_tools([TOOL], tool_choice="connection_check")
    question = HumanMessage(content='必须调用 connection_check，value="ok"，不要输出其他内容。')
    reply = await bound.ainvoke([question])
    calls = reply.tool_calls
    if len(calls) != 1 or calls[0]["name"] != TOOL["name"] or calls[0]["args"] != {"value": "ok"}:
        raise ValueError("模型没有返回要求的工具调用")
    # 不再强制第二次调用，检查工具结果能否作为下一轮上下文使用。
    followup = await model.bind_tools([TOOL]).ainvoke(
        [
            question,
            reply,
            ToolMessage(content="连接检查成功，请用一句话确认", tool_call_id=calls[0]["id"]),
        ]
    )
    if not followup.text.strip() or followup.tool_calls:
        raise ValueError("工具结果返回后，模型没有完成正常回复")
    return "工具调用与结果返回均通过"


async def check_summary(model):
    reply = await model.ainvoke(
        "将以下对话压缩为目标、结论、待办三项：用户要求解释 Program.cs；"
        "助手确认 Main 是入口；下一步读取 FrmMain.cs。只输出简短摘要。"
    )
    if not reply.text.strip():
        raise ValueError("压缩模型返回了空摘要")
    return reply.text


async def probe_capabilities(settings):
    # 短请求检测协议能力，不将声明的上下文容量误当成已测得的窗口上限。
    bounded = settings.model_copy(
        update={"output_tokens": 256, "timeout_seconds": min(45, settings.timeout_seconds)}
    )
    model = provider.create_model(bounded)
    owned = [model]
    results = []
    functions = {
        "reply": check_reply,
        "streaming": check_streaming,
        "tools": check_tools,
        "summary": check_summary,
    }
    try:
        for key, label in CHECKS:
            if results and results[0]["status"] != "passed":
                results.append(
                    {
                        "id": key,
                        "label": label,
                        "status": "not_run",
                        "detail": "普通连接未通过，未继续请求",
                    }
                )
                continue
            try:
                selected = model
                if key == "summary":
                    selected = provider.create_model(bounded, summary=True)
                    owned.append(selected)
                detail = await functions[key](selected)
                detail = provider.safe_error(ValueError(detail), settings)
                results.append({"id": key, "label": label, "status": "passed", "detail": detail})
            except Exception as error:
                results.append(
                    {
                        "id": key,
                        "label": label,
                        "status": "failed",
                        "detail": provider.safe_error(error, settings),
                    }
                )
        return {
            "ok": all(item["status"] == "passed" for item in results),
            "connection_ok": results[0]["status"] == "passed",
            "model": settings.model,
            "protocol": settings.protocol,
            "summary_model": settings.summary_model or settings.model,
            "checked_at": datetime.now(UTC).isoformat(),
            "checks": results,
            "reply": results[0]["detail"],
        }
    finally:
        await provider.close_models(owned)
