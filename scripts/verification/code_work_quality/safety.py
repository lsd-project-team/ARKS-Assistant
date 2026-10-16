"""正式目录先拒绝；原件快照和输出摘要不依赖模型的自述。"""

import hashlib
import json
from pathlib import Path

from app.agents.runtime.privacy import redact
from app.core.config import PROJECT_ROOT
from app.modules.code_changes.files import inventory, safe_path, tree_version

INTERNAL = (
    "data",
    "backend",
    "frontend",
    "scripts",
    "docs",
    "skills",
    "resources",
    ".git",
    ".tools",
)


def overlaps(left, right):
    return left.is_relative_to(right) or right.is_relative_to(left)


def checked_path(path, *, source=False):
    resolved = Path(path).resolve()
    blocked = (*INTERNAL, "output") if source else (*INTERNAL, "trunk")
    if any(overlaps(resolved, (PROJECT_ROOT / name).resolve()) for name in blocked):
        raise ValueError("拒绝正式data、应用内部目录及其父目录；原trunk仅可作为只读源码")
    return resolved


def json_hash(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot(root, case):
    versions = inventory(root)
    verify_expected(root, case, versions)
    return versions, tree_version(versions)


def verify_expected(root, case, versions):
    for path, expected in case.expected_sources.items():
        relative = safe_path(root, path).relative_to(root).as_posix()
        if versions.get(relative) != expected:
            raise ValueError(f"场景源码版本不符：{relative}，拒绝请求供应商")


def clean(value, key):
    if isinstance(value, dict):
        return {name: clean(item, key) for name, item in value.items()}
    if isinstance(value, list):
        return [clean(item, key) for item in value]
    if isinstance(value, str):
        text = value.replace(key, "[API_KEY]") if key else value
        return redact(text)
    return value


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
