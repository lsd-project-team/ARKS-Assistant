"""共享对话的来源与运行事件不向其他账号暴露个人记忆和指令正文。"""

from app.modules.memory.identity import user_memory_owner


def run_memory_actor(repository, run):
    snapshot = run.get("project_snapshot", {}).get("_execution_user")
    return snapshot["id"] if snapshot else repository.message(run["message_id"]).get("actor_id")


def visible_memories(rows, actor_id=None):
    owner = user_memory_owner()
    return [
        row
        for row in rows
        if row.get("scope") != "user" or not owner or (row.get("owner_id") or actor_id) == owner
    ]


def visible_run_event(event, actor_id):
    owner = user_memory_owner()
    kind, payload = event["kind"], event["payload"]
    if kind == "agent_instructions" and owner and payload.get("owner_id") != owner:
        return None
    if kind == "context_sources":
        return {
            **event,
            "payload": {
                **payload,
                "memories": visible_memories(payload.get("memories", []), actor_id),
            },
        }
    if not owner or actor_id == owner:
        return event
    if kind == "memory_selection" or (
        kind == "provider_usage" and payload.get("purpose") == "memory_selection"
    ):
        return None
    if kind == "memory_save" and payload.get("scope") == "user":
        return None
    if kind in {"tool_start", "tool_end"} and payload.get("name") == "remember":
        hidden = {
            key: value for key, value in payload.items() if key not in {"arguments", "result"}
        }
        hidden["result" if kind == "tool_end" else "arguments"] = (
            "个人记忆内容仅保存账号可见" if kind == "tool_end" else {}
        )
        return {**event, "payload": hidden}
    return event
