"""错误分类用于处理入口；原始错误必须先脱敏再返回。"""

from langchain_core.exceptions import ContextOverflowError

from app.provider import safe_error


def error_feedback(error, settings):
    status = getattr(error, "status_code", None)
    name = type(error).__name__.lower()
    text = safe_error(error, settings)
    lowered = text.lower()
    if status in {401, 403}:
        code, hint, action = (
            "authentication",
            "密钥无效或没有模型权限，请检查供应商配置。",
            "settings",
        )
    elif status == 429:
        code, hint, action = "rate_limit", "供应商限流，请稍后重试或切换模型。", "retry"
    elif status in {408, 504} or "timeout" in name:
        code, hint, action = "timeout", "请求超时，已生成内容保留；可重试或调整超时时间。", "retry"
    elif "connection" in name or "connecterror" in name:
        code, hint, action = "connection", "无法连接模型接口，请检查地址和本机网络。", "settings"
    elif isinstance(error, ContextOverflowError) or (
        "context" in lowered and any(word in lowered for word in ("length", "limit", "token"))
    ):
        code, hint, action = (
            "context_limit",
            "上下文超过输入预算，可减少选区、工具或记忆，或调整模型容量配置。原始内容保留。",
            "context",
        )
    elif status and status >= 500:
        code, hint, action = "provider_unavailable", "供应商暂时不可用，稍后重试。", "retry"
    elif "请先配置" in text:
        code, hint, action = "configuration", "请配置接口地址、模型名称和密钥。", "settings"
    else:
        code, hint, action = "unknown", "本轮未完成，输入和部分回复已保留，可重试。", "retry"
    return {"code": code, "text": text, "hint": hint, "action": action}


def tool_stage(name):
    if name in {
        "search_handover_materials",
        "read_handover_material",
        "search_project_materials",
        "read_project_material",
    }:
        return "reading_materials"
    if name in {"search_debug_issues", "read_debug_issue"}:
        return "reading_debug"
    if name.startswith("mcp_"):
        return "reading_wiki"
    if name in {"recall_conversation", "read_conversation_message", "remember"}:
        return "reading_memory"
    if name == "compact_conversation":
        return "compacting"
    return "reading_source"
