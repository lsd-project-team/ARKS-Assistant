"""先在隔离目录检查备份，再允许恢复；禁止直接解压到现有数据目录。"""

import json
import shutil
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core.config import PROJECT_ROOT
from app.infrastructure.storage.manifest import (
    FORMAT_VERSION,
    MAX_ARCHIVE_BYTES,
    MAX_EXPANDED_BYTES,
    database_info,
    file_hash,
)


def safe_member(name: str) -> bool:
    parts = name.split("/")
    if not parts or "\\" in name or ":" in name or "\x00" in name or name.startswith("/"):
        return False
    reserved = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        *(f"COM{index}" for index in range(1, 10)),
        *(f"LPT{index}" for index in range(1, 10)),
    }
    if any(
        not part
        or part in {".", ".."}
        or part.endswith((".", " "))
        or part.split(".")[0].upper() in reserved
        for part in parts
    ):
        return False
    return name in {"app.sqlite3", "checkpoints.sqlite3", "manifest.json"} or (
        len(parts) > 1 and parts[0] in {"memories", "scratch"}
    )


def check_revision(revision):
    if revision is None:
        return
    migration = Config(str(PROJECT_ROOT / "backend/alembic.ini"))
    known = {item.revision for item in ScriptDirectory.from_config(migration).walk_revisions()}
    if revision not in known:
        raise ValueError("备份数据版本不受当前程序支持，请使用兼容版本的程序恢复")


def validate_contents(folder: Path) -> dict:
    if not (folder / "app.sqlite3").is_file():
        raise ValueError("备份缺少业务数据库 app.sqlite3")
    info = database_info(folder / "app.sqlite3", business=True)
    check_revision(info["revision"])
    if (folder / "checkpoints.sqlite3").exists():
        database_info(folder / "checkpoints.sqlite3")
    names = {file.relative_to(folder).as_posix() for file in folder.rglob("*") if file.is_file()}
    manifest_path = folder / "manifest.json"
    manifest = None
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if (
                not isinstance(manifest, dict)
                or type(manifest.get("format_version")) is not int
                or manifest["format_version"] != FORMAT_VERSION
            ):
                raise ValueError("备份格式版本不受支持")
            for field in ("created_at", "workspace_root"):
                if manifest.get(field) is not None and not isinstance(manifest[field], str):
                    raise ValueError("备份清单字段类型不正确")
            entries = manifest["files"]
            if not isinstance(entries, dict) or set(entries) != names - {"manifest.json"}:
                raise ValueError("备份文件清单与实际内容不一致")
            for name, expected in entries.items():
                file = folder / name
                if expected != {"bytes": file.stat().st_size, "sha256": file_hash(file)}:
                    raise ValueError("备份文件哈希校验未通过")
            if (
                manifest["database_revision"] != info["revision"]
                or manifest["counts"] != info["counts"]
            ):
                raise ValueError("备份数据库版本或数量与清单不一致")
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError) as error:
            raise ValueError("备份清单损坏或字段缺失") from error
    return {
        "valid": True,
        "format_version": FORMAT_VERSION if manifest else 0,
        "created_at": manifest.get("created_at") if manifest else None,
        "workspace_root": manifest.get("workspace_root") if manifest else None,
        "database_revision": info["revision"],
        "counts": info["counts"],
        "file_count": len(names),
        "expanded_bytes": sum((folder / name).stat().st_size for name in names),
        "warnings": ([] if manifest else ["旧版备份没有哈希清单，已完成 ZIP 与数据库完整性检查"]),
    }


@contextmanager
def checked_backup(source, *, temporary_parent: Path | None = None):
    if isinstance(source, Path) and source.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("备份 ZIP 超过 512 MiB 上限")
    with tempfile.TemporaryDirectory(dir=temporary_parent) as temporary:
        folder = Path(temporary)
        try:
            with ZipFile(source) as archive:
                members = archive.infolist()
                if (
                    len(members) > 100000
                    or sum(row.file_size for row in members) > MAX_EXPANDED_BYTES
                ):
                    raise ValueError("备份展开内容超过 2 GiB 或文件数量上限")
                seen = set()
                for member in members:
                    # Windows 的 zipfile 会规范化 filename，原始头部名字才能检出反斜杠和空字节。
                    raw_name = member.orig_filename
                    name = raw_name.rstrip("/") if member.is_dir() else raw_name
                    if member.is_dir() and name in {"memories", "scratch"}:
                        continue
                    if not safe_member(name) or stat.S_ISLNK(member.external_attr >> 16):
                        raise ValueError("备份包含非法路径、链接或不允许恢复的文件")
                    if name.casefold() in seen:
                        raise ValueError("备份含重复或大小写冲突的文件路径")
                    seen.add(name.casefold())
                    if member.flag_bits & 1:
                        raise ValueError("不支持加密备份，请先在本机解密")
                    if name == "manifest.json" and member.file_size > 64 * 1024 * 1024:
                        raise ValueError("备份清单超过大小上限")
                    target = (folder / name).resolve()
                    if not target.is_relative_to(folder):
                        raise ValueError("备份路径超出隔离目录")
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with archive.open(member) as incoming, target.open("wb") as outgoing:
                        shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            report = validate_contents(folder)
        except (BadZipFile, OSError, RuntimeError, NotImplementedError) as error:
            raise ValueError("备份无法读取或 ZIP 完整性检查未通过") from error
        yield report, folder


def validate_backup(source) -> dict:
    with checked_backup(source) as (report, _folder):
        return report
