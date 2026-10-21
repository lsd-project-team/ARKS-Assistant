"""停用未核对的引用时保留展示结构，不能把一个坏链接扩大为整篇降级。"""

from pydantic import BaseModel

from app.modules.chat.rich_content import RichDocument, SourcePointer
from app.modules.chat.rich_presentation import rich_documents, source_text

PROSE_FIELDS = {"content", "title", "description", "details", "label", "cells"}
NESTED_FIELDS = {
    "source",
    "sources",
    "blocks",
    "items",
    "steps",
    "columns",
    "rows",
    "nodes",
    "edges",
}


def rewrite_source_citations(content, rewrite_markdown, invalid_source):
    """只改正文链接和白名单来源字段；代码、文件名及快照元数据保持原样。"""
    cursor, parts = 0, []
    for start, end, document in rich_documents(content):
        parts.append(rewrite_markdown(content[cursor:start]))
        cursor = end
        if document is None:
            parts.append(content[start:end])
            continue
        notes = []

        def rewrite(value, *, notes=notes):
            if isinstance(value, SourcePointer):
                if invalid_source(value):
                    notes.append(rewrite_markdown(source_text(value)))
                    return None
                return value
            if isinstance(value, BaseModel):
                changes = {}
                for name in type(value).model_fields:
                    if name not in PROSE_FIELDS | NESTED_FIELDS:
                        continue
                    if name == "content" and getattr(value, "type", None) == "code":
                        continue
                    changes[name] = rewrite(getattr(value, name))
                return value.model_copy(update=changes)
            if isinstance(value, list):
                # 表格中的原始 null 单元格必须保留，只删除被停用的 SourcePointer。
                result = []
                for item in value:
                    revised = rewrite(item)
                    if revised is not None or item is None:
                        result.append(revised)
                return result
            return rewrite_markdown(value) if isinstance(value, str) else value

        updated = rewrite(document)
        if updated == document:
            parts.append(content[start:end])
            continue
        data = updated.model_dump(exclude_none=True, exclude_unset=True, by_alias=True)
        encoded = RichDocument.model_validate(data).model_dump_json(
            exclude_none=True, exclude_unset=True, by_alias=True
        )
        parts.append("```rich-content\n" + encoded + "\n```")
        # 注记放在结构化块旁，不挤占有长度限制的步骤说明，也不保留可点击的坏引用。
        if notes:
            parts.append("\n\n" + "\n\n".join(dict.fromkeys(notes)))
    return "".join([*parts, rewrite_markdown(content[cursor:])])
