"""临时文件的路径边界和完整性检查，供聊天归档使用。"""

import hashlib
import os
import stat
from pathlib import Path, PurePosixPath

from app.modules.source_analysis.workspace import IGNORED

MAX_DIRECTORY_FILES = 30000
MAX_DIRECTORY_BYTES = 1_000_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def is_link(path):
    info = path.lstat()
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def safe_path(root, relative="", *, allow_root=False):
    value = str(relative).replace("\\", "/")
    parts = PurePosixPath(value).parts
    if (
        ":" in value
        or "\x00" in value
        or value.startswith("/")
        or ".." in parts
        or (not parts and not allow_root)
        or any(part in IGNORED for part in parts)
        or any(ord(char) < 32 or char in '<>"|?*' for char in value)
    ):
        raise ValueError("只能访问临时目录内未排除的相对路径")
    # Windows 尾随点/空格、设备名会改变 Win32 的实际路径含义。
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10))}
    reserved.update(f"LPT{i}" for i in range(1, 10))
    if any(part.endswith((".", " ")) or part.split(".")[0].upper() in reserved for part in parts):
        raise ValueError("路径包含系统保留名称")
    root = Path(root)
    if is_link(root):
        raise ValueError("临时目录根目录不能是链接或目录联接")
    resolved_root = root.resolve()
    cursor = root
    for part in parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if is_link(cursor):
                raise ValueError("临时目录中不允许符号链接或目录联接")
            if cursor.is_file() and cursor.stat().st_nlink > 1:
                raise ValueError("临时目录中不允许硬链接")
    target = (root / value).resolve()
    if not target.is_relative_to(resolved_root) or (target == resolved_root and not allow_root):
        raise ValueError("路径超出临时目录边界")
    return target


def inventory(root, *, bounded=True):
    root = Path(root)
    if not root.is_dir() or is_link(root):
        raise ValueError("源码或临时目录目录不存在，或根目录是链接")
    manifest, total = {}, 0
    for folder, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORED)
        names = [name for name in names if name not in IGNORED]
        for name in [*directories, *names]:
            target = Path(folder) / name
            if is_link(target):
                raise ValueError(f"临时目录含链接：{target.relative_to(root)}")
        for name in sorted(names):
            target = safe_path(root, (Path(folder) / name).relative_to(root).as_posix())
            if not target.is_file():
                raise ValueError("临时目录只允许普通文件")
            total += target.stat().st_size
            if bounded and (total > MAX_DIRECTORY_BYTES or len(manifest) >= MAX_DIRECTORY_FILES):
                raise ValueError(
                    f"临时目录超过 {MAX_DIRECTORY_BYTES:,} 字节或 "
                    f"{MAX_DIRECTORY_FILES} 个文件的限制"
                )
            manifest[target.relative_to(root).as_posix()] = digest(target.read_bytes())
    return manifest
