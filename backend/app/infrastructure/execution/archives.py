"""副本传输仅处理普通文件，不执行解压器提供的路径或链接语义。"""

import os
import shutil
import stat
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

from .cli import ExecutionError

MAX_FILES = 30000
RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def safe_relative(name):
    if (
        not isinstance(name, str)
        or len(name) > 4096
        or "\\" in name
        or ":" in name
        or "\x00" in name
        or any(ord(character) < 32 or character in '<>"|?*' for character in name)
    ):
        raise ExecutionError("传输包含非法文件名")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts:
        raise ExecutionError("传输包含越界路径")
    for part in path.parts:
        if part == ".arks-execution-result":
            raise ExecutionError("传输使用了执行器保留路径")
        if part.endswith((".", " ")) or part.split(".", 1)[0].casefold() in RESERVED:
            raise ExecutionError("传输包含不兼容的文件名")
    return path


def reject_link(path):
    if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
        raise ExecutionError("沙箱传输不接受符号链接或目录联接")


def check_root(root):
    root = Path(root).absolute()
    for path in [root, *root.parents]:
        reject_link(path)
    if not root.is_dir():
        raise ExecutionError("隔离副本目录不存在")
    return root


def write_source(root, destination, maximum):
    root = check_root(root)
    total = 0
    count = 0
    with tarfile.open(destination, "w") as archive:
        for folder, directories, filenames in os.walk(root, followlinks=False):
            for name in sorted([*directories, *filenames]):
                path = Path(folder) / name
                reject_link(path)
                relative = path.relative_to(root).as_posix()
                safe_relative(relative)
                count += 1
                if count > MAX_FILES:
                    raise ExecutionError("传输文件数量超过限制")
                info = path.stat()
                if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
                    raise ExecutionError("沙箱只接受普通文件和目录")
                if stat.S_ISREG(info.st_mode) and info.st_nlink > 1:
                    raise ExecutionError("沙箱传入不接受硬链接")
                total += info.st_size if path.is_file() else 0
                if total > maximum:
                    raise ExecutionError("源码副本超过沙箱空间限制")
                member = tarfile.TarInfo(relative)
                member.uid = member.gid = 0
                member.mode = 0o755 if path.is_dir() else 0o644 | (info.st_mode & 0o111)
                member.mtime = info.st_mtime
                if path.is_dir():
                    member.type = tarfile.DIRTYPE
                    archive.addfile(member)
                else:
                    member.size = info.st_size
                    with path.open("rb") as source:
                        archive.addfile(member, source)
    return total


class BoundedArchive:
    def __init__(self, stream):
        self.stream = stream

    def read(self, size=-1):
        # 普通文件按块读取；拒绝 tar 扩展头诱导的大块内存分配。
        if size < 0 or size > 1024 * 1024:
            raise ExecutionError("归档元数据超过限制")
        return self.stream.read(size)


def unpack_result(source, destination, maximum):
    """先在空 staging 校验全部成员，失败时不会触碰当前工作副本。"""
    seen = set()
    total = 0
    with tarfile.open(fileobj=BoundedArchive(source), mode="r|") as archive:
        for member in archive:
            relative = safe_relative(member.name)
            if not relative.parts:
                if member.isdir():
                    continue
                raise ExecutionError("传输包含无效根文件")
            key = relative.as_posix().casefold()
            if key in seen:
                raise ExecutionError("传输包含重复或大小写冲突路径")
            seen.add(key)
            if len(seen) > MAX_FILES:
                raise ExecutionError("传输文件数量超过限制")
            if not (member.isfile() or member.isdir()) or member.sparse:
                raise ExecutionError("结果包含链接、稀疏文件或特殊设备")
            total += member.size
            if member.size < 0 or total > maximum:
                raise ExecutionError("沙箱回传结果超过空间限制")
            target = destination.joinpath(*relative.parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.extractfile(member) as stream, target.open("xb") as output:
                shutil.copyfileobj(stream, output, length=65536)
            target.chmod((member.mode & 0o777) | 0o600)


def replace_worktree(source, root, maximum):
    root = check_root(root)
    with tempfile.TemporaryDirectory(prefix="arks-return-", dir=root.parent) as temporary:
        staging = Path(temporary) / "work"
        staging.mkdir()
        unpack_result(source, staging, maximum)
        reject_link(root)
        backup = Path(temporary) / "previous"
        # 同一父目录交换，异常时回滚；不会跟随副本内的输出链接。
        root.rename(backup)
        try:
            staging.rename(root)
        except BaseException:
            backup.rename(root)
            raise
