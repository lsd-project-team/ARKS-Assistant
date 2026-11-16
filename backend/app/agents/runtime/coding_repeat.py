"""编码工具重复调用保护：同样的检查或命令连续执行三次就拦截，避免空转。"""

import json
import os
import re

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import SystemMessage, ToolMessage

GUARDED = {
    "list_files",
    "read_project_file",
    "search_files",
    "find_files",
    "run_command",
    "read_process",
    "list_checkpoints",
    "diff_checkpoint",
}
PROGRESS = {
    "write_file",
    "edit_file",
    "multi_edit",
    "write_binary_file",
    "create_directory",
    "move_path",
    "delete_path",
    "checkpoint",
    "restore_checkpoint",
    "start_process",
    "stop_process",
}
LOOP_LIMIT = 12
SOURCE_EXTENSIONS = (
    ".cs",
    ".csproj",
    ".sln",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".go",
    ".rs",
    ".java",
    ".cpp",
    ".h",
)


def _is_source_write(name, args):
    if name not in {"write_file", "edit_file", "multi_edit"}:
        return False
    path = str(args.get("path", "")).replace("\\", "/").lower()
    if "tools/" in path or "probe" in path:
        return False
    return path.endswith(SOURCE_EXTENSIONS)


def _env_int(name, default):
    try:
        return max(1, int(os.environ.get(name, default)))
    except (TypeError, ValueError):
        return default


class CodingRepeatGuard(AgentMiddleware):
    def __init__(self, emit, limit=3, total_limit=150, require_source=False, explore_limit=20):
        self.emit = emit
        self.limit = _env_int("CODING_REPEAT_LIMIT", limit)
        self.total_limit = _env_int("CODING_REPEAT_TOTAL_LIMIT", total_limit)
        self.explore_limit = _env_int("CODING_SOURCE_EXPLORE_LIMIT", explore_limit)
        self.read_block_at = _env_int("CODING_REPEAT_READ_BLOCK", 6)
        self.command_block_at = _env_int("CODING_REPEAT_COMMAND_BLOCK", 10)
        self.require_source = require_source
        self.source_written = False
        self.total = 0
        self.counts = {}
        self.norm_counts = {}
        self.write_counts = {}
        self.write_blocked = 0
        self.force_build = False
        self.force_action = False
        self.cached = {}
        self.blocked_streak = 0

    async def awrap_model_call(self, request, handler):
        repeated = [
            (key[0], key[1], count)
            for key, count in self.counts.items()
            if count > 10
        ]
        normalized = [
            (key[0], key[1], count)
            for key, count in self.norm_counts.items()
            if count >= 6
        ]
        if (
            self.blocked_streak < 2
            and not repeated
            and not normalized
            and not (self.require_source and not self.source_written)
            and not self.force_build
            and not self.force_action
        ):
            return await handler(request)
        if normalized:
            tool, args, count = max(normalized, key=lambda item: item[2])
            guidance = (
                f"\n【空转保护】检测到 {tool} 的同类命令（忽略数字差异）已执行 {count} 次："
                f"{args[:120]}。不要再用打印数字/倒计时/重复探查等待；"
                "立即创建或修改工程文件并构建一个最小可运行版本，或结束并说明未完成项。"
            )
        elif self.force_action:
            guidance = (
                "\n【停止重复读取】同一内容已重复读取多次。不要再读同一文件；"
                "立即写文件、修改代码或运行 verify build，然后继续。"
            )
        elif self.force_build:
            guidance = (
                "\n【必须构建】同一文件已重复写入被拦截多次。立即调用 verify build"
                "（或 run_command 构建）；在构建完成前不要再写同一个文件。"
            )
        elif self.require_source and not self.source_written:
            guidance = (
                "\n【空目录生成】尚未写出任何源码。先write_file 创建工程与最小可运行入口，"
                "再继续调查；不要再做纯探索。"
            )
        elif repeated:
            tool, args, count = repeated[0]
            guidance = (
                f"\n【重复读取限制】{tool} 的同一参数已被请求 {count} 次（{args[:120]}）。"
                "不要再读取同一内容：基于已有信息直接写文件/Actions.cs，或调用 update_plan "
                "标记完成并结束；继续重复读取不会得到新信息。"
            )
        else:
            guidance = (
                "\n【重复调用保护】同一工具调用已被拦截多次，不要再读同一段内容。"
                "直接修改或删除失败的自测、换一个命令/路径，或者结束本轮并说明未完成项。"
            )
        system = request.system_message
        blocks = list(system.content_blocks) if system else []
        blocks.append({"type": "text", "text": guidance})
        prompt = (
            system.model_copy(update={"content": blocks})
            if system
            else SystemMessage(content=blocks)
        )
        return await handler(request.override(system_message=prompt))

    async def awrap_tool_call(self, request, handler):
        name = request.tool_call["name"]
        if self.force_action and name in {
            "read_project_file",
            "list_files",
            "grep",
            "read_source",
            "search_files",
            "find_files",
        }:
            return _blocked(
                request,
                name,
                {
                    "ok": False,
                    "note": (
                        "重复读取已触发限制。现在必须先写文件/修改代码或构建；"
                        "写文件或 verify build 成功后才能继续读。"
                    ),
                },
            )
        if self.force_action and name == "run_command":
            command = str(request.tool_call.get("args", {}).get("command", "")).lower()
            if "build" not in command and "verify" not in command:
                return _blocked(
                    request,
                    name,
                    {
                        "ok": False,
                        "note": (
                            "重复命令已触发限制。不要继续跑同一命令；"
                            "先修改文件，或执行构建（dotnet build / verify build）。"
                        ),
                    },
                )
        if self.force_build and name in {"write_file", "edit_file", "multi_edit"}:
            return _blocked(
                request,
                name,
                {
                    "ok": False,
                    "note": (
                        "已多次重复写入同一内容。现在只允许先构建："
                        "调用 verify build 或 run_command 执行构建，构建后再修改文件。"
                    ),
                },
            )
        if name == "verify" or (
            name == "run_command"
            and "build" in str(request.tool_call.get("args", {}).get("command", "")).lower()
        ):
            self.force_build = False
            self.write_blocked = 0
            self.force_action = False
        if name in GUARDED or name in PROGRESS:
            self.total += 1
            if self.total > self.total_limit:
                self.blocked_streak += 1
                self.emit("coding_budget_blocked", {"total": self.total})
                return _blocked(
                    request,
                    name,
                    {
                        "ok": False,
                        "budget_exhausted": True,
                        "note": (
                            "本轮编码工具调用已达上限。请停止继续探查，"
                            "基于已有结果总结完成情况、未完成项和下一步建议。"
                        ),
                    },
                )
        if name in PROGRESS:
            self.counts.clear()
            self.norm_counts.clear()
            self.cached.clear()
            self.blocked_streak = 0
            if name in {"write_file", "edit_file", "multi_edit"}:
                args = request.tool_call.get("args", {})
                self.force_action = False
                import hashlib

                content = str(args.get("content", args.get("new_string", "")))
                write_key = (
                    name,
                    str(args.get("path", "")),
                    hashlib.sha1(content.encode("utf-8", "replace")).hexdigest(),
                )
                write_count = self.write_counts.get(write_key, 0) + 1
                self.write_counts[write_key] = write_count
                if write_count >= 3:
                    self.write_blocked += 1
                    if self.write_blocked >= 3:
                        self.force_build = True
                    self.emit("coding_repeat_write_blocked", {"path": write_key[1]})
                    return _blocked(
                        request,
                        name,
                        {
                            "ok": False,
                            "note": (
                                "同一文件相同内容已经写入 3 次，不要重复写。"
                                "请继续下一个文件，或立即运行 verify build 检查当前结果。"
                            ),
                        },
                    )
            result = await handler(request)
            if _is_source_write(name, request.tool_call.get("args", {})) and not _failed(result):
                self.source_written = True
                self.write_blocked = 0
            return result
        if name not in GUARDED:
            return await handler(request)
        if (
            self.require_source
            and not self.source_written
            and self.total >= self.explore_limit
        ):
            self.emit(
                "coding_source_required",
                {"tool": name, "total": self.total},
            )
            return _blocked(
                request,
                name,
                {
                    "ok": False,
                    "note": (
                        "空目录生成任务：探查阶段已结束，必须先写工程文件与源码。"
                        "请立即用 write_file 创建 csproj/Program/界面文件，再构建；"
                        "在写出源码前不要继续跑命令或读文件。"
                    ),
                },
            )
        arguments = json.dumps(
            request.tool_call.get("args", {}), sort_keys=True, ensure_ascii=False
        )
        if name == "run_command":
            command = str(request.tool_call.get("args", {}).get("command", ""))
            normalized = re.sub(r"\d+", "#", command)
            norm_key = (name, normalized)
            norm_count = self.norm_counts.get(norm_key, 0) + 1
            self.norm_counts[norm_key] = norm_count
            if norm_count >= self.command_block_at:
                self.emit("coding_repeat_normalized_blocked", {"command": command[:120]})
                return _blocked(
                    request,
                    name,
                    {
                        "ok": False,
                        "note": (
                            "同一类命令（忽略数字差异）已重复执行 10 次，属于空转。"
                            "请立即开始写工程文件并构建，或结束并说明未完成项。"
                        ),
                    },
                )
        key = (name, arguments)
        count = self.counts.get(key, 0) + 1
        self.counts[key] = count
        if count < self.limit:
            result = await handler(request)
            if not _failed(result):
                self.cached[key] = _reusable(result)
            return result
        if key in self.cached:
            if count >= self.read_block_at:
                self.force_action = True
                self.emit("coding_repeat_read_blocked", {"tool": name, "count": count})
                return _blocked(
                    request,
                    name,
                    {
                        "ok": False,
                        "note": (
                            f"同一读取已重复 {count} 次，停止继续读。"
                            "立即写文件/修改代码或运行 verify build。"
                        ),
                    },
                )
            # 重复读取直接返回上次内容，但必须换成当前调用的 tool_call_id，
            # 否则会出现“tool_result 找不到对应 tool_use”的 400。
            self.emit("coding_repeat_cached", {"tool": name, "count": count})
            self.blocked_streak = 0
            cached = self.cached[key]
            return cached.model_copy(update={"tool_call_id": request.tool_call["id"]})
        result = await handler(request)
        if not _failed(result):
            self.cached[key] = _reusable(result)
        return result


def _failed(result):
    return getattr(result, "status", "success") == "error"


def _reusable(result):
    try:
        return result.model_copy(
            update={
                "content": result.text
                or "（同一调用已执行过，返回上次相同结果；请基于该结果继续，不要重复读取。）",
                "additional_kwargs": {**getattr(result, "additional_kwargs", {}), "cached": True},
            }
        )
    except AttributeError:
        return result


def _blocked(request, name, payload):
    return ToolMessage(
        content=json.dumps(payload, ensure_ascii=False),
        tool_call_id=request.tool_call["id"],
        name=name,
        status="error",
    )
