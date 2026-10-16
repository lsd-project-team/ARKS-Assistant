"""只在源码根内检查文件存在性；Windows 路径在 Linux 上也不能误当相对路径。"""

import os
import re
import stat
from pathlib import Path, PureWindowsPath

from app.modules.source_analysis.workspace import IGNORED

MAX_FILE_BYTES = 2_000_000
MAX_SCAN_FILES = 100_000
MAX_BUILD_FILES = 2_000
PROJECT_SUFFIXES = {".csproj", ".vbproj", ".fsproj"}


def display(value, maximum=240):
    return re.sub(r"[\x00-\x1f\x7f]", "", str(value))[:maximum]


def is_link(path):
    info = path.lstat()
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0)
        & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def local_file(root, path):
    """不跟随链接，也不探查根外的文件是否存在。"""
    lexical = Path(os.path.abspath(path))
    if not lexical.is_relative_to(root):
        return "external"
    current = root
    for part in lexical.relative_to(root).parts:
        current /= part
        try:
            if is_link(current):
                return "linked"
        except FileNotFoundError:
            return "missing"
        except OSError:
            return "unreadable"
    try:
        return "exists" if lexical.is_file() else "missing"
    except OSError:
        return "unreadable"


def reference(root, directory, value):
    value = str(value or "").strip()
    windows = PureWindowsPath(value)
    absolute = bool(windows.drive or windows.root or value.startswith("/"))
    if not value:
        return {"path": "", "status": "environment", "absolute": False}
    if re.search(r"\$\(|@\(|%\(|[?*]", value):
        # 属性、条件和通配符由 MSBuild 决定；静态扫描不能伪装成已求值。
        return {"path": "<requires-msbuild-evaluation>", "status": "dynamic", "absolute": absolute}
    if "\x00" in value:
        return {"path": "<invalid-path>", "status": "invalid", "absolute": absolute}
    if absolute:
        if os.name != "nt" and (windows.drive or value.startswith("\\")):
            return {
                "path": "<outside-source-root>/" + display(windows.name),
                "status": "external",
                "absolute": True,
            }
        target = Path(value.replace("\\", "/"))
        # C:foo 是依赖当前盘符工作目录的路径，绝不能据宿主当前目录猜测。
        if windows.drive and not windows.root:
            target = root.parent / "<drive-relative>"
    else:
        target = directory / value.replace("\\", "/")
    status = local_file(root, target)
    if status == "external":
        label = "<outside-source-root>/" + display(windows.name)
    else:
        label = display(Path(os.path.abspath(target)).relative_to(root).as_posix())
    return {"path": label, "status": status, "absolute": absolute}


def discover(root):
    paths, issues, scanned = [], [], 0
    if not root.is_dir() or is_link(root):
        return [], [
            {
                "code": "invalid_source_root",
                "severity": "error",
                "path": "",
                "message": "主源码根不存在或是链接；未扫描。",
            }
        ]
    for folder, directories, names in os.walk(root, followlinks=False):
        retained = []
        for name in sorted(directories):
            path = Path(folder) / name
            if name in IGNORED:
                continue
            try:
                if is_link(path):
                    issues.append(
                        {
                            "code": "linked_path_skipped",
                            "severity": "warning",
                            "path": display(path.relative_to(root).as_posix()),
                            "message": "跳过链接或目录联接；不能据此确认依赖齐全。",
                        }
                    )
                else:
                    retained.append(name)
            except OSError:
                issues.append(
                    {
                        "code": "unreadable_directory",
                        "severity": "error",
                        "path": display(path.relative_to(root).as_posix()),
                        "message": "无法检查目录；扫描不完整。",
                    }
                )
        directories[:] = retained
        for name in sorted(names):
            scanned += 1
            if scanned > MAX_SCAN_FILES or len(paths) >= MAX_BUILD_FILES:
                issues.append(
                    {
                        "code": "scan_limit",
                        "severity": "error",
                        "path": "",
                        "message": "达到扫描文件数量上限；结果不完整。",
                    }
                )
                return paths, issues
            path = Path(folder) / name
            if path.suffix.lower() not in PROJECT_SUFFIXES | {".sln"}:
                continue
            paths.append(path)
    return paths, issues
