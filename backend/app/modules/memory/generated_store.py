"""后台记忆的原子发布和本地可读文件；所有读取都按账号及项目约束。"""

import json
import time
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from app.core.config import dump_json
from app.core.identifiers import now_iso
from app.modules.memory.conflicts import RELATION_LABELS, annotate_groups
from app.modules.memory.models import MemoryBundle, MemoryExtraction


def collection_id(owner, workspace):
    return sha256(dump_json([owner, workspace]).encode()).hexdigest()


def markdown(document, *, evidence_ids=False):
    sections = []
    groups = document["groups"]
    if "relations" in document:
        groups = annotate_groups(groups, document["relations"])
    titles = {fact["id"]: fact["title"] for group in groups for fact in group["memories"]}
    for group in groups:
        rows = ["## " + group["title"]]
        for fact in group["memories"]:
            state = fact.get("state", "valid")
            label = "【" + RELATION_LABELS[state] + "】" if state in RELATION_LABELS else ""
            rows.append("- " + label + fact["content"])
            if state == "conflicted":
                rows.append(
                    "  此处存在未决矛盾，不能任选一方作为确定事实；需核查原始依据或确认适用条件。"
                )
            if state == "superseded":
                rows.append("  仅保留历史依据，不作为当前事实带入回答。")
            related = [titles[key] for key in fact.get("related_ids", []) if key in titles]
            if related:
                rows.append("  关联记录：" + "；".join(related))
            rows.append(
                "  依据："
                + "；".join(
                    (item["message_id"] if evidence_ids else "") + "「" + item["quote"] + "」"
                    for item in fact["evidence"]
                )
            )
        sections.append("\n".join(rows))
    return "\n\n".join(sections)


class GeneratedMemoryStore:
    def __init__(self, paths, database):
        self.root = paths.memories / "automatic"
        self.database = database

    def bundle(self, owner, workspace):
        with self.database.session() as session:
            row = session.get(MemoryBundle, collection_id(owner, workspace))
            if not row:
                return None
            return {
                "document": json.loads(row.document_json),
                "revision": row.revision,
                "updated_at": row.updated_at,
            }

    def inputs(self, owner, workspace):
        with self.database.session() as session:
            return [
                {
                    "thread_id": row.thread_id,
                    "fingerprint": row.fingerprint,
                    "facts": json.loads(row.raw_json),
                }
                for row in session.scalars(
                    select(MemoryExtraction)
                    .where(
                        MemoryExtraction.owner_id == owner,
                        MemoryExtraction.workspace_id == workspace,
                        MemoryExtraction.raw_json != "",
                    )
                    .order_by(MemoryExtraction.updated_at.desc())
                    .limit(256)
                )
            ]

    def unreconciled_threads(self):
        with self.database.session() as session:
            threads = []
            for row in session.scalars(select(MemoryBundle)):
                document = json.loads(row.document_json)
                if document.get("relation_version") == 1:
                    continue
                threads.extend(
                    fact["thread_id"] for group in document["groups"] for fact in group["memories"]
                )
            return list(dict.fromkeys(threads))

    def publish(self, snapshot, document, *, lease_token=None, expected_revision=None):
        owner, workspace = snapshot["owner_id"], snapshot["workspace_id"]
        identifier = collection_id(owner, workspace)
        encoded = dump_json(document)
        digest = sha256(encoded.encode()).hexdigest()
        folder = self.root / identifier / digest
        folder.mkdir(parents=True, exist_ok=True)
        files = {
            "MEMORY.md": markdown(document, evidence_ids=True),
            "memory_summary.md": "\n".join("- " + group["title"] for group in document["groups"]),
            "raw_memories.json": encoded,
        }
        for name, content in files.items():
            target = folder / name
            temporary = target.with_suffix(".tmp")
            temporary.write_bytes(content.encode("utf-8"))
            temporary.replace(target)
        # 完整文件写入后才发布数据库指针；中断不会让回答读到半份新成果。
        with self.database.session.begin() as session:
            row = session.get(MemoryBundle, identifier)
            if expected_revision is not None and (row.revision if row else 0) != expected_revision:
                raise ValueError("memory_bundle_changed")
            if lease_token is not None:
                job = session.get(MemoryExtraction, snapshot["thread_id"])
                if (
                    not job
                    or job.lease_token != lease_token
                    or job.fingerprint != snapshot["fingerprint"]
                    or job.lease_until <= time.time()
                ):
                    raise ValueError("memory_lease_lost")
                job.state, job.lease_until, job.retry_after = "completed", 0, 0
                job.updated_at = now_iso()
            if row is None:
                session.add(
                    MemoryBundle(
                        id=identifier, owner_id=owner, workspace_id=workspace, document_json=encoded
                    )
                )
            elif row.document_json != encoded:
                row.document_json, row.revision, row.updated_at = (
                    encoded,
                    row.revision + 1,
                    now_iso(),
                )
        return self.bundle(owner, workspace)


def archive_legacy_memories(paths):
    """旧文件移入备份范围内的归档，不再被新记忆检索；重复启动不重复移动。"""
    root = paths.memories.resolve()
    children = [path for path in root.iterdir() if path.name not in {"automatic", "legacy-archive"}]
    if not children:
        return None
    archive = root / "legacy-archive" / datetime.now(UTC).strftime("%Y%m%dT%H%M%S%f")
    archive.mkdir(parents=True, exist_ok=False)
    for source in children:
        destination = archive / source.name
        if not source.resolve().is_relative_to(root) or not destination.resolve().is_relative_to(
            root
        ):
            raise ValueError("记忆归档路径越出数据目录")
        source.rename(destination)
    return str(Path(archive).relative_to(root))
