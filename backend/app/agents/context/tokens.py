"""完整请求的保守估算；未知供应商 tokenizer 时不冒充实际用量。"""

import json
import math
import re

from langchain_core.messages.utils import count_tokens_approximately
from langchain_core.utils.function_calling import convert_to_openai_tool


def text_tokens(text: str) -> int:
    return math.ceil(max(len(text) / 4, len(text.encode("utf-8")) / 3))


def fit_text(text: str, budget: int) -> str:
    """只缩短注入副本，二分寻找预算内的 Unicode 前缀，原始资料保持完整。"""
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if text_tokens(text[:middle]) <= budget:
            low = middle
        else:
            high = middle - 1
    return text[:low]


def tools_tokens(tools) -> int:
    if not tools:
        return 0
    definitions = [convert_to_openai_tool(tool) for tool in tools]
    return text_tokens(json.dumps(definitions, ensure_ascii=False, separators=(",", ":")))


def estimate_tokens(messages, *, tools=None) -> int:
    rows = list(messages)
    approximate = count_tokens_approximately(rows)
    serialized = []
    for row in rows:
        # 工具调用参数和调用 ID 也是请求内容，不能只计算 content 字段。
        value = {"role": getattr(row, "type", "unknown"), "content": getattr(row, "content", row)}
        for key in ("name", "tool_calls", "tool_call_id"):
            if item := getattr(row, key, None):
                value[key] = item
        serialized.append(json.dumps(value, ensure_ascii=False, default=str))
    byte_estimate = sum(text_tokens(value) + 8 for value in serialized)
    return max(approximate, byte_estimate) + tools_tokens(tools)


def input_budget(limit: int, output: int) -> int:
    return max(0, int(limit * 0.95) - output)


def message_breakdown(messages) -> dict:
    rows = list(messages)
    total = estimate_tokens(rows)
    instructions = [row for row in rows if row.id == "global-agent-instructions"]
    instruction_tokens = min(total, estimate_tokens(instructions)) if instructions else 0
    selection_tokens = sum(
        text_tokens(block)
        for row in rows
        if row.id != "global-agent-instructions"
        for block in re.findall(
            r"<code_selection\b.*?</code_selection>", str(row.content), flags=re.DOTALL
        )
    )
    selection_tokens = min(selection_tokens, total - instruction_tokens)
    return {
        "messages": total - selection_tokens - instruction_tokens,
        "selections": selection_tokens,
        **({"instructions": instruction_tokens} if instructions else {}),
    }


def request_budget(request, limit: int, output: int, memory_prompt: str = "") -> dict:
    system = estimate_tokens([request.system_message]) if request.system_message else 0
    memory = min(system, text_tokens(memory_prompt))
    parts = {
        "system": system - memory,
        "tools": tools_tokens(request.tools),
        "memory": memory,
        **message_breakdown(request.messages),
    }
    return {
        "tokens": sum(parts.values()),
        "limit": limit,
        "output_reserved": output,
        "headroom": limit - output - input_budget(limit, output),
        "input_limit": input_budget(limit, output),
        "breakdown": parts,
        "complete": True,
        "basis": "last_request",
    }


def current_budget(messages, snapshot: dict | None, limit: int, output: int) -> dict:
    if snapshot:
        result = {**snapshot, "breakdown": {**snapshot["breakdown"], **message_breakdown(messages)}}
        result["tokens"] = sum(result["breakdown"].values())
        return result
    return {
        "tokens": estimate_tokens(messages),
        "limit": limit,
        "input_limit": input_budget(limit, output),
        "output_reserved": output,
        "headroom": limit - output - input_budget(limit, output),
        "breakdown": message_breakdown(messages),
        "complete": False,
        "basis": "legacy_messages",
    }
