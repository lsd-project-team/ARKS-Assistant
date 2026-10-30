"""Agent 运行职责拆分，依赖通过运行实例显式传入。"""

import asyncio

from deepagents import create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend
from deepagents.middleware.filesystem import FilesystemMiddleware
from deepagents.middleware.summarization import SummarizationToolMiddleware

from app.agents.analysis.policy import CONTINUE_QUESTION
from app.agents.analysis.retrieval_budget import RetrievalBudget
from app.agents.context.budget import BudgetedSummarization, ContextBudget
from app.agents.context.instructions import GlobalAgentInstructions, instruction_snapshot
from app.agents.context.task_guidance import TaskGuidance
from app.agents.context.tokens import estimate_tokens, input_budget
from app.agents.prompts.retrieval import RETRIEVAL_GUIDANCE
from app.agents.prompts.system import SYSTEM_PROMPT
from app.agents.runtime.answer_completion import AnswerCompletion
from app.agents.runtime.answer_draft import FlowAnswerDraft
from app.agents.runtime.artifacts import thread_artifacts
from app.agents.runtime.configuration import current_configuration
from app.agents.runtime.knowledge_answer import KnowledgeAnswerGuard
from app.agents.runtime.knowledge_selection import KnowledgeRetrieval
from app.agents.runtime.model_budget import ProjectModelBudget
from app.agents.runtime.privacy import redact
from app.agents.tools.conversation import conversation_tools
from app.agents.tools.source import source_tools
from app.infrastructure.providers.models import StateInspectionModel, create_model
from app.infrastructure.providers.usage import ProviderUsage, SummaryUsage
from app.modules.chat.schemas import SourceOptions
from app.modules.knowledge.corpora.debug_lookup import DebugIssueLookup
from app.modules.memory.selection import MemorySelection
from app.modules.projects.context import project_prompt
from app.modules.source_analysis.backend import SourceBackend
from app.modules.source_analysis.evidence import (
    SourceEvidenceGuard,
)


class AgentGraphBuilder:
    def __init__(self, runtime):
        self.runtime = runtime

    async def build(
        self,
        thread_id,
        checkpointer,
        emit,
        owned_models=None,
        *,
        inspection=False,
        memory_query=None,
        question_text=None,
        evidence=None,
        source_options=None,
        verified_context="",
        progress=None,
        retrieval=None,
        policy=None,
    ):
        runtime = self.runtime
        # 筛选后的工具结果和最终核查共用本轮资料范围。
        settings = current_configuration(runtime.settings, runtime.repository.database)
        options = SourceOptions.model_validate(source_options or {})
        instructions = await asyncio.to_thread(instruction_snapshot, runtime.paths)
        if not inspection:
            emit("agent_instructions", redact(instructions))
        if not inspection:
            emit("stage", {"stage": "connecting_model"})
        model = StateInspectionModel() if inspection else create_model(settings.model)
        summary_model = (
            StateInspectionModel() if inspection else create_model(settings.model, summary=True)
        )
        if not inspection and runtime.repository.project_id:
            for owned in (model, summary_model):
                owned.callbacks = [
                    *(getattr(owned, "callbacks", None) or []),
                    ProjectModelBudget(
                        runtime.model_ledger,
                        settings.model.context_tokens,
                        output_tokens=settings.model.output_tokens,
                    ),
                ]
        if not inspection:
            summary_model.callbacks = [*(summary_model.callbacks or []), SummaryUsage(emit)]
        if owned_models is not None:
            owned_models.extend([model, summary_model])
        backend = CompositeBackend(
            default=FilesystemBackend(
                await asyncio.to_thread(thread_artifacts, runtime.paths.scratch, thread_id)
            ),
            routes={"/workspace/": SourceBackend(runtime.workspace)},
            artifacts_root=f"/threads/{thread_id}",
        )
        tools = source_tools(runtime.workspace, evidence, progress)
        tools += runtime.semantic.tools()
        source_tool_names = {tool.name for tool in tools}
        requested_work = question_text if question_text is not None else memory_query or ""
        if (
            policy
            and policy.get("continuing")
            and CONTINUE_QUESTION.fullmatch(requested_work.strip())
        ):
            requested_work += "\n此前已授权的请求：" + policy["question"]
        if evidence is not None:
            evidence.user_request = requested_work
        tools += conversation_tools(runtime.repository, thread_id)
        available = input_budget(settings.model.context_tokens, settings.model.output_tokens)
        # 主模型先选择是否查资料；定义工具时不建立问题库快照或自动检索。
        debug_issues = (
            KnowledgeRetrieval(
                DebugIssueLookup(runtime.repository.database, emit, requested_work),
                model,
                requested_work,
                emit,
                available,
                timeout=min(30, settings.model.timeout_seconds),
            )
            if options.use_knowledge
            else None
        )
        if debug_issues:
            tools += debug_issues.tools()
        servers = [
            server
            for server in settings.mcp_servers
            if (options.use_deepwiki and settings.deepwiki_repo)
            or "deepwiki" not in (server.name + server.url).lower()
        ]
        if not inspection and servers:
            tools += await runtime.remote_tools(servers, emit)
        budget = min(int(settings.model.context_tokens * 0.75), int(available * 0.9))
        memory_prompt, included_memories = (
            await MemorySelection(runtime.memories, model, settings.model, emit).prepare(
                memory_query or requested_work, max_tokens=min(8000, available // 6)
            )
            if options.use_memory and not inspection
            else ("", [])
        )
        summary = BudgetedSummarization(
            summary_model,
            backend=backend,
            limit=settings.model.context_tokens,
            output=settings.model.output_tokens,
            emit=emit,
            memory_prompt=memory_prompt,
            trigger=("tokens", max(1, budget)),
            keep=("tokens", max(256, available // 8)),
            trim_tokens_to_summarize=max(1, available // 2),
            token_counter=estimate_tokens,
        )
        prompt = (
            SYSTEM_PROMPT
            + project_prompt()
            + f"\nDeepWiki 仓库：{settings.deepwiki_repo or '未配置'}\n"
        )
        prompt += "\n已有长期记忆：\n" + memory_prompt
        prompt += "\nDeepWiki 使用当前项目关联的仓库；未关联时不能沿用其他项目或历史对话的仓库。"
        prompt += (
            "\n本轮补读源码见 verified_source_context；"
            "同路径异版本的历史选区或工具结果只作历史快照。"
        )
        prompt += (
            "\n本轮未接入流程图谱、功能说明和交接资料，不能声称已检索这些来源。"
            "项目资料和全项目阅读功能已移除，不检索项目文档、旧共享结论或阅读成果。"
            "相关代码问题请读取本地源码；历史对话中的资料引用不代表本轮已经检索。"
        )
        if policy:
            prompt += (
                f"\n本轮分析模式：{policy['mode']}，工具额度 {policy['limit']}，"
                f"其中 {policy['reserve']} 次预留关键复核。"
            )
            if policy["continuing"]:
                prompt += "\n继续核查用户此前的问题，剩余项优先：" + policy["question"]
        # 恢复和重新生成也能看到本轮补读资料，不能只记录证据而不给模型正文。
        prompt += verified_context
        prompt += (
            "\n业务源码保持只读，可提供分析与修改建议；"
            "没有修改文件、执行命令或审核交付工具，不能声称已执行。"
        )
        if debug_issues:
            prompt += "\n" + RETRIEVAL_GUIDANCE
        if not inspection:
            emit(
                "context_sources",
                {
                    "memories": included_memories,
                    "materials": [],
                    "handover_materials": [],
                    "debug_issues": [],
                    "source_options": options.model_dump(),
                },
            )
        if not options.use_memory:
            prompt += "\n本轮不使用长期记忆。"
        prompt += (
            "\n长期记忆由后台从符合条件的闲置聊天提取整理，本轮没有即时保存或修改记忆工具。"
            "不能声称已经记住或已保存；用户提出稳定偏好时正常回应，是否生成由后台处理。"
        )
        prompt += (
            "\n个人偏好以当前登录账号带入的记忆为准，"
            "不把其他人在共享对话里的偏好当作本账号长期偏好。"
        )
        graph = create_deep_agent(
            model=model,
            tools=tools,
            backend=backend,
            checkpointer=checkpointer,
            system_prompt=prompt,
            subagents=[],
            middleware=[
                summary,
                SummarizationToolMiddleware(summary),
                GlobalAgentInstructions(instructions),
                TaskGuidance(
                    requested_work,
                    source_tool_names,
                    evidence,
                    deep=bool(policy and policy["mode"] == "deep"),
                ),
                *(
                    [SourceEvidenceGuard(evidence, None if inspection else model)]
                    if evidence is not None
                    else []
                ),
                KnowledgeAnswerGuard(
                    None if inspection else model,
                    question_text or "",
                    lambda: debug_issues.review_records() if debug_issues else [],
                    emit,
                    available,
                    source_required=bool(evidence and evidence.required),
                    resolve=debug_issues.resolve_references if debug_issues else None,
                    preselected=debug_issues.selected if debug_issues else None,
                ),
                FlowAnswerDraft(
                    None if inspection else model,
                    question_text or "",
                    evidence,
                    emit,
                    available,
                    instructions=instructions,
                ),
                AnswerCompletion(
                    emit, settings.model.output_tokens, settings.analysis.max_continuations
                ),
                retrieval or RetrievalBudget(emit),
                ContextBudget(
                    settings.model.context_tokens, settings.model.output_tokens, memory_prompt, emit
                ),
                ProviderUsage(emit),
                FilesystemMiddleware(
                    backend=backend,
                    tools=["read_file", "ls", "glob", "grep"],
                    # 批量源码本身限制为 12000 tokens，不能再被旧的 4000 阈值移出正文。
                    tool_token_limit_before_evict=16000,
                ),
            ],
        )
        return graph
