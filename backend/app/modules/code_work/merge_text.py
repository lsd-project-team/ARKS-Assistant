"""三方文本合并：保留双方非重叠编辑，重叠时交给用户明确处理。"""

import re
from difflib import SequenceMatcher
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

from app.modules.code_work.files import PROJECT, encode_text
from app.modules.source_analysis.workspace import decode_source


def edits(before, after):
    return [
        (a, b, after[c:d])
        for tag, a, b, c, d in SequenceMatcher(None, before, after, autojunk=False).get_opcodes()
        if tag != "equal"
    ]


def overlaps(left, right):
    a, b, _ = left
    c, d, _ = right
    if a == b:
        return c <= a <= d
    if c == d:
        return a <= c <= b
    return max(a, c) < min(b, d)


def merge(base, source, workspace):
    if source == workspace or workspace == base:
        return source
    if source == base:
        return workspace
    if base is None or source is None or workspace is None:
        raise ValueError("同名新增文件或删除与修改冲突")
    original, left, right = [
        decode_source(data)[0].replace("\r\n", "\n").splitlines(keepends=True)
        for data in (base, source, workspace)
    ]
    source_edits, work_edits = edits(original, left), edits(original, right)
    for first in source_edits:
        for second in work_edits:
            if first != second and overlaps(first, second):
                raise ValueError("原工程与副本修改了重叠内容")
    combined = source_edits + [item for item in work_edits if item not in source_edits]
    result = list(original)
    for start, end, replacement in sorted(
        combined, key=lambda item: (item[0], item[1]), reverse=True
    ):
        result[start:end] = replacement
    return encode_text("".join(result), source)


def include_files(data, files):
    """只给经典C#项目补充缺少的Compile项，保留原编码、换行和排版。"""
    text = decode_source(data)[0]
    root = ET.fromstring(text)
    if root.attrib.get("Sdk") and not any(
        item.tag.endswith("EnableDefaultCompileItems") and item.text == "false"
        for item in root.iter()
    ):
        return data
    included = {
        item.attrib.get("Include", "").replace("\\", "/").lower()
        for item in root.iter()
        if item.tag.rsplit("}", 1)[-1] == "Compile"
    }
    missing = [
        path[len(PROJECT) + 1 :]
        for path in files
        if path.startswith(PROJECT + "/") and path[len(PROJECT) + 1 :].lower() not in included
    ]
    if not missing:
        return data
    newline = "\r\n" if "\r\n" in text else "\n"
    additions = "".join(
        '    <Compile Include="'
        + escape(path.replace("/", "\\"), {'"': "&quot;"})
        + '" />'
        + newline
        for path in sorted(missing)
    )
    groups = list(re.finditer(r"<ItemGroup\b[^>]*>.*?</ItemGroup>", text, re.DOTALL))
    group = next((item for item in groups if "<Compile " in item.group()), None)
    if group:
        position = text.rfind("</ItemGroup>", group.start(), group.end())
        text = text[:position] + additions + "  " + text[position:]
    else:
        block = "  <ItemGroup>" + newline + additions + "  </ItemGroup>" + newline
        if "</Project>" in text:
            text = text.replace("</Project>", block + "</Project>", 1)
        else:
            text = re.sub(
                r"<Project([^>]*)/>",
                lambda match: "<Project" + match[1] + ">" + newline + block + "</Project>",
                text,
                count=1,
            )
    ET.fromstring(text)
    return encode_text(text, data)
