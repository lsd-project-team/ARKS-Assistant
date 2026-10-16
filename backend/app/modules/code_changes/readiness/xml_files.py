"""读取有限大小的项目元数据，不解析外部实体，不导入 targets。"""

import re
from xml.etree import ElementTree

from app.modules.source_analysis.workspace import decode_source

from .paths import MAX_FILE_BYTES, display, local_file


class MetadataError(ValueError):
    pass


def text_file(root, path):
    status = local_file(root, path)
    if status != "exists":
        raise MetadataError(f"文件状态为 {status}，未读取。")
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
    except OSError as error:
        raise MetadataError("无法读取项目元数据。") from error
    if len(data) > MAX_FILE_BYTES:
        raise MetadataError("项目元数据超过 2 MB，未解析。")
    try:
        return decode_source(data)[0]
    except (ValueError, UnicodeError) as error:
        raise MetadataError("项目元数据编码无效，未解析。") from error


def xml_file(root, path):
    text = text_file(root, path)
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.IGNORECASE):
        raise MetadataError("不允许 DTD 或实体声明；未解析该文件。")
    try:
        document = ElementTree.fromstring(text)
    except ElementTree.ParseError as error:
        # ParseError 正文可能包含输入片段，界面只返回位置而不回显原文。
        line, column = getattr(error, "position", (0, 0))
        raise MetadataError(f"XML 格式错误，位置 {line}:{column}。") from error
    return document


def elements(document, tag):
    return (element for element in document.iter() if element.tag.split("}")[-1] == tag)


def child_text(element, tag):
    return next(
        (display(item.text or "") for item in element if item.tag.split("}")[-1] == tag), ""
    )


def values(document, tag):
    return sorted(
        {
            display(item.text.strip())
            for item in elements(document, tag)
            if item.text and item.text.strip()
        }
    )
