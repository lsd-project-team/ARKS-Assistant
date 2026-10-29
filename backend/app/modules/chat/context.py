"""上下文透明度：读取真实检查点与本轮注入记录，纠错不改原始对话。"""

from langchain_core.messages import AIMessage
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents.context.summary_text import summary_parts
from app.agents.context.tokens import current_budget
from app.agents.runtime.configuration import current_configuration
from app.agents.runtime.engine import AgentRuntime
from app.infrastructure.providers.models import close_models
from app.modules.chat.schemas import SummaryCorrection
from app.modules.memory.visibility import run_memory_actor, visible_run_event


class ConversationContext:
    def __init__(self, runtime: AgentRuntime):
        self.runtime = runtime
        self.repository = runtime.repository
        self.checkpoints = str(runtime.paths.data / "checkpoints.sqlite3")

    async def read(self, thread_id: str) -> dict:
        self.repository.thread(thread_id)
        async with AsyncSqliteSaver.from_conn_string(self.checkpoints) as saver:
            graph = await self.runtime.graph(
                thread_id, saver, lambda *_event: None, inspection=True
            )
            # LangGraph 增量通道不会在每个检查点重复保存全部消息，必须由图还原状态。
            config = {"configurable": {"thread_id": self.runtime.checkpoint_id(thread_id)}}
            state = await graph.aget_state(config)
            values = state.values
            if not state.values.get("messages") and not self.repository.has_active_run(thread_id):
                # 返回待重建的完整会话，不在读取接口写检查点，避免与新运行竞争。
                prior = self.repository.branches.context(thread_id)
                if prior:
                    values = {
                        **values,
                        "messages": [
                            self.runtime.current_input(row)
                            if row["role"] == "user"
                            else AIMessage(content=row["content"], id=row["id"])
                            for row in prior
                        ],
                    }
        event = values.get("_summarization_event")
        messages = values.get("messages", [])
        effective = (
            [event["summary_message"], *messages[event["cutoff_index"] :]] if event else messages
        )
        settings = current_configuration(self.runtime.settings, self.repository.database).model
        snapshot = self.repository.latest_event(thread_id, "context_budget")
        return {
            "summary": summary_parts(event["summary_message"].text)[1] if event else None,
            "version": state.config["configurable"].get("checkpoint_id") if state.config else None,
            "updated_at": state.created_at,
            "summarized_count": event["cutoff_index"] if event else 0,
            "message_count": len(messages),
            **current_budget(effective, snapshot, settings.context_tokens, settings.output_tokens),
        }

    async def correct(self, thread_id: str, request: SummaryCorrection) -> dict:
        if self.repository.has_active_run(thread_id):
            raise ValueError("请等待回复完成或停止运行后再纠正摘要")
        if not request.summary.strip():
            raise ValueError("摘要不能为空")
        owned_models = []
        config = {"configurable": {"thread_id": self.runtime.checkpoint_id(thread_id)}}
        try:
            async with AsyncSqliteSaver.from_conn_string(self.checkpoints) as saver:
                # 仅装配状态通道，不连接 MCP，也不调用模型生成文本。
                graph = await self.runtime.graph(
                    thread_id, saver, lambda *_event: None, owned_models, inspection=True
                )
                state = await graph.aget_state(config)
                if state.next:
                    raise ValueError("存在待恢复执行，请先继续运行或完成新回复再纠正摘要")
                if (
                    not state.config
                    or state.config["configurable"].get("checkpoint_id") != request.version
                ):
                    raise ValueError("上下文已变化，请重新加载摘要后编辑")
                event = state.values.get("_summarization_event")
                if not event:
                    raise ValueError("当前对话尚未压缩")
                prefix, _body, suffix = summary_parts(event["summary_message"].text)
                corrected = {
                    **event,
                    "summary_message": event["summary_message"].model_copy(
                        update={"content": prefix + request.summary.strip() + suffix}
                    ),
                }
                await graph.aupdate_state(
                    config, {"_summarization_event": corrected}, as_node="model"
                )
        finally:
            await close_models(owned_models)
        result = await self.read(thread_id)
        latest = self.repository.thread(thread_id)["runs"][-1]
        self.repository.event(
            latest["id"],
            "summary_correction",
            {
                "version": result["version"],
                "previous_version": request.version,
                "text": "用户已纠正压缩摘要",
            },
        )
        return result

    def run_sources(self, run_id: str) -> dict:
        run = self.repository.run(run_id)
        actor_id = run_memory_actor(self.repository, run)
        message = self.repository.message(run["message_id"])
        snapshot = None
        budget = None
        tools = []
        evidence = []
        usage = []
        validation = None
        wiki, knowledge = [], []
        source_review = None
        completion, progress, plan = None, None, None
        tool_ends = {}
        instructions = None
        references, searches, memory_saves = {}, [], []
        cursor = 0
        while True:
            events = self.repository.events(run_id, cursor)
            for original in events:
                event = visible_run_event(original, actor_id)
                if event and event["kind"] == "agent_instructions":
                    instructions = event["payload"]
                if event is None:
                    continue
                if event["kind"] == "knowledge_reference":
                    row = event["payload"]
                    references[(row["kind"], row["id"], row["version"], row["citation"])] = row
                if event["kind"] == "knowledge_search":
                    searches.append(event["payload"])
                if event["kind"] == "memory_save":
                    memory_saves.append(event["payload"])
                if event["kind"] == "context_sources":
                    snapshot = event["payload"]
                if event["kind"] == "context_budget":
                    budget = event["payload"]
                if event["kind"] == "tool_start":
                    tools.append(event["payload"])
                if event["kind"] == "tool_end":
                    tool_ends[event["payload"]["id"]] = event["payload"]
                if event["kind"] == "run_completion":
                    completion = event["payload"]
                if event["kind"] == "analysis_progress":
                    progress = event["payload"]
                if event["kind"] == "analysis_plan":
                    plan = event["payload"]
                if event["kind"] == "source_evidence":
                    row = dict(event["payload"])
                    try:
                        source = self.runtime.workspace.read(row["path"])
                        row["current_status"] = (
                            "match" if source["version"] == row["version"] else "changed"
                        )
                    except (OSError, ValueError):
                        row["current_status"] = "unavailable"
                    evidence.append(row)
                if event["kind"] == "provider_usage":
                    usage.append(event["payload"])
                if event["kind"] == "answer_validation":
                    validation = event["payload"]
                if event["kind"] == "wiki_provenance":
                    wiki.append(event["payload"])
                if event["kind"] == "knowledge_retrieval":
                    knowledge.append(event["payload"])
                if event["kind"] == "source_review":
                    source_review = event["payload"]
            if len(events) < 500:
                break
            cursor = events[-1]["sequence"]
        # 兼容升级前已经记录的自动带入快照，不把“允许使用”冒充实际来源。
        for field, kind in (
            ("materials", "material"),
            ("handover_materials", "handover_material"),
            ("debug_issues", "debug_issue"),
        ):
            for row in (snapshot or {}).get(field, []):
                key = (kind, row["id"], row["version"], row["citation"])
                references.setdefault(key, {"kind": kind, **row})
        return {
            "model": run["model_snapshot"],
            "agent_instructions": instructions,
            "budget": budget,
            "memories": snapshot["memories"] if snapshot else [],
            "materials": snapshot.get("materials", []) if snapshot else [],
            "handover_materials": snapshot.get("handover_materials", []) if snapshot else [],
            "debug_issues": snapshot.get("debug_issues", []) if snapshot else [],
            "recorded": snapshot is not None,
            "selections": message["selections"],
            "tools": [{**tool, **tool_ends.get(tool["id"], {})} for tool in tools],
            "completion": completion,
            "analysis_progress": progress,
            "analysis_plan": plan,
            "source_evidence": evidence,
            "provider_usage": usage,
            "answer_validation": validation,
            "source_options": snapshot.get("source_options") if snapshot else None,
            "wiki_provenance": wiki,
            "knowledge_retrieval": knowledge,
            "references": list(references.values()),
            "searches": searches,
            "memory_saves": memory_saves,
            "source_review": source_review,
        }
