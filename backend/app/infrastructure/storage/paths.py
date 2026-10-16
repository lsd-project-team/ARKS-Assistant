"""内部暂存使用 Windows 长路径；本地盘身份和普通展示路径保持可区分。"""

import os
import re
from pathlib import Path


def ordinary_path(path: Path) -> Path:
    value = str(path)
    if os.name == "nt" and value.startswith("\\\\?\\"):
        if not re.match(r"^\\\\\?\\[A-Za-z]:\\", value):
            raise ValueError("备份暂存目录必须使用本地绝对路径，不支持UNC或设备路径")
        value = value[4:]
    return Path(value)


def staging_parent(path: Path) -> Path:
    parent = ordinary_path(path).absolute()
    if os.name != "nt":
        return parent.resolve()
    # UNC/设备身份在任何 resolve 或目录访问前拒绝；解析后再次检查重解析目标。
    if not re.fullmatch(r"[A-Za-z]:", parent.drive) or parent.root != "\\":
        raise ValueError("备份暂存目录必须使用本地绝对路径，不支持UNC或设备路径")
    resolved = ordinary_path(parent.resolve())
    if not re.fullmatch(r"[A-Za-z]:", resolved.drive) or resolved.root != "\\":
        raise ValueError("备份暂存目录解析后必须仍为本地绝对路径")
    return Path("\\\\?\\" + str(resolved))
