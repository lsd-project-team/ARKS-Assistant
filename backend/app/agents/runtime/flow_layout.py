"""流程回答的展示约束；只校验组织与引用，事实仍交给原核查链路。"""

import re
from urllib.parse import unquote

from pydantic import ValidationError

from app.core.config import dump_json
from app.modules.chat.rich_content import RichDocument
from app.modules.chat.rich_presentation import block_text, project_rich_content, rich_documents

MAIN_LIMIT = 1400
SOURCE_LINK = re.compile(r"\[[^\]\n]*\]\(source:([^\s)]+)\)")
PLAIN_REQUEST = re.compile(r"纯\s*Markdown|不要卡片|不用卡片|不要结构化|不要JSON", re.I)


def source_targets(content):
    targets = set()
    for match in SOURCE_LINK.finditer(project_rich_content(content)):
        target = unquote(match[1])
        location = re.fullmatch(r"(.+)#L(\d+)(?:[-–]L?(\d+))?", target)
        if location:
            path, start, end = location.groups()
            target = f"{path}#L{int(start)}-L{int(end or start)}"
        targets.add(target)
    return targets


def source_catalog(content):
    """给整理器可直接复制的合法引用对象，避免从路径和行号字符串重新猜协议。"""
    result = []
    for target in sorted(source_targets(content)):
        location = re.fullmatch(r"(.+)#L(\d+)-L(\d+)", target)
        if location:
            path, start, end = location.groups()
            result.append({"path": path, "start_line": int(start), "end_line": int(end)})
    return result


def visible_block(block):
    if block.type == "collapsible":
        return (
            block.title + "\n" + "\n".join(visible_block(child) for child in block.blocks)
            if block.default_open
            else block.title
        )
    if block.type == "step_flow":
        # 步骤详情默认折叠；不把已妥善安放的补充实现重复算入主阅读区。
        block = block.model_copy(
            update={"steps": [step.model_copy(update={"details": None}) for step in block.steps]}
        )
    return block_text(block)


def main_text(content):
    for start, end, document in reversed(list(rich_documents(content))):
        if document is not None:
            content = (
                content[:start]
                + "\n\n".join(visible_block(block) for block in document.blocks)
                + content[end:]
            )
    # JSON 字段、完整路径与快照元数据不是用户读到的说明，不以其长度误判正文。
    return SOURCE_LINK.sub("", content).strip()


def has_main_steps(content):
    def contains(blocks):
        return any(
            (block.type == "step_flow" and bool(block.steps))
            or (block.type == "collapsible" and block.default_open and contains(block.blocks))
            for block in blocks
        )

    return any(doc and contains(doc.blocks) for _, _, doc in rich_documents(content))


def layout_problem(content, original, question):
    if PLAIN_REQUEST.search(question) and list(rich_documents(content)):
        return "用户要求纯Markdown，不能包含rich-content围栏"
    for start, end, doc in rich_documents(content):
        if doc is None:
            try:
                RichDocument.model_validate_json("\n".join(content[start:end].splitlines()[1:-1]))
            except ValidationError as error:
                details = "; ".join(
                    ".".join(str(part) for part in row["loc"]) + ": " + row["msg"]
                    for row in error.errors(include_input=False, include_url=False)[:3]
                )
                return "结构化围栏无效，请按展示协议修正：" + details
            return "结构化围栏超过展示协议限制"
    if len(content) < 20 or not main_text(content) or len(main_text(content)) > MAIN_LIMIT:
        return "主阅读区过长或内容为空；精简主线，把补充实现放入默认收起的区域"
    targets = source_targets(content)
    if not targets or not targets <= source_targets(original):
        return "只能使用原稿已有的源码引用，不新建路径或行号"
    if not PLAIN_REQUEST.search(question) and (
        len(main_text(content)) >= 200 or has_supplements(content)
    ):
        if not has_main_steps(content):
            return "主流程应使用合法的 step_flow，不能全部藏在折叠区或只输出普通长列表"
    return ""


def has_supplements(content):
    return any(
        doc and any(block.type == "collapsible" for block in doc.blocks)
        for _, _, doc in rich_documents(content)
    )


def preserve_unorganized(content, *, plain=False):
    notice = "这次回答未完成流程整理。完整原稿保留在下方供核对，也可以重新生成。"
    projected = project_rich_content(content)
    if plain:
        return notice + "\n\n" + projected
    if len(projected) > 20000:
        # 超过协议单块上限时保留原文并明确失败，不截断事实、代码或引用。
        return notice + "\n\n" + content
    document = {
        "version": 1,
        "blocks": [
            {
                "id": "unorganized-draft",
                "type": "collapsible",
                "title": "查看完整原稿（流程尚未整理）",
                "blocks": [{"id": "original-text", "type": "text", "content": projected}],
            }
        ],
    }
    return notice + "\n\n```rich-content\n" + dump_json(document) + "\n```"
