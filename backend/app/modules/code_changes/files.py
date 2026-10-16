"""副本只复制普通文件，所有读写与清理都重新检查解析后的边界。"""

import base64
import difflib
import hashlib
import json
import os
import shutil
import stat
import zlib
from pathlib import Path, PurePosixPath

from app.modules.source_analysis.workspace import IGNORED, MAX_FILE_BYTES, decode_source

MAX_COPY_FILES = 30000
MAX_COPY_BYTES = 1_000_000_000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def tree_version(manifest):
    return digest(json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode())


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
        raise ValueError("只能访问副本内未排除的相对路径")
    # Windows 尾随点/空格、设备名会改变 Win32 的实际路径含义。
    reserved = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10))}
    reserved.update(f"LPT{i}" for i in range(1, 10))
    if any(part.endswith((".", " ")) or part.split(".")[0].upper() in reserved for part in parts):
        raise ValueError("路径包含系统保留名称")
    root = Path(root)
    if is_link(root):
        raise ValueError("副本根目录不能是链接或目录联接")
    resolved_root = root.resolve()
    cursor = root
    for part in parts:
        cursor = cursor / part
        if cursor.exists() or cursor.is_symlink():
            if is_link(cursor):
                raise ValueError("副本中不允许符号链接或目录联接")
            if cursor.is_file() and cursor.stat().st_nlink > 1:
                raise ValueError("副本中不允许硬链接")
    target = (root / value).resolve()
    if not target.is_relative_to(resolved_root) or (target == resolved_root and not allow_root):
        raise ValueError("路径超出副本边界")
    return target


def inventory(root, *, bounded=True):
    root = Path(root)
    if not root.is_dir() or is_link(root):
        raise ValueError("源码或副本目录不存在，或根目录是链接")
    manifest, total = {}, 0
    for folder, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORED)
        names = [name for name in names if name not in IGNORED]
        for name in [*directories, *names]:
            target = Path(folder) / name
            if is_link(target):
                raise ValueError(f"目录含链接，不能建立或验证副本：{target.relative_to(root)}")
        for name in sorted(names):
            target = safe_path(root, (Path(folder) / name).relative_to(root).as_posix())
            if not target.is_file():
                raise ValueError("副本只允许普通文件")
            total += target.stat().st_size
            if bounded and (total > MAX_COPY_BYTES or len(manifest) >= MAX_COPY_FILES):
                raise ValueError(
                    f"源码副本超过 {MAX_COPY_BYTES:,} 字节或 {MAX_COPY_FILES} 个文件的限制"
                )
            manifest[target.relative_to(root).as_posix()] = digest(target.read_bytes())
    return manifest


def copy_snapshot(source, base, work):
    manifest = inventory(source)
    base.mkdir(parents=True)
    work.mkdir()
    for relative, version in manifest.items():
        original = safe_path(source, relative)
        data = original.read_bytes()
        if digest(data) != version:
            raise ValueError(f"建立副本时源码已改变：{relative}")
        for root in (base, work):
            target = safe_path(root, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    if inventory(source) != manifest:
        raise ValueError("建立副本时源码目录已改变，请重试")
    return manifest


def read_text(root, relative):
    target = safe_path(root, relative)
    if not target.exists():
        return {
            "path": relative,
            "content": "",
            "version": "",
            "exists": False,
            "encoding": "UTF-8",
        }
    if not target.is_file() or target.stat().st_size > MAX_FILE_BYTES:
        raise ValueError("只能编辑不超过 2 MB 的文本文件")
    data = target.read_bytes()
    content, encoding = decode_source(data)
    if encoding == "UTF-8-SIG" and not data.startswith(b"\xef\xbb\xbf"):
        encoding = "UTF-8"
    elif encoding == "UTF-16":
        encoding = "UTF-16-LE" if data.startswith(b"\xff\xfe") else "UTF-16-BE"
    return {
        "path": relative,
        "content": content,
        "version": digest(data),
        "exists": True,
        "encoding": encoding,
    }


def edit_text(root, relative, before, after, version):
    previous = read_text(root, relative)
    if version != previous["version"]:
        raise ValueError("副本文件版本已改变，请重新读取后合并修改")
    content = previous["content"]
    if (not before and content) or (before and content.count(before) != 1):
        raise ValueError("修改上下文不存在或不唯一，请重新读取文件")
    updated = content.replace(before, after, 1) if before else after
    if "\x00" in updated:
        raise ValueError("不允许写入二进制内容")
    # 文本框通常归一化为 LF；保留原件的单一 CRLF 换行和 BOM/字节序。
    if "\r\n" in content and "\n" not in content.replace("\r\n", ""):
        updated = updated.replace("\r\n", "\n").replace("\n", "\r\n")
    encoding = previous["encoding"].lower()
    data = updated.encode(encoding)
    if encoding in {"utf-16-le", "utf-16-be"}:
        data = (b"\xff\xfe" if encoding.endswith("le") else b"\xfe\xff") + data
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("修改后的文件超过 2 MB")
    target = safe_path(root, relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    safe_path(root, relative).write_bytes(data)


def changes_diff(base, work, baseline):
    if inventory(base) != baseline:
        raise ValueError("副本基线内容已改变，请丢弃后重新建立副本")
    current = inventory(work)
    files, chunks = [], []
    for relative in sorted(set(baseline) | set(current)):
        old, new = baseline.get(relative), current.get(relative)
        if old == new:
            continue
        files.append(
            {
                "path": relative,
                "status": "added" if old is None else "deleted" if new is None else "modified",
                "base_version": old,
                "current_version": new,
            }
        )
        try:
            before = read_text(base, relative)["content"] if old else ""
            after = read_text(work, relative)["content"] if new else ""
            chunks.append(text_patch(relative, before, after, old is not None, new is not None))
        except ValueError:
            chunks.append(f"Binary files a/{relative} and b/{relative} differ\n")
    return current, files, "".join(chunks)


def patch_header(relative, old_exists, new_exists):
    old_path = json.dumps(f"a/{relative}", ensure_ascii=False)
    new_path = json.dumps(f"b/{relative}", ensure_ascii=False)
    header = f"diff --git {old_path} {new_path}\n"
    if not old_exists:
        header += "new file mode 100644\n"
    elif not new_exists:
        header += "deleted file mode 100644\n"
    return header, old_path, new_path


def text_patch(relative, before, after, old_exists, new_exists):
    header, old_path, new_path = patch_header(relative, old_exists, new_exists)
    chunks = [header]
    for line in difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=old_path if old_exists else "/dev/null",
        tofile=new_path if new_exists else "/dev/null",
    ):
        chunks.append(line if line.endswith("\n") else line + "\n\\ No newline at end of file\n")
    return "".join(chunks)


def binary_literal(data):
    compressed = zlib.compress(data)
    lines = [f"literal {len(data)}\n"]
    for start in range(0, len(compressed), 52):
        chunk = compressed[start : start + 52]
        length = len(chunk)
        marker = chr(ord("A") + length - 1) if length <= 26 else chr(ord("a") + length - 27)
        lines.append(marker + base64.b85encode(chunk, pad=True).decode("ascii") + "\n")
    return "".join(lines) + "\n"


def export_patch(base, work, baseline):
    _, files, _ = changes_diff(base, work, baseline)
    chunks = []
    for item in files:
        relative = item["path"]
        old_exists, new_exists = (
            item["base_version"] is not None,
            item["current_version"] is not None,
        )
        before = safe_path(base, relative).read_bytes() if old_exists else b""
        after = safe_path(work, relative).read_bytes() if new_exists else b""
        try:
            old_text, new_text = before.decode("utf-8"), after.decode("utf-8")
            if b"\x00" in before + after:
                raise ValueError("二进制文件使用 Git binary patch")
            chunks.append(text_patch(relative, old_text, new_text, old_exists, new_exists))
        except (UnicodeDecodeError, ValueError):
            # 非 UTF-8 源码使用可直接应用的二进制补丁，避免下载时转码损坏 GB/UTF-16。
            header, _, _ = patch_header(relative, old_exists, new_exists)
            old_hash = git_blob(before) if old_exists else "0" * 40
            new_hash = git_blob(after) if new_exists else "0" * 40
            mode = " 100644" if old_exists and new_exists else ""
            chunks.append(header + f"index {old_hash}..{new_hash}{mode}\nGIT binary patch\n")
            chunks.extend([binary_literal(after), binary_literal(before)])
    return "".join(chunks)


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def remove_copy(root, target):
    expected = safe_path(root, target.name)
    if expected != target.resolve() or expected.parent != root.resolve():
        raise ValueError("拒绝清理不属于隔离目录的路径")
    # 不跟随任何副本中后添的目录联接；清理前要求整棵树仍满足边界。
    inventory(expected, bounded=False)
    shutil.rmtree(expected)
