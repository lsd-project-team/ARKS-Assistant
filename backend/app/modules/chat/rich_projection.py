"""新增展示块进入事实核查时的文字投影，不改写原消息或执行可视化内容。"""

import json
import re


def fenced_text(content, language=""):
    fence = "`" * max(3, max((len(m[0]) + 1 for m in re.finditer(r"`+", content)), default=3))
    return f"{fence}{language}\n{content}\n{fence}"


def literal_text(value):
    # 图表标签与文件名是纯文字，不能在核查投影里变成可点击的源码/经验引用。
    return str(value).replace("[", r"\[").replace("|", r"\|").replace("\n", " ")


def visual_block_text(block):
    title = f"### {literal_text(block.title)}\n\n" if getattr(block, "title", None) else ""
    if block.type == "chart":
        header = ["项目", *(literal_text(series.name) for series in block.series)]
        rows = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
        for index, label in enumerate(block.labels):
            values = [
                "—" if s.values[index] is None else str(s.values[index]) for s in block.series
            ]
            rows.append("| " + " | ".join([literal_text(label), *values]) + " |")
        return title + "\n".join(rows)
    if block.type == "mermaid":
        return title + fenced_text(block.content, "mermaid")
    if block.type == "mindmap":
        names = {node.id: literal_text(node.label) for node in block.nodes}
        return title + "\n".join(
            f"- {names[node.parent_id]} → {names[node.id]}"
            if node.parent_id
            else f"- {names[node.id]}"
            for node in block.nodes
        )
    if block.type == "file":
        version = f" · v{block.version}" if block.version is not None else ""
        return f"{literal_text(block.name)}（资料 {block.record_id}{version}）"
    if block.type == "tool_call":
        # 参数及结果不参与 Markdown 引用提取，也不能被当成模型已核实的正文结论。
        return "工具调用记录：\n" + fenced_text(
            json.dumps(block.tool.model_dump(exclude_unset=True), ensure_ascii=False), "json"
        )
    return None
