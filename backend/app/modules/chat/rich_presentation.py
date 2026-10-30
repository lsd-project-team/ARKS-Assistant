"""展示协议与既有事实核查之间的适配，无模型、检索或数据库写入。"""

import re
from urllib.parse import quote

from app.modules.chat.rich_content import RichDocument
from app.modules.chat.rich_projection import visual_block_text

MAX_DOCUMENT_BYTES = 262144
FENCE = re.compile(r"(?m)^[ ]{0,3}(`{3,}|~{3,})([^\r\n]*)\r?$")


def rich_documents(content, *, include_incomplete=False):
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
    if include_incomplete and opened is not None and opened[3]:
        yield opened[1], len(content), None


def source_text(source):
    path = quote(source.path, safe="/@._-")
    end = source.end_line or source.start_line
    label = source.path.replace("[", "（").replace("]", "）")
    return f"[{label}:{source.start_line}–{end}](source:{path}#L{source.start_line}-L{end})"


def source_pointers(content):
    """仅遍历白名单引用字段，代码和普通文字不当成元数据。"""

    def visit(blocks):
        for block in blocks:
            if block.type == "overview_grid":
                for item in block.items:
                    if item.source:
                        yield item.source
            elif block.type == "step_flow":
                for step in block.steps:
                    yield from step.sources
            elif block.type == "source_reference":
                yield from block.sources
            elif block.type == "code" and block.source:
                yield block.source
            elif block.type == "collapsible":
                yield from visit(block.blocks)

    for _, _, document in rich_documents(content):
        if document:
            yield from visit(document.blocks)


def block_text(block):
    data = block.model_dump(exclude_none=True, by_alias=True)
    kind = data["type"]
    title = f"### {data['title']}\n\n" if data.get("title") else ""
    if kind in {"text", "markdown"}:
        return data["content"]
    visual = visual_block_text(block)
    if visual is not None:
        return visual
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

        def cell(value):
            return ("—" if value is None else str(value)).replace("|", "\\|").replace("\n", "<br>")

        return (
            title
            + "| "
            + " | ".join(cell(column.label) for column in block.columns)
            + " |\n"
            + "| "
            + " | ".join("---" for _ in block.columns)
            + " |\n"
            + "\n".join(
                "| " + " | ".join(cell(value) for value in row.cells) + " |" for row in block.rows
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


def replace_answer_claims(content, replacements):
    """只降低有具体争议的块；无争议的步骤、表格和引用继续按协议显示。"""
    from app.modules.chat.rich_content import TextBlock

    def replace(text):
        for claim, replacement in replacements:
            text = text.replace(claim, replacement)
        return text

    def rewrite(block):
        if block.type == "collapsible":
            return block.model_copy(update={"blocks": [rewrite(child) for child in block.blocks]})
        projected = block_text(block)
        revised = replace(projected)
        if revised != projected:
            return TextBlock(id=block.id, type="text", content=revised)
        return block

    if not replacements:
        return content
    original = content
    try:
        for start, end, document in reversed(list(rich_documents(content))):
            if document is None:
                continue
            updated = document.model_copy(update={"blocks": [rewrite(b) for b in document.blocks]})
            # 重新验证变换结果；过大的块、跨块争议或无法定位的句子保守降为可核对文字。
            data = updated.model_dump(exclude_none=True, by_alias=True)
            encoded = RichDocument.model_validate(data).model_dump_json(
                exclude_none=True, by_alias=True
            )
            content = content[:start] + "```rich-content\n" + encoded + "\n```" + content[end:]
        # 普通 Markdown 中的争议句直接替换，不把 JSON 键或源码元数据当正文修改。
        cursor, parts = 0, []
        for start, end, _ in rich_documents(content):
            parts += [replace(content[cursor:start]), content[start:end]]
            cursor = end
        result = "".join([*parts, replace(content[cursor:])])
        if any(claim in project_rich_content(result) for claim, _ in replacements):
            return replace(project_rich_content(original))
        return result
    except ValueError:
        return replace(project_rich_content(original))


RICH_CONTENT_GUIDANCE = """
可选回答展示协议（只定义支持的格式，事实核查和检索规则不变）：
由你根据问题和用户要求选择普通 Markdown 或以下结构化组件，不强制卡片、步骤、折叠或固定篇幅。
用户要求纯 Markdown、原文或保留格式时遵从，不转换为结构化组件。
选择结构化组件时，在普通 Markdown 之间使用 rich-content 围栏，内部为 JSON：
{"version":1,"blocks":[...]}。每个块有唯一英文数字/短横线 id 和白名单 type。
需要卡片时，围栏语言必须逐字写成 rich-content，不能写 json；json 围栏只显示示例代码。
格式示例（占位文字必须替换为本题已核实的内容）：
```rich-content
{"version":1,"blocks":[{"id":"steps","type":"step_flow","steps":[{"id":"s1","title":"实际步骤名称","description":"实际步骤说明"}]}]}
```
overview_grid: title?、items:[{id,title,description,icon?,source?}]。
icon 只能为 code/layers/settings/workflow。
step_flow: title?、description?、steps:[{id,title,description,details?,sources?:[源码引用]}]。
source_reference: sources:[源码引用]。
code: content、language?、filename?、start_line?、source?。
table: title?、columns:[{id,label,align?:left/right/center}]、rows:[{id,cells:[字符串/数字/null]}]。
每行列数一致。
diagram: title、description?、layout?:vertical/horizontal。
nodes:[{id,label,description?}]、edges:[{from,to,label?}]。
只列已核实的连接。
collapsible: title、default_open?:布尔、blocks:[子块]；只折叠补充说明，关键结论保持可见。
text: content（Markdown）。
markdown: content，与 text 等价，兼容旧会话；普通段落仍可直接用 Markdown。
chart: title?、chart_type:bar/line/pie、labels:[字符串]、
series:[{id,name,values:[有限数字/null]}]。每个系列数值个数与 labels 一致。
最多500标签/12系列；pie只能一个系列，数值非负；null表示真实缺失，不补零，不能全部缺失。
mermaid: title?、content（Mermaid语法）；也支持普通 mermaid 代码围栏。
禁止 frontmatter、%%配置、click、style、classDef、HTML和外链。
mindmap: title?、nodes:[{id,label,parent_id?}]；最多60节点，唯一根节点省略parent_id。
不能有环或缺失父节点。
file: record_id、name、version?；version是正整数JSON数字，不能加引号或写成字符串。
只能引用本轮实际拿到的资料ID、文件名与版本，不接受路径或URL。
tool_call: tool:{id,name,arguments?,result?,status?:running/pending/success/error,
execution_status?:skipped,skip_reason?,cached?:布尔}。
工具参数与结果必须来自本轮真实工具返回，不推测调用ID、执行状态或成功结果；
前端已展示真实工具事件，通常无需在正文重复生成tool_call。没有实际工具/文件依据时不用相应块。
选择展示方式：单组参数可用Markdown列表，多组参数或方案按共同维度比较用table；
数值趋势或分布且具备真实数据时用chart，分支与依赖关系用mermaid，层级关系较多时用mindmap。
实际操作顺序可用Markdown有序列表或step_flow，简单解释用自然段；用户明确要求的受支持格式优先。
围绕本题选能减少阅读负担的组件，不为使用组件扩写内容，也不把所有回答变成卡片。
表格每列承担明确的比较维度，长解释放在表外；图的节点用简短动作或状态命名，不把整段说明塞进节点。
同一事实在主要图表中表达后，配文只说明关键结论、分支或必要限制，不再逐项复述整张图表。
图表只能采用用户明确提供或实际工具返回的数据，不编造业务数据；缺数据时先说明缺项，不补示例数据。
流程和导图中的项目事实仍需已有源码/资料依据；来源用独立source_reference块或正文引用保留。
源码引用为 {path,start_line,end_line?,version?,source_workspace_id?}。
源码start_line/end_line是正整数；源码version是读取返回的字符串哈希，与file的数字修订号不同。
只能用本轮实际读取的路径、版本和范围，不能伪造。
未知可选字段省略，不写 null（表格单元格、图表缺失值和原始工具参数除外）。
不生成 HTML、JSX、JavaScript、任意ECharts option/formatter、事件、路由或未知字段。
代码块内的代码建议仍可正常展示，不执行模型输出。不强制所有回答 JSON 化。
完整关闭围栏；文字字段≤20000字符，文档≤128块/256KiB，嵌套≤4层。
输出前自行核对JSON字段类型与白名单，不混用源码版本字符串和文件修订数字。
"""
