"""项目目录内的通用文件读写；路径限制在项目根，保留原编码与换行。"""

import codecs
import json
import os
import re
import tempfile
from pathlib import Path

from app.infrastructure.storage.files import digest, is_link, safe_path

MAX_FILE_BYTES = 2_000_000
MAX_LIST_ENTRIES = 2_000
MAX_SEARCH_RESULTS = 200
EXCLUDED = {
    ".git",
    ".vs",
    ".svn",
    "bin",
    "obj",
    "packages",
    "node_modules",
    "dist",
    "publish",
}
BINARY_SUFFIXES = {
    ".dll",
    ".exe",
    ".pdb",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".zip",
    ".7z",
    ".rar",
    ".pdf",
    ".sqlite3",
    ".db",
    ".nupkg",
}


def project_root(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("项目目录不存在，请先创建或选择目录")
    return root


def resolve(root, relative=""):
    """把项目内相对路径解析为绝对路径；拒绝绝对路径和 .. 逃逸。"""
    relative = (relative or "").replace("\\", "/").strip()
    if Path(relative).is_absolute():
        raise ValueError("请使用项目内的相对路径")
    return safe_path(project_root(root), relative or ".", allow_root=True)


def relative(root, path):
    return Path(path).resolve().relative_to(project_root(root)).as_posix()


def _decode(data):
    for bom, encoding in (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if data.startswith(bom):
            return data.decode(encoding), encoding
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("文件不是可识别的文本编码（支持 UTF-8 / UTF-16 / GB18030）")


def _looks_binary(path, data):
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    sample = data[:8000]
    return b"\x00" in sample


def read_text(root, path, start_line=1, end_line=400):
    target = resolve(root, path)
    if not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    data = target.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"文件超过 {MAX_FILE_BYTES // 1_000_000} MB，请改用命令读取")
    if _looks_binary(target, data):
        raise ValueError("这是二进制文件，不能按文本读取")
    text, encoding = _decode(data)
    lines = text.replace("\r\n", "\n").split("\n")
    start = max(1, int(start_line))
    end = min(len(lines), max(start, int(end_line)))
    numbered = "\n".join(f"{index:>5} {lines[index - 1]}" for index in range(start, end + 1))
    return {
        "path": relative(root, target),
        "start_line": start,
        "end_line": end,
        "total_lines": len(lines),
        "encoding": encoding,
        "version": digest(data),
        "content": numbered,
    }


def write_text(root, path, content, expected_hash=""):
    target = resolve(root, path)
    if target.is_dir():
        raise ValueError("目标是目录，不能写入")
    exists = target.is_file()
    if exists and not expected_hash:
        raise ValueError("覆盖已有文件必须带上一次读取的 version，避免覆盖他人修改")
    if exists:
        current = digest(target.read_bytes())
        if current != expected_hash:
            raise ValueError("文件已被修改，请重新读取后再写")
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("写入内容超过 2 MB 限制")
    encoding, bom, newline = "utf-8", b"", "\n"
    if exists:
        original = target.read_bytes()
        text, detected = _decode(original)
        encoding = "utf-16" if detected.startswith("utf-16") else detected
        bom = original[: len(codecs.BOM_UTF8)] if original.startswith(codecs.BOM_UTF8) else b""
        if detected.startswith("utf-16"):
            bom = original[:2]
        newline = "\r\n" if "\r\n" in text else "\n"
    body = content.replace("\r\n", "\n")
    if newline == "\r\n":
        body = body.replace("\n", "\r\n")
    if encoding == "utf-8":
        data = bom + body.encode("utf-8")
    elif encoding == "gb18030":
        data = body.encode("gb18030")
    else:
        data = bom + body.encode("utf-16-le" if bom == codecs.BOM_UTF16_LE else "utf-16-be")
    atomic_bytes(target, data)
    return {
        "path": relative(root, target),
        "version": digest(data),
        "bytes": len(data),
        "created": not exists,
    }


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".coding-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_directory(root, path):
    target = resolve(root, path)
    if target.exists():
        raise ValueError("目录或文件已存在")
    target.mkdir(parents=True)
    return {"path": relative(root, target)}


def move(root, path, destination):
    source = resolve(root, path)
    target = resolve(root, destination)
    if not source.exists():
        raise FileNotFoundError(f"路径不存在：{path}")
    if target.exists():
        raise ValueError("目标已存在，不能覆盖")
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    return {"from": relative(root, source), "to": relative(root, target)}


def delete(root, path, recursive=False):
    target = resolve(root, path)
    if not target.exists():
        raise FileNotFoundError(f"路径不存在：{path}")
    if target == project_root(root):
        raise ValueError("不能删除项目根目录")
    if target.is_dir():
        if not recursive:
            raise ValueError("删除目录需要显式 recursive=true")
        import shutil

        shutil.rmtree(target)
    else:
        target.unlink()
    return {"path": relative(root, target) if target.exists() else path}


def list_tree(root, path=".", depth=2):
    base = resolve(root, path)
    if not base.is_dir():
        raise ValueError("不是目录")
    rows = []
    base_depth = len(base.relative_to(project_root(root)).parts)

    def walk(directory):
        nonlocal rows
        for entry in sorted(
            directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower())
        ):
            if entry.name in EXCLUDED or is_link(entry):
                continue
            current = len(entry.relative_to(project_root(root)).parts)
            if current - base_depth > depth:
                continue
            if entry.is_dir():
                rows.append(f"{entry.relative_to(project_root(root)).as_posix()}/")
                if len(rows) < MAX_LIST_ENTRIES:
                    walk(entry)
            else:
                rows.append(entry.relative_to(project_root(root)).as_posix())
            if len(rows) >= MAX_LIST_ENTRIES:
                return

    walk(base)
    return {
        "path": relative(root, base) if base != project_root(root) else ".",
        "entries": rows[:MAX_LIST_ENTRIES],
    }


def search_text(root, query, path=".", glob="", limit=100):
    query = query.strip()
    if not query:
        raise ValueError("搜索内容不能为空")
    base = resolve(root, path)
    pattern = re.compile(
        rf"^{re.escape(glob).replace(r'\*', '.*').replace(r'\?', '.')}$", re.IGNORECASE
    )
    rows, scanned = [], 0
    for file in sorted(base.rglob("*")):
        if len(rows) >= min(limit, MAX_SEARCH_RESULTS):
            break
        if not file.is_file() or any(part in EXCLUDED for part in file.parts):
            continue
        if glob and not pattern.match(file.name):
            continue
        scanned += 1
        if scanned > 5000 or file.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            data = file.read_bytes()
            if _looks_binary(file, data):
                continue
            text, _ = _decode(data)
        except (ValueError, OSError):
            continue
        for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
            if query.lower() in line.lower():
                rows.append(
                    {
                        "path": file.relative_to(project_root(root)).as_posix(),
                        "line": number,
                        "text": line.strip()[:300],
                    }
                )
                break
    return {"query": query, "results": rows[:MAX_SEARCH_RESULTS]}


def tree_snapshot(root, depth=2):
    return json.dumps(list_tree(root, ".", depth), ensure_ascii=False)
