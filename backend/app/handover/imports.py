"""只解析文档或固定源码 ZIP，不运行附件、宏或项目构建。"""

import hashlib
import io
import re
import stat
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree as ET

from pypdf import PdfReader

from app.workspace import decode_source

MAX_UPLOAD = 32 * 1024 * 1024
MAX_EXPANDED = 64 * 1024 * 1024
MAX_TEXT = 100000
NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def safe_archive(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError("附件不是有效的 ZIP 或 Word 文档") from error
    entries = archive.infolist()
    if len({item.filename for item in entries}) != len(entries):
        archive.close()
        raise ValueError("压缩包存在重复文件名，无法可靠定位固定版本")
    if len(entries) > 2000 or sum(item.file_size for item in entries) > MAX_EXPANDED:
        archive.close()
        raise ValueError("压缩包展开后超过 64 MB 或 2000 项，请缩小交接范围")
    for item in entries:
        path = PurePosixPath(item.filename.replace("\\", "/"))
        if (
            path.is_absolute()
            or ".." in path.parts
            or ":" in item.filename
            or stat.S_ISLNK(item.external_attr >> 16)
        ):
            archive.close()
            raise ValueError("压缩包包含不安全路径或符号链接")
        if item.flag_bits & 1:
            archive.close()
            raise ValueError("暂不支持加密压缩包")
    return archive


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


def parse_pdf(data):
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ValueError("暂不支持加密 PDF")
        if len(reader.pages) > 300:
            raise ValueError("PDF 超过 300 页，请按范围拆分")
        pages, empty = [], []
        for index, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            pages.append(f"[第 {index} 页]\n{text}")
            if not text.strip():
                empty.append(index)
        status = "needs_ocr" if len(empty) == len(pages) else "partial" if empty else "readable"
        notes = (
            f"共 {len(pages)} 页；无可提取文字页：{empty or '无'}。"
            "不执行 OCR，图形与扫描内容须人工补充。"
        )
        return "\n\n".join(pages), status, notes, []
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("PDF 解析失败，请导出为普通文本 PDF 后重试") from error


def parse_snapshot(data):
    files, previews, skipped = [], [], 0
    with safe_archive(data) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            raw = archive.read(item)
            path = item.filename.replace("\\", "/")
            files.append(
                {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "size": str(len(raw))}
            )
            try:
                if len(raw) > 2_000_000:
                    raise ValueError("大文件")
                text, _ = decode_source(raw)
                previews.append(f"[文件 {path}]\n{text[:10000]}")
                skipped += int(len(text) > 10000)
            except ValueError:
                skipped += 1
    notes = (
        f"固定源码快照，共 {len(files)} 文件。每文件预览最多 10000 字；{skipped} 项未完整预览。"
        "完整原件可下载，文件哈希用于比对，不代表功能验证通过。"
    )
    return "\n\n".join(previews), "readable", notes, files


def import_source(store, data, filename, metadata, actor):
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError("附件不能为空且不能超过 32 MB")
    filename = PurePosixPath(filename.replace("\\", "/")).name[:250]
    extension = PurePosixPath(filename).suffix.lower()
    parser = {".docx": parse_docx, ".pdf": parse_pdf, ".zip": parse_snapshot}.get(extension)
    if parser:
        content, status, notes, files = parser(data)
    elif extension in {
        ".txt",
        ".md",
        ".cs",
        ".cpp",
        ".c",
        ".h",
        ".json",
        ".yaml",
        ".yml",
        ".xml",
        ".ini",
        ".log",
    }:
        content, _ = decode_source(data)
        status, notes, files = "readable", "以行号定位；未执行附件内容。", []
    else:
        raise ValueError("支持 DOCX、文本 PDF、源码 ZIP 和常见文本文件；旧版 DOC 请转为 DOCX")
    if len(content) > MAX_TEXT:
        content = content[:MAX_TEXT]
        notes += " 正文预览超过 100000 字，已截断；完整附件仍保留。"
        if extension != ".zip":
            status = "partial"
    payload = {
        **metadata,
        "origin": "import",
        "filename": filename,
        "format": extension.lstrip("."),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content": content,
        "parse_status": status,
        "parse_notes": notes,
        "files": files,
    }
    return store.create(
        "source",
        filename[:200],
        payload,
        actor,
        blob={
            "name": filename,
            "media_type": "application/octet-stream",
            "sha256": payload["sha256"],
            "content": data,
        },
    )


def import_text(store, title, content, metadata, actor):
    # 正文不裁剪、不规范化换行，保留聊天记录、缩进和原始引用；超限由入口拒绝。
    raw = content.encode("utf-8")
    filename = re.sub(r'[\\/:*?"<>|\r\n]', "_", title) + ".txt"
    payload = {
        **metadata,
        "origin": "human",
        "filename": filename,
        "format": "text",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "content": content,
        "parse_status": "readable",
        "parse_notes": "直接输入的文本，原文完整保存；以行号定位。",
    }
    return store.create(
        "source",
        title,
        payload,
        actor,
        blob={
            "name": filename,
            "media_type": "text/plain; charset=utf-8",
            "sha256": payload["sha256"],
            "content": raw,
        },
    )


def capture_source(store, workspace, path, metadata, actor):
    file = workspace.read(path)
    content = file["content"]
    if not content.strip():
        raise ValueError("源码文件没有可读内容，请选择实际源码文件")
    raw = workspace.resolve(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != file["version"]:
        raise ValueError("读取期间源码已变化，请重试")
    payload = {
        **metadata,
        "origin": "import",
        "filename": path,
        "source_workspace_id": file["source_workspace_id"],
        "path": path,
        "format": "source",
        "sha256": file["version"],
        "content": content[:MAX_TEXT],
        "parse_status": "partial" if len(content) > MAX_TEXT else "readable",
        "parse_notes": "固定源码文本；记录哈希，仅证明这一版本的内容存在。",
    }
    return store.create(
        "source",
        path[:200],
        payload,
        actor,
        blob={
            "name": PurePosixPath(path).name,
            "media_type": "text/plain",
            "sha256": file["version"],
            "content": raw,
        },
    )


def snapshot_file(store, identifier, path):
    source = store.get(identifier)
    if source["kind"] != "source" or source["payload"]["format"] != "zip":
        raise ValueError("请指定源码 ZIP 资料")
    with safe_archive(store.blob(identifier)["content"]) as archive:
        normalized = path.replace("\\", "/")
        if normalized not in archive.namelist():
            raise FileNotFoundError("快照中没有此文件")
        entry = archive.getinfo(normalized)
        if entry.file_size > 2_000_000:
            raise ValueError("文件超过 2 MB，请下载原始快照查看")
        data = archive.read(entry)
        content, _ = decode_source(data)
        return {"path": normalized, "content": content, "sha256": hashlib.sha256(data).hexdigest()}
