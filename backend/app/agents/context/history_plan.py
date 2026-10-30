"""历史的请求级投影：保留用户消息和近期轮次，候选始终按完整工具链分组。"""

import re
from dataclasses import dataclass, field

from langchain_core.messages import HumanMessage

from app.agents.context.summary_text import summary_parts

RECENT_TURNS = 6
OPTIONAL_SECTIONS = {"已确认结论", "源码依据"}


def message_data(message):
    result = {"role": message.type, "content": message.text}
    if getattr(message, "tool_calls", None):
        result["tool_calls"] = message.tool_calls
    return result


@dataclass
class SummaryView:
    message: object
    prefix: str
    suffix: str
    sections: list = field(default_factory=list)

    def render(self, selected):
        blocks = []
        for header, parts in self.sections:
            content = "".join(
                text for identifier, text in parts if identifier is None or identifier in selected
            )
            if content:
                blocks.append(header + content)
        return self.message.model_copy(
            update={"content": self.prefix + "".join(blocks) + self.suffix}
        )


class HistoryPlan:
    def __init__(self, messages, recent_turns=RECENT_TURNS):
        self.slots, self.candidates, self.protected, self.recent = [], [], [], []
        summaries = {
            i: summary_parts(row.text)
            if i == 0
            and isinstance(row, HumanMessage)
            and any(isinstance(later, HumanMessage) for later in messages[1:])
            else ("", "", "")
            for i, row in enumerate(messages)
        }
        user_indices = [
            i
            for i, row in enumerate(messages)
            if isinstance(row, HumanMessage) and not summaries[i][0]
        ]
        cutoff = user_indices[-recent_turns] if len(user_indices) > recent_turns else 0
        group = []
        request_index = None

        def flush():
            if group:
                identifier = self.add(
                    "dialogue",
                    {
                        "request_index": request_index,
                        "messages": [message_data(row) for row in group],
                    },
                )
                self.slots.append((identifier, list(group)))
                group.clear()

        for i, message in enumerate(messages):
            prefix, body, suffix = summaries[i]
            if prefix:
                flush()
                view = self.summary(message, prefix, body, suffix)
                self.slots.append((None, view))
            elif i >= cutoff:
                flush()
                self.slots.append((None, [message]))
                self.recent.append(message_data(message))
            elif isinstance(message, HumanMessage) or message.type == "system":
                flush()
                self.slots.append((None, [message]))
                self.protected.append(message_data(message))
                request_index = len(self.protected) - 1
            else:
                group.append(message)
        flush()

    def add(self, kind, content):
        identifier = len(self.candidates) + 1
        self.candidates.append({"id": identifier, "kind": kind, **content})
        return identifier

    def summary(self, message, prefix, body, suffix):
        view = SummaryView(message, prefix, suffix)
        headings = list(re.finditer(r"(?m)^##[ \t]+([^\n]+)\n?", body))
        if not headings:
            # 手动纠正的自由格式摘要无法可靠区分约束，保守保留，不能当作无关事实删掉。
            view.sections.append(("", [(None, body)]))
        else:
            view.sections.append(("", [(None, body[: headings[0].start()])]))
            for n, match in enumerate(headings):
                end = headings[n + 1].start() if n + 1 < len(headings) else len(body)
                title, text = match[1].strip(), body[match.end() : end]
                if title in OPTIONAL_SECTIONS:
                    parts = [
                        (
                            None
                            if line.strip() == "无"
                            else self.add("summary", {"section": title, "content": line}),
                            line,
                        )
                        for line in text.splitlines(keepends=True)
                        if line.strip()
                    ]
                else:
                    parts = [(None, text)]
                view.sections.append((match[0], parts))
        protected = view.render(set()).text
        self.protected.append({"role": "summary", "content": protected})
        return view

    def render(self, selected):
        result = []
        for identifier, value in self.slots:
            if isinstance(value, SummaryView):
                result.append(value.render(selected))
            elif identifier is None or identifier in selected:
                result.extend(value)
        return result
