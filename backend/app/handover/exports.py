"""无需桌面 Word 的 OOXML 导出；包内各条内容读取固定修订。"""

import io
import json
import re
import zipfile
from xml.sax.saxutils import escape

from app.handover.labels import FIELDS, KINDS, STATES, VALUES
from app.handover.rules import linked_ids
from app.handover.word_styles import CONTENT_TYPES, DOCUMENT_RELS, ROOT_RELS, STYLES

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def package_references(store, record_ids):
    queue = [(identifier, None) for identifier in dict.fromkeys(record_ids)]
    references, seen = [], set()
    while queue:
        identifier, version = queue.pop(0)
        row = store.get(identifier, version)
        key = row["id"], row["version"]
        if key in seen:
            continue
        if row["state"] == "archived" or row["kind"] in {"job", "candidate", "package"}:
            raise ValueError("交接包来源有归档或非业务记录，请先复核选择范围")
        seen.add(key)
        if len(seen) > 1000:
            raise ValueError("交接包超过 1000 条版本，请拆分交接范围")
        references.append({"record_id": identifier, "version": row["version"]})
        evidence_ids = set()
        for evidence in row["payload"].get("evidence", []):
            evidence_ids.add(evidence["record_id"])
            queue.append((evidence["record_id"], evidence["version"]))
        for related in linked_ids(row["payload"]) - evidence_ids:
            # 接收记录保留原包的 ID 与版本，避免把旧包递归嵌套进新包。
            if related != row["payload"].get("package_id"):
                queue.append((related, None))
    return references


def xml_text(value):
    # XML 1.0 不允许部分控制字符，附件文本不应损坏整个导出。
    return escape(re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value)))


def paragraph(text, style="Normal"):
    lines = str(text).splitlines() or [""]
    runs = "<w:br/>".join(f'<w:t xml:space="preserve">{xml_text(line)}</w:t>' for line in lines)
    return f'<w:p><w:pPr><w:pStyle w:val="{style}"/></w:pPr><w:r>{runs}</w:r></w:p>'


def word_document(title, introduction, sections):
    body = paragraph(title, "Title") + paragraph(introduction)
    for heading, paragraphs in sections:
        body += paragraph(heading, "Heading1")
        body += "".join(paragraph(text) for text in paragraphs)
    body += (
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
        '<w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr>'
    )
    files = {
        "[Content_Types].xml": CONTENT_TYPES,
        "_rels/.rels": ROOT_RELS,
        "word/_rels/document.xml.rels": DOCUMENT_RELS,
        "word/styles.xml": STYLES,
        "word/document.xml": f'<w:document xmlns:w="{W}"><w:body>{body}</w:body></w:document>',
    }
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(
                name, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + content
            )
    return stream.getvalue()


def record_paragraphs(record, lookup):
    payload = record["payload"]
    output = [
        f"记录 {record['id']}  版本 {record['version']}  {STATES[record['state']]}  "
        f"{VALUES.get(payload.get('origin', ''), '')}"
    ]
    for key, value in payload.items():
        if key not in FIELDS or key == "origin":
            continue
        if key == "content":
            output.append("原始资料保留在附件中；正文预览范围见解析说明。")
            continue
        if isinstance(value, list):
            value = "、".join(lookup.get(item, item) for item in value)
        elif key.endswith("_id"):
            value = lookup.get(value, value)
        formats = {
            "source": "源码文本",
            "zip": "固定源码 ZIP",
            "docx": "Word 文档",
            "pdf": "PDF 文档",
        }
        display = (
            (formats.get(value, value) if key == "format" else VALUES.get(value, value))
            if isinstance(value, str)
            else value
        )
        output.append(f"{FIELDS[key]}：{display or '未填写'}")
    for index, step in enumerate(payload.get("steps", []), 1):
        output.append(
            f"步骤 {index}：{step['action']}\n前提：{step['prerequisite']}\n输出：{step['output']}"
            f"\n验证：{step['verification']}\n停止条件：{step['stop']}\n回退：{step['rollback']}"
            f"\n负责人：{step['owner']}"
        )
    for ref in payload.get("evidence", []):
        output.append(
            f"来源：{lookup.get(ref['record_id'], ref['record_id'])}  v{ref['version']}  "
            f"{ref['locator']}\n原文：{ref['quote'] or '无逐字引文'}"
        )
    if "confirmation" in record:
        confirmation = record["confirmation"]
        output.append(
            f"确认：{confirmation.get('actor', '尚未确认')}  {confirmation.get('role', '')}  "
            f"{confirmation.get('time', '')}\n意见：{confirmation.get('opinion', '待复核')}"
        )
    return output


def export_package(store, identifier, zipped=False, version=None):
    package = store.get(identifier, version)
    if package["kind"] != "package":
        raise ValueError("请选择交接包")
    records = [store.get(ref["record_id"], ref["version"]) for ref in package["payload"]["records"]]
    lookup = {row["id"]: row["title"] for row in records}
    sections = [
        (
            "交接范围与缺项",
            [
                package["payload"]["scope"] or "未填写范围",
                "接收对象：" + (package["payload"]["recipient"] or "未填写"),
                "仍需补充：" + (package["payload"]["gaps"] or "请复核各记录中的未知条件"),
            ],
        )
    ]
    for kind in (
        "framework",
        "training",
        "baseline",
        "source",
        "interview",
        "task",
        "decision",
        "constraint",
        "issue",
        "verification",
        "plan",
        "receipt",
    ):
        selected = [row for row in records if row["kind"] == kind]
        if not selected:
            sections.append((KINDS[kind], ["此交接范围尚无记录，需接收双方确认是否适用或补充。 "]))
        for row in selected:
            sections.append((KINDS[kind] + " " + row["title"], record_paragraphs(row, lookup)))
    content = word_document(
        "全局设备软件交接包",
        f"交接包记录 {package['id']}  版本 {package['version']}  {STATES[package['state']]}。"
        "本包提供接手所需的框架、未完成工作、设计约束、验证证据和接续步骤。"
        "每条记录的确认状态独立显示，接收人应先处理缺项与阻塞条件。",
        sections,
    )
    if not zipped:
        return content
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("handover.docx", content)
        archive.writestr(
            "manifest.json",
            json.dumps({"package": package, "records": records}, ensure_ascii=False, indent=2),
        )
        for row in records:
            if row["kind"] == "source":
                blob = store.blob(row["id"])
                archive.writestr(
                    f"sources/{row['id']}/v{row['version']}/{blob['name']}", blob["content"]
                )
    return stream.getvalue()
