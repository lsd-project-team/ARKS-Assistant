"""文档格式适配入口；不执行附件、宏或项目构建。"""

import hashlib
from pathlib import PurePosixPath

from app.modules.handover.domain.materials import MAX_TEXT, MAX_UPLOAD
from app.modules.source_analysis.workspace import decode_source

from .archive import safe_archive
from .docx import parse_docx
from .pdf import parse_pdf
from .snapshot import parse_snapshot


def parse_document(data, filename):
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
    return {
        "filename": filename,
        "format": extension.lstrip("."),
        "sha256": hashlib.sha256(data).hexdigest(),
        "content": content,
        "parse_status": status,
        "parse_notes": notes,
        "files": files,
    }


def read_snapshot(data, path):
    with safe_archive(data) as archive:
        normalized = path.replace("\\", "/")
        if normalized not in archive.namelist():
            raise FileNotFoundError("快照中没有此文件")
        entry = archive.getinfo(normalized)
        if entry.file_size > 2_000_000:
            raise ValueError("文件超过 2 MB，请下载原始快照查看")
        data = archive.read(entry)
        content, _ = decode_source(data)
        return {"path": normalized, "content": content, "sha256": hashlib.sha256(data).hexdigest()}


class DocumentParser:
    def parse(self, data: bytes, filename: str) -> dict:
        return parse_document(data, filename)

    def snapshot(self, data: bytes, path: str) -> dict:
        return read_snapshot(data, path)
