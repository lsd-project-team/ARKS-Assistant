"""工作区内的安全路径、文本编码与原子写入；不改动工作区以外的文件。"""

import codecs
import os
import tempfile
from pathlib import Path

from app.infrastructure.storage.files import digest, is_link
from app.modules.source_analysis.workspace import decode_source

IGNORED = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vs",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "bin",
    "obj",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "packages",
    "target",
}
MAX_FILE_BYTES = 2_000_000
MAX_LIST_ENTRIES = 5_000
MAX_SEARCH_FILES = 5_000


def workspace_root(value) -> Path:
    if not value:
        raise ValueError("尚未配置工作目录")
    root = Path(value).expanduser()
    if not root.is_absolute() or not root.is_dir():
        raise ValueError("工作目录必须是本机已存在的绝对路径")
    if is_link(root):
        raise ValueError("工作目录不能是链接")
    return root.resolve()


def resolve(root, value) -> tuple[Path, str]:
    """返回工作区内文件与相对路径；拒绝越界、链接和忽略目录。"""
    if value is None:
        value = ""
    if not isinstance(value, str):
        raise ValueError("路径必须是字符串")
    if value.startswith(("/", "\\")) or (len(value) > 1 and value[1] == ":"):
        raise ValueError("请使用工作区内的相对路径")
    normalized = value.replace("\\", "/").strip("/")
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    base = Path(root).resolve()
    if not parts:
        return base, ""
    if any(part == ".." for part in parts):
        raise ValueError("路径必须位于工作区内")
    if any(part in IGNORED for part in parts):
        raise ValueError("该目录不作为代码工作区内容")
    candidate = base.joinpath(*parts)
    cursor = base
    for part in parts:
        cursor = cursor / part
        if cursor.exists() and is_link(cursor):
            raise ValueError("路径包含链接，已拒绝")
    resolved = candidate.resolve()
    if resolved != base and not resolved.is_relative_to(base):
        raise ValueError("路径超出工作区")
    return resolved, "/".join(parts)


def read_bytes(path: Path) -> bytes:
    if not path.is_file():
        raise FileNotFoundError("工作区文件不存在")
    if is_link(path):
        raise ValueError("路径包含链接，已拒绝")
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise ValueError("单个文件不能超过 2 MB")
    return path.read_bytes()


def text_of(data: bytes) -> str:
    return decode_source(data)[0]


def encode(text: str, original: bytes = b"") -> bytes:
    """统一换行匹配，落盘保留原 BOM、中文编码与换行。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    previous, encoding = decode_source(original) if original else ("", "UTF-8")
    if "\r\n" in previous:
        text = text.replace("\n", "\r\n")
    if original.startswith(codecs.BOM_UTF16_BE):
        data = codecs.BOM_UTF16_BE + text.encode("utf-16-be")
    elif original.startswith(codecs.BOM_UTF16_LE):
        data = codecs.BOM_UTF16_LE + text.encode("utf-16-le")
    elif encoding == "GB18030":
        data = text.encode("gb18030")
    else:
        data = (codecs.BOM_UTF8 if original.startswith(codecs.BOM_UTF8) else b"") + text.encode(
            "utf-8"
        )
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("单个文件不能超过 2 MB")
    return data


def atomic_bytes(path: Path, data: bytes):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".ww-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def version_of(path: Path) -> str:
    return digest(path.read_bytes()) if path.is_file() else ""


def walk(root: Path, limit=MAX_LIST_ENTRIES):
    """按稳定顺序遍历工作区文件，跳过忽略目录和链接。"""
    count = 0
    for folder, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(
            name
            for name in directories
            if name not in IGNORED and not (Path(folder) / name).is_symlink()
        )
        for name in sorted(names):
            path = Path(folder) / name
            if path.is_symlink() or not path.is_file():
                continue
            count += 1
            if count > limit:
                raise ValueError("工作区文件过多，请缩小范围")
            yield path
