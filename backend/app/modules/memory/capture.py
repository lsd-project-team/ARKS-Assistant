"""记忆工具的真实保存结果，同时供模型、流式反馈和历史来源面板使用。"""

import asyncio
import re

from app.modules.chat.schemas import MemoryWrite
from app.modules.memory.identity import user_memory_owner


def feedback(emit, name, scope, status, text):
    if emit:
        emit(
            "memory_save",
            {
                "name": name,
                "scope": scope,
                "status": status,
                "text": text,
                "owner_id": user_memory_owner(),
            },
        )


async def remember_fact(
    memories,
    thread_id,
    evidence,
    model,
    emit,
    *,
    name,
    content,
    scope="project",
    source_paths=None,
    allow_automatic=True,
    request_text="",
):
    if not name.endswith(".md"):
        name += ".md"
    if re.search(r"我的.{0,12}(偏好|习惯)|个人偏好|以后.{0,12}(中文|简短|详细)", request_text):
        scope = "user"
    if not allow_automatic and not re.search(
        r"记住|记下来|记一下|保存.{0,12}(记忆|偏好|结论)", request_text
    ):
        feedback(emit, name, scope, "not_saved", "自动记忆已关闭，本轮没有明确的记忆保存请求")
        return {"saved": False, "reason": "请先取得用户明确的记忆保存请求"}
    try:
        try:
            previous = memories.read(scope, name)
        except FileNotFoundError:
            previous = None
        if previous and previous.get("lifecycle") in {"invalid", "needs_review"}:
            feedback(emit, name, scope, "needs_review", "已有记忆待复核，本次尚未保存")
            return {
                "saved": False,
                "requires_review": True,
                "reason": "已有记忆待复核，请到记忆管理核对后更新",
            }
        paths = [path.removeprefix("/workspace/") for path in source_paths or []]
        verified = scope == "user" or bool(
            evidence
            and paths
            and all(
                any(
                    row["path"] == path
                    and row["version"] == memories.workspace.read(path)["version"]
                    for row in evidence.reads
                )
                for path in paths
            )
        )
        request = MemoryWrite(
            name=name,
            content=content,
            scope=scope,
            version=previous["version"] if previous else None,
            record_version=previous["record_version"] if previous else None,
            source_thread_id=thread_id,
            source_paths=paths,
            lifecycle="valid" if verified else "needs_review",
        )
        matches = await memories.semantic_review(request, model, emit)
        if any(row["kind"] == "conflict" for row in matches):
            feedback(
                emit, name, scope, "needs_review", "发现记忆冲突，本次尚未保存，请到记忆管理核对"
            )
            return {
                "saved": False,
                "requires_review": True,
                "matches": matches,
                "reason": "存在潜在矛盾，不可自行确认",
            }
        result = await asyncio.to_thread(memories.save, request)
        pending = result["lifecycle"] != "valid"
        feedback(
            emit,
            name,
            scope,
            "needs_review" if pending else "saved",
            "记忆已保存，待复核" if pending else "记忆已保存",
        )
        return {**result, "saved": True}
    except (ValueError, OSError):
        feedback(emit, name, scope, "not_saved", "记忆未保存，请核对重复内容、版本或保存条件")
        raise
