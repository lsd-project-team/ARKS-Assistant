"""展示协议与既有事实核查之间的适配，无模型、检索或数据库写入。"""

import re
from urllib.parse import quote

from app.modules.chat.rich_content import RichDocument

MAX_DOCUMENT_BYTES = 262144
FENCE = re.compile(r"(?m)^[ ]{0,3}(`{3,}|~{3,})([^\r\n]*)\r?$")


def rich_documents(content):
    opened, count = None, 0
    for match in FENCE.finditer(content):
        marker, info = match[1], match[2].strip()
        if opened is None:
            opened = (marker, match.start(), match.end() + 1, info == "rich-content" and count < 32)
            continue
        previous, start, body, rich = opened
        if marker[0] != previous[0] or len(marker) < len(previous) or info:
            continue
        if rich:
            raw = content[body : match.start()]
            try:
                if len(raw.encode("utf-8")) > MAX_DOCUMENT_BYTES:
                    raise ValueError("结构化内容超过限制")
                document = RichDocument.model_validate_json(raw)
            except ValueError:
                document = None
            yield start, match.end(), document
            count += 1
        opened = None


def source_text(source):
    path = quote(source.path, safe="/@._-")
    end = source.end_line or source.start_line
    return f"[{source.path}:{source.start_line}–{end}](source:{path}#L{source.start_line}-L{end})"


def block_text(block):
    data = block.model_dump(exclude_none=True, by_alias=True)
    kind = data["type"]
    title = f"### {data['title']}\n\n" if data.get("title") else ""
    if kind == "text":
        return data["content"]
    if kind == "overview_grid":
        return title + "\n".join(
            f"- **{item.title}**：{item.description}"
            + (f" · {item.status}" if item.status else "")
            + (" " + source_text(item.source) if item.source else "")
            for item in block.items
        )
    if kind == "step_flow":
        return (
            title
            + (block.description or "")
            + "\n\n"
            + "\n\n".join(
                f"{index}. **{step.title}**：{step.description}\n"
                + (step.details or "")
                + " ".join(source_text(source) for source in step.sources)
                for index, step in enumerate(block.steps, 1)
            )
        )
    if kind == "source_reference":
        return " ".join(source_text(source) for source in block.sources)
    if kind == "code":
        # 避免代码内容中的围栏逃逸，影响原有证据解析。
        fence = "`" * max(
            3, max((len(m[0]) + 1 for m in re.finditer(r"`+", block.content)), default=3)
        )
        return (
            (block.filename or "")
            + f"\n{fence}{block.language or ''}\n{block.content}\n{fence}\n"
            + (source_text(block.source) if block.source else "")
        )
    if kind == "table":
        return (
            title
            + " | ".join(column.label for column in block.columns)
            + "\n"
            + "\n".join(
                " | ".join("—" if cell is None else str(cell) for cell in row.cells)
                for row in block.rows
            )
        )
    if kind == "diagram":
        names = {node.id: node.label for node in block.nodes}
        return (
            title
            + (block.description or "")
            + "\n"
            + "\n".join(
                f"- {node.label}" + (f"：{node.description}" if node.description else "")
                for node in block.nodes
            )
            + "\n"
            + "\n".join(
                f"{names[edge.from_]} → {names[edge.to]}"
                + (f"：{edge.label}" if edge.label else "")
                for edge in block.edges
            )
        )
    if kind == "collapsible":
        return title + "\n\n".join(block_text(child) for child in block.blocks)
    return ""


def project_rich_content(content):
    """已校验展示语义进入原核查；非法块不能作为可信引用。"""
    for start, end, document in reversed(list(rich_documents(content))):
        if document is not None:
            content = (
                content[:start]
                + "\n\n".join(block_text(block) for block in document.blocks)
                + content[end:]
            )
    return content


RICH_CONTENT_GUIDANCE = """
可选展示协议（只影响排版，事实核查和检索规则不变）：
简单问答、原文提取、含调试记录/资料引用的回答继续用普通 Markdown。
当答案确有功能概览、顺序步骤或对比时，可以在普通 Markdown 之间使用 rich-content 围栏，内部为 JSON：
{"version":1,"blocks":[...]}。每个块有唯一英文数字/短横线 id 和白名单 type。
overview_grid: title?、items:[{id,title,description,icon?,source?}]。
icon 只能为 code/layers/settings/workflow。
step_flow: title?、description?、steps:[{id,title,description,details?,sources?:[源码引用]}]。
保留关键前置条件、异常、停止与保存。
source_reference: sources:[源码引用]。
code: content、language?、filename?、start_line?、source?。
table: title?、columns:[{id,label,align?:left/right/center}]、rows:[{id,cells:[字符串/数字/null]}]。
每行列数一致。
diagram: title、description?、layout?:vertical/horizontal。
nodes:[{id,label,description?}]、edges:[{from,to,label?}]。
只列已核实的连接。
collapsible: title、default_open?:布尔、blocks:[子块]；只折叠补充说明，关键结论保持可见。
text: content（Markdown）。
源码引用为 {path,start_line,end_line?,version?,source_workspace_id?}。
只能用本轮实际读取的路径、版本和范围，不能伪造。
未知可选字段省略，不写 null。不生成 HTML、事件、路由或未知字段。不强制所有回答 JSON 化。
完整关闭围栏；文字字段≤20000字符，文档≤128块/256KiB，嵌套≤4层。
"""
