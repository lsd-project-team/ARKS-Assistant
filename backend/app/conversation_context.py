"""上下文透明度：读取真实检查点与本轮注入记录，纠错不改原始对话。"""

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.context import estimate_tokens
from app.provider import close_models
from app.runtime import AgentRuntime
from app.schemas import SummaryCorrection


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
            state = await graph.aget_state({"configurable": {"thread_id": thread_id}})
        values = state.values
        event = values.get("_summarization_event")
        messages = values.get("messages", [])
        effective = (
            [event["summary_message"], *messages[event["cutoff_index"] :]] if event else messages
        )
        return {
            "summary": event["summary_message"].text if event else None,
            "version": state.config["configurable"].get("checkpoint_id") if state.config else None,
            "updated_at": state.created_at,
            "summarized_count": event["cutoff_index"] if event else 0,
            "message_count": len(messages),
            "tokens": estimate_tokens(effective),
            "limit": self.runtime.settings.load().model.context_tokens,
        }

    async def correct(self, thread_id: str, request: SummaryCorrection) -> dict:
        if self.repository.has_active_run(thread_id):
            raise ValueError("请等待回复完成或停止运行后再纠正摘要")
        if not request.summary.strip():
            raise ValueError("摘要不能为空")
        owned_models = []
        config = {"configurable": {"thread_id": thread_id}}
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
                corrected = {
                    **event,
                    "summary_message": event["summary_message"].model_copy(
                        update={"content": request.summary.strip()}
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
        message = self.repository.message(run["message_id"])
        snapshot = None
        tools = []
        cursor = 0
        while True:
            events = self.repository.events(run_id, cursor)
            for event in events:
                if event["kind"] == "context_sources":
                    snapshot = event["payload"]
                if event["kind"] == "tool_start":
                    tools.append(event["payload"])
            if len(events) < 500:
                break
            cursor = events[-1]["sequence"]
        return {
            "memories": snapshot["memories"] if snapshot else [],
            "recorded": snapshot is not None,
            "selections": message["selections"],
            "tools": tools,
        }
