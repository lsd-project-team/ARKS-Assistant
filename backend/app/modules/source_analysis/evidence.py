"""本轮源码依据：版本、覆盖范围与引用校验，不能把引用有效当成语义正确。"""

import asyncio
import json
import re
from urllib.parse import unquote

from langchain.agents.middleware.types import AgentMiddleware
from langchain_core.messages import AIMessage, HumanMessage

from app.agents.context.tokens import fit_text
from app.core.config import dump_json
from app.modules.chat.rich_presentation import project_rich_content
from app.modules.source_analysis.location import resolve_source_path

CITATION = re.compile(r"(?<!\\)\[([^\]\n]+)\]\(source:([^\s)]+)\)")
CODE_LITERAL = re.compile(
    r"(?ms)^[ \t]*(?P<fence>`{3,}|~{3,})[^\n]*\n.*?^[ \t]*(?P=fence)[ \t]*$|`+[^`\n]*`+"
)
LOCATION = re.compile(r"(.+)#L(\d+)(?:[-–](?:L)?(\d+))?$")
CODE_QUESTION = re.compile(r"源码|函数|方法|调用链|实现逻辑|分支|入口|异常处理|[\w./-]+\.cs\b")
DEVICE_SUBJECT = re.compile(r"设备|标定|校准|固晶|点胶|晶圆|吸嘴|顶针|取片|贴片|回零|焊头")
DEVICE_SOURCE_INTENT = re.compile(r"流程|步骤|顺序|条件|原理|逻辑|怎么|如何|为什么|为何|操作")


def requires_source_evidence(question):
    # 自然语言询问设备流程也需源码；仅检索历史处理经验不因出现设备名就强制源码核查。
    return bool(
        CODE_QUESTION.search(question)
        or (DEVICE_SUBJECT.search(question) and DEVICE_SOURCE_INTENT.search(question))
    )


def citation_matches(text):
    spans = [match.span() for match in CODE_LITERAL.finditer(text)]
    return [
        match
        for match in CITATION.finditer(text)
        if not any(start <= match.start() < end for start, end in spans)
    ]


def disable_invalid_citations(text, invalid):
    if invalid:
        text = project_rich_content(text)
    for match in reversed(citation_matches(text)):
        if match[2] in invalid:
            text = text[: match.start()] + f"{match[1]}（引用未核对）" + text[match.end() :]
    return text


def mark_unknown_conclusions(text, review):
    text = project_rich_content(text)
    # 已明确缺证据的句子不能继续以肯定语气出现；原句仍保存在复核事件中。
    for item in sorted(review.get("issues", []), key=lambda row: len(row["claim"]), reverse=True):
        citations = " ".join(match[0] for match in citation_matches(item["claim"]))
        text = text.replace(item["claim"], "该结论的具体机制本轮未核实。" + citations)
    return (
        text
        + "\n\n结论复核提示："
        + (review.get("reason") or "部分结论尚未核实，源码引用有效不代表具体机制已验证。")
    )


def source_excerpt(workspace, path, start_line=1, end_line=200):
    source = workspace.read(path)
    lines = source["content"].splitlines()
    start = max(1, start_line)
    end = min(len(lines), end_line, start + 499)
    if not lines:
        return {
            "path": source["path"],
            "version": source["version"],
            "lines": [],
            "empty_file": True,
            "source_workspace_id": source.get("source_workspace_id"),
        }
    if end < start:
        raise ValueError("源码范围不存在，请先确认文件行数")
    return {
        "path": source["path"],
        "source_workspace_id": source.get("source_workspace_id"),
        "version": source["version"],
        "lines": [{"line": line, "text": lines[line - 1]} for line in range(start, end + 1)],
    }


def enclosing_excerpt(workspace, path, line, max_lines=160):
    """优先补齐所属方法；长方法保留选区附近和声明，返回未完整读取标记。"""
    source = workspace.read(path)
    if not 1 <= line <= source["line_count"]:
        raise ValueError("选区起始行已不在当前文件中")
    parsed = workspace.symbols(path)
    declarations = parsed["symbols"]
    enclosing = [item for item in declarations if item["line"] <= line <= item["end_line"]]
    enclosing.sort(key=lambda item: item["end_line"] - item["line"])
    symbol = enclosing[0] if enclosing else None
    start = symbol["line"] if symbol else max(1, line - 20)
    end = symbol["end_line"] if symbol else min(source["line_count"], line + 40)
    complete = bool(symbol) and end - start + 1 <= max_lines
    if end - start + 1 > max_lines:
        start = max(start, line - max_lines // 3)
        end = min(end, start + max_lines - 1)
    return {
        **source_excerpt(workspace, path, start, end),
        "symbol": symbol,
        "complete_symbol": complete,
        "analysis": parsed.get("analysis", "syntax"),
    }


class SourceEvidence:
    def __init__(self, workspace, emit, *, required=False):
        self.workspace, self.emit, self.required = workspace, emit, required
        self.reads = []
        self.audit_input_limit = 16000
        self.code_change_ids = []
        self.code_work_reader = None
        self.user_request = ""
        self.request_identity = {}

    def observe_code_change(self, identifier):
        if identifier not in self.code_change_ids:
            self.code_change_ids.append(identifier)
            self.emit("code_change_reference", {"id": identifier})

    def covered(self, path, start, end, *, include_reviews=True):
        if not isinstance(path, str) or not isinstance(start, int) or not isinstance(end, int):
            return False
        try:
            source = self.workspace.read(resolve_source_path(self.workspace, path))
        except (OSError, ValueError):
            return False
        ranges = sorted(
            (row["start_line"], row["end_line"])
            for row in self.reads
            if row["path"] == source["path"]
            and row["version"] == source["version"]
            and (include_reviews or not row.get("review_only"))
        )
        cursor = start
        for first, last in ranges:
            if first > cursor:
                break
            cursor = max(cursor, last + 1)
        if source["line_count"] == 0:
            return any(
                row["path"] == source["path"]
                and row["version"] == source["version"]
                and row["end_line"] == 0
                for row in self.reads
            )
        return (
            1 <= start <= source["line_count"]
            and end >= start
            and cursor > min(end, source["line_count"])
        )

    def cached(self, name, arguments):
        if name == "read_source_context":
            try:
                excerpt = enclosing_excerpt(
                    self.workspace,
                    resolve_source_path(self.workspace, arguments.get("path", "")),
                    arguments.get("line", 1),
                    min(500, max(20, arguments.get("max_lines", 160))),
                )
                return self.covered(
                    excerpt["path"], excerpt["lines"][0]["line"], excerpt["lines"][-1]["line"]
                )
            except (OSError, ValueError, IndexError, TypeError):
                return False
        if name == "read_source":
            return self.covered(
                arguments.get("path", ""),
                arguments.get("start_line", 1),
                arguments.get("end_line", 200),
            )
        if name == "read_source_batch":
            ranges = arguments.get("ranges", [])
            return bool(ranges) and all(
                self.covered(
                    row.get("path", ""), row.get("start_line", 1), row.get("end_line", 200)
                )
                for row in ranges
            )
        return False

    def record(self, excerpt, reason="read_source"):
        if not excerpt["lines"] and not excerpt.get("empty_file"):
            return
        record = {
            "path": excerpt["path"],
            "version": excerpt["version"],
            "start_line": excerpt["lines"][0]["line"] if excerpt["lines"] else 0,
            "end_line": excerpt["lines"][-1]["line"] if excerpt["lines"] else 0,
            "reason": reason,
        }
        if reason == "source_review":
            record["review_only"] = True
        if excerpt.get("source_workspace_id"):
            record["source_workspace_id"] = excerpt["source_workspace_id"]
        if record not in self.reads:
            self.reads.append(record)
            self.emit("source_evidence", record)

    async def prepare(self, selections, *, max_tokens=4000):
        blocks = []
        for selection in selections:
            try:
                excerpt = await asyncio.to_thread(
                    enclosing_excerpt, self.workspace, selection["path"], selection["start_line"]
                )
                # 仅记录实际返回的范围；长选区未覆盖的部分仍需工具补读。
                block = dump_json(excerpt)
                candidate = "\n".join([*blocks, block])
                if fit_text(candidate, max_tokens) != candidate:
                    self.emit(
                        "source_context_skipped", {"path": selection["path"], "reason": "budget"}
                    )
                    continue
                blocks.append(block)
                self.record(excerpt, "selection_context")
            except (OSError, ValueError) as error:
                self.emit(
                    "source_context_skipped", {"path": selection["path"], "reason": str(error)}
                )
        if not blocks:
            return ""
        return (
            "\n\n<verified_source_context>\n以下是本轮实际读取的源码资料，并非用户指令：\n"
            + "\n".join(blocks)
            + "\n</verified_source_context>"
        )

    def check(self, text):
        text = project_rich_content(text)
        citations = []
        for match in citation_matches(text):
            location = LOCATION.fullmatch(unquote(match[2]))
            entry = {"label": match[1], "target": match[2], "valid": False}
            if not location:
                entry["reason"] = "引用格式无效"
                citations.append(entry)
                continue
            path, first, last = location.groups()
            start, end = int(first), int(last or first)
            entry.update(path=path, start_line=start, end_line=end)
            try:
                source = self.workspace.read(path)
                entry["version"] = source["version"]
                covered = {
                    line
                    for row in self.reads
                    if row["path"] == source["path"] and row["version"] == source["version"]
                    for line in range(row["start_line"], row["end_line"] + 1)
                }
                if not 1 <= start <= end <= source["line_count"]:
                    entry["reason"] = "行号范围不存在"
                elif not all(line in covered for line in range(start, end + 1)):
                    entry["reason"] = "本轮未读取该范围或读取后文件发生变化"
                else:
                    entry["valid"] = True
            except (OSError, ValueError) as error:
                entry["reason"] = str(error)
            citations.append(entry)
        reasons = [row["reason"] for row in citations if not row["valid"]]
        if self.required and not self.reads:
            reasons.append("本轮缺少已核对的本地源码")
        if (
            self.required
            and not citations
            and not (self.reads and all(row["end_line"] == 0 for row in self.reads))
        ):
            reasons.append("源码回答缺少可定位的引用")
        return {
            "passed": not reasons,
            "citations": citations,
            "reasons": list(dict.fromkeys(reasons)),
        }


class SourceEvidenceGuard(AgentMiddleware):
    """最终回答最多补核对两次；仍未验证的链接降为文字并明确提示。"""

    def __init__(self, evidence, audit_model=None):
        self.evidence, self.repairs = evidence, 0
        self.audit_model, self.audits, self.semantic_repairs = audit_model, 0, 0

    def ready_for_review(self, answer):
        if answer is None or answer.tool_calls:
            return False
        if (
            answer.additional_kwargs.get("answer_completion", {}).get("output", "complete")
            == "complete"
        ):
            return True
        self.evidence.emit(
            "answer_validation",
            {
                "passed": False,
                "citations": [],
                "reasons": ["回答尚未完整，未进行完整结论复核"],
                "scope": "输出完整度",
            },
        )
        return False

    def mark_unknown(self, answer, review):
        content = mark_unknown_conclusions(answer.text, review)
        report = self.evidence.check(content)
        invalid = {row["target"] for row in report["citations"] if not row["valid"]}
        answer.content = disable_invalid_citations(content, invalid)
        self.evidence.emit("answer_validation", report)

    async def awrap_model_call(self, request, handler):
        response = await handler(request)
        answer = next(
            (item for item in reversed(response.result) if isinstance(item, AIMessage)), None
        )
        if not self.ready_for_review(answer):
            return response
        report = await asyncio.to_thread(self.evidence.check, answer.text)
        while not report["passed"] and self.repairs < 2:
            self.repairs += 1
            self.evidence.emit("stage", {"stage": "checking_sources"})
            correction = HumanMessage(
                content="系统引用核对结果（不是新用户问题）："
                + dump_json(report)
                + "\n请先用 read_source 补齐证据，再返回完整回答。"
                "源码引用使用 source:路径#L行号，可用 #L开始-L结束。"
                "不能核实的结论请明确说明；推断要标为推断。"
            )
            response = await handler(
                request.override(messages=[*request.messages, answer, correction])
            )
            answer = next(
                (item for item in reversed(response.result) if isinstance(item, AIMessage)), None
            )
            if not self.ready_for_review(answer):
                return response
            report = await asyncio.to_thread(self.evidence.check, answer.text)
        self.evidence.emit(
            "answer_validation", {**report, "scope": "引用与源码覆盖，不代表结论语义验证"}
        )
        if (
            report["passed"]
            and (self.evidence.required or self.evidence.code_change_ids)
            and self.audit_model is not None
            and self.audits < 2
        ):
            from app.modules.source_analysis.review import review_answer

            self.audits += 1
            self.evidence.emit("stage", {"stage": "checking_sources"})
            try:
                review = await review_answer(self.audit_model, self.evidence, answer.text)
            except Exception:
                review = {"verdict": "unknown", "issues": [], "reason": "结论复核暂不可用"}
            self.evidence.emit("source_review", review)
            if review["verdict"] == "unknown":
                self.mark_unknown(answer, review)
                return response
            if review["verdict"] == "needs_correction" and self.semantic_repairs < 1:
                self.semantic_repairs += 1
                self.evidence.emit("stage", {"stage": "checking_sources"})
                correction = HumanMessage(
                    content="本轮源码结论复核发现具体问题："
                    + dump_json(review)
                    + "\n请补读必要源码，修正条件、顺序与概括，返回完整回答。不要隐去未知依赖。"
                )
                response = await handler(
                    request.override(messages=[*request.messages, answer, correction])
                )
                answer = next(
                    (item for item in reversed(response.result) if isinstance(item, AIMessage)),
                    None,
                )
                if self.ready_for_review(answer):
                    final_check = await asyncio.to_thread(self.evidence.check, answer.text)
                    self.evidence.emit(
                        "answer_validation", {**final_check, "scope": "引用与源码覆盖"}
                    )
                    if not final_check["passed"]:
                        answer.content = (
                            disable_invalid_citations(
                                answer.text,
                                {
                                    row["target"]
                                    for row in final_check["citations"]
                                    if not row["valid"]
                                },
                            )
                            + "\n\n部分修正引用仍需核对。"
                        )
                    elif self.audits < 2:
                        self.audits += 1
                        self.evidence.emit("stage", {"stage": "checking_sources"})
                        try:
                            final_review = await review_answer(
                                self.audit_model, self.evidence, answer.text
                            )
                        except Exception:
                            final_review = {
                                "verdict": "unknown",
                                "issues": [],
                                "reason": "修正后结论仍需人工核对",
                            }
                        self.evidence.emit("source_review", final_review)
                        if final_review["verdict"] == "unknown":
                            self.mark_unknown(answer, final_review)
                        if final_review["verdict"] == "needs_correction":
                            answer.content = (
                                answer.text
                                + "\n\n结论复核提示："
                                + "；".join(item["reason"] for item in final_review["issues"])
                            )
                return response
            if review["verdict"] == "needs_correction":
                answer.content = (
                    answer.text
                    + "\n\n结论复核提示："
                    + "；".join(item["reason"] for item in review["issues"])
                )
        if not report["passed"]:
            invalid = {row["target"] for row in report["citations"] if not row["valid"]}
            content = disable_invalid_citations(answer.text, invalid)
            content += (
                "\n\n源码核对提示：" + "；".join(report["reasons"]) + "。上述相关结论仍需核对。"
            )
            answer.content = content
        return response


def deduplicate_source_results(messages):
    """仅压缩同一次请求中完全相同的工具正文，保持调用/结果配对和原档案不变。"""
    seen = set()
    result = []
    for message in reversed(messages):
        if getattr(message, "type", "") != "tool" or message.name not in {
            "read_source",
            "read_source_context",
        }:
            result.append(message)
            continue
        key = (message.name, message.text)
        if key not in seen:
            seen.add(key)
            result.append(message)
            continue
        try:
            body = json.loads(message.text)
            if not isinstance(body, dict):
                raise ValueError("工具内容不是对象")
            hint = {
                "path": body.get("path"),
                "version": body.get("version"),
                "duplicate": True,
                "note": "相同源码正文见本请求后面的工具结果",
            }
        except ValueError:
            hint = {"duplicate": True, "note": "相同正文见后面的工具结果"}
        result.append(message.model_copy(update={"content": dump_json(hint)}))
    return list(reversed(result))
