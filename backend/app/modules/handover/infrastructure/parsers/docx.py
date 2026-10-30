from xml.etree import ElementTree as ET

from .archive import safe_archive

NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def parse_docx(data):
    with safe_archive(data) as archive:
        if "word/document.xml" not in archive.namelist():
            raise ValueError("Word 文档缺少正文")
        xml = archive.read("word/document.xml")
        if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
            raise ValueError("不支持带实体声明的文档")
        root = ET.fromstring(xml)
        paragraphs = []
        for paragraph in root.iter(NS + "p"):
            paragraphs.append("".join(node.text or "" for node in paragraph.iter(NS + "t")))
        notes = (
            "按段落及表格单元格顺序解析；页码随排版变化，使用段落定位。"
            "图片、嵌入对象和页眉页脚未解析。"
        )
        content = "\n".join(
            f"[段落 {index}] {text}" for index, text in enumerate(paragraphs, 1) if text.strip()
        )
        return content, "readable" if content.strip() else "needs_ocr", notes, []
