"""资料接入用例；解析器与仓储由应用入口注入。"""

import hashlib
import re
from pathlib import PurePosixPath

from app.modules.handover.application.ports import MaterialParser, RecordRepository
from app.modules.handover.domain.materials import MAX_TEXT, MAX_UPLOAD, original_media_type


def upload_original(store: RecordRepository, data: bytes, filename: str, actor: str):
    """新上传只保存原始字节，不调用文档解析器或建立正文索引。"""
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError("文件不能为空且不能超过 32 MB")
    filename = PurePosixPath(filename.replace("\\", "/")).name
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename).strip()[:250]
    if filename in {"", ".", ".."}:
        raise ValueError("请提供有效文件名")
    sha256 = hashlib.sha256(data).hexdigest()
    return store.create(
        "source",
        filename[:200],
        {
            "origin": "import",
            "filename": filename,
            "format": PurePosixPath(filename).suffix.lstrip(".").lower(),
            "sha256": sha256,
        },
        actor,
        blob={
            "name": filename,
            "media_type": original_media_type(filename) or "application/octet-stream",
            "sha256": sha256,
            "content": data,
        },
    )


def original_file(store: RecordRepository, identifier: str):
    try:
        return store.blob(identifier)
    except FileNotFoundError:
        row = store.get(identifier)
        payload = row["payload"]
        content = payload.get("content", "")
        if row["kind"] != "source" or not content:
            raise FileNotFoundError("原始附件不存在") from None
        # 纯文本资料可按已保存正文下载，不解析新文件或改写原文。
        filename = re.sub(r'[\\/:*?"<>|\r\n]', "_", row["title"]) + ".txt"
        return {"content": content.encode("utf-8"), "name": filename, "media_type": "text/plain"}


def import_source(store: RecordRepository, data, filename, metadata, actor, parser: MaterialParser):
    parsed = parser.parse(data, filename)
    payload = {**metadata, "origin": "import", **parsed}
    return store.create(
        "source",
        parsed["filename"][:200],
        payload,
        actor,
        blob={
            "name": parsed["filename"],
            "media_type": "application/octet-stream",
            "sha256": parsed["sha256"],
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


def snapshot_file(store: RecordRepository, identifier, path, parser: MaterialParser):
    source = store.get(identifier)
    if source["kind"] != "source" or source["payload"]["format"] != "zip":
        raise ValueError("请指定源码 ZIP 资料")
    return parser.snapshot(store.blob(identifier)["content"], path)
