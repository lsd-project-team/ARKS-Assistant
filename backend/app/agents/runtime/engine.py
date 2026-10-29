"""Deep Agents 装配、检查点恢复和流事件归一化。"""

import asyncio

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.analysis.policy import configured_analysis
from app.agents.runtime.configuration import bind_configuration, current_configuration
from app.agents.runtime.executor import AgentRunExecutor
from app.agents.runtime.feedback import tool_stage
from app.agents.runtime.graph_builder import AgentGraphBuilder
from app.agents.tools.debug_capture import capture_command
from app.core.config import Paths, SettingsStore
from app.infrastructure.mcp.client import ToolCatalog, adapt_tool
from app.infrastructure.providers.models import close_models
from app.modules.chat.regeneration import previous_run_event
from app.modules.chat.repository import Repository
from app.modules.knowledge.source_guides import ProjectKnowledge
from app.modules.memory.service import MemoryService
from app.modules.settings.model_ledger import ModelLedger
from app.modules.source_analysis.csharp import CSharpAnalysis
from app.modules.source_analysis.workspace import Workspace


class AgentRuntime:
    def checkpoint_id(self, thread_id):
        generation = self.repository.catalog.get(thread_id).get("context_generation", 0)
        return f"{thread_id}:project:{generation}" if generation else thread_id

    def __init__(
        self,
        paths: Paths,
        settings: SettingsStore,
        workspace: Workspace,
        repository: Repository,
        memories: MemoryService,
    ):
        self.paths, self.settings, self.workspace = paths, settings, workspace
        self.repository, self.memories = repository, memories
        self.mcp_cache = ToolCatalog(paths.data / "mcp-tools")
        self.knowledge = ProjectKnowledge(workspace)
        self.semantic = CSharpAnalysis(workspace)

        def project_id():
            return repository.project_id or repository.workspace_id

        self.model_ledger = ModelLedger(repository.database, project_id)
        self.project_lock = asyncio.Lock()

    async def remote_tools(self, servers, emit):
        result = []
        for server in servers:
            if not server.enabled:
                continue
            try:
                emit("stage", {"stage": "connecting_mcp", "detail": server.name})
                definitions, cached = await self.mcp_cache.get(server)
                if cached:
                    emit(
                        "notice",
                        {
                            "text": f"{server.name} 连接不稳定，使用已保存的工具定义",
                            "code": "mcp_connection",
                            "action": "mcp_settings",
                        },
                    )
                result.extend(
                    adapt_tool(
                        server,
                        remote,
                        workspace=self.workspace,
                        repo=current_configuration(self.settings).deepwiki_repo,
                        emit=emit,
                    )
                    for remote in definitions
                )
            except Exception:
                emit(
                    "notice",
                    {
                        "text": f"{server.name} 暂时无法连接，本轮继续使用本地源码",
                        "code": "mcp_connection",
                        "action": "mcp_settings",
                    },
                )
        return result

    async def graph(self, *args, **kwargs):
        return await AgentGraphBuilder(self).build(*args, **kwargs)

    def input_message(self, message):
        content = message["content"]
        for selection in message["selections"]:
            stale = selection.get("stale", False)
            if stale:
                content += (
                    "\n\n注意：以下代码选区是历史快照，当前文件已经变化或不存在。"
                    "回答时明确区分快照和当前源码，引用当前行号前必须重新读取核对。"
                )
            content += (
                f"\n\n<code_selection path={selection['path']!r} "
                f"lines={selection['start_line']}-{selection['end_line']} "
                f"version={selection['version']} stale={str(stale).lower()}>"
                f"\n{selection['content']}\n</code_selection>"
            )
        return HumanMessage(content=content, id=message["id"])

    def current_input(self, message):
        # 等待队列与历史分支可能停留很久，在真正发送前再次核对快照版本。
        selections = []
        for selection in message["selections"]:
            try:
                current_source = self.workspace.read(selection["path"])
                stale = current_source["version"] != selection["version"]
                stale = stale or bool(
                    selection.get("source_workspace_id")
                    and selection["source_workspace_id"] != current_source["source_workspace_id"]
                )
            except (OSError, ValueError):
                stale = True
            selections.append({**selection, "stale": stale})
        return self.input_message({**message, "selections": selections})

    async def execute(self, run, emit):
        owned_models = []
        configuration, policy = configured_analysis(
            current_configuration(self.settings),
            self.repository.message(run["message_id"])["content"],
            previous_run_event(self.repository, run, "analysis_plan"),
        )
        run = {**run, "analysis_policy": policy}
        try:
            with bind_configuration(configuration):
                captured = await capture_command(self, run, emit, owned_models)
                if captured is not None:
                    return captured
                return await self._execute(run, emit, owned_models)
        finally:
            await close_models(owned_models)

    async def _execute(self, *args, **kwargs):
        return await AgentRunExecutor(self).execute(*args, **kwargs)

    @staticmethod
    def emit_updates(event, emit):
        for node, update in event.items():
            if not isinstance(update, dict):
                continue
            for message in update.get("messages", []):
                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        emit("stage", {"stage": tool_stage(call["name"])})
                        emit(
                            "tool_start",
                            {"id": call["id"], "name": call["name"], "arguments": call["args"]},
                        )
                elif getattr(message, "type", "") == "tool":
                    emit("stage", {"stage": "thinking"})
                    emit(
                        "tool_end",
                        {
                            "id": message.tool_call_id,
                            "name": message.name,
                            "result": message.text[:2000],
                            "status": getattr(message, "status", "success"),
                            **{
                                key: message.additional_kwargs[key]
                                for key in ("execution_status", "skip_reason", "cached")
                                if key in message.additional_kwargs
                            },
                        },
                    )
            if "summarization" in node.lower():
                emit("compaction", {"text": "上下文已压缩，原始对话仍可检索"})
