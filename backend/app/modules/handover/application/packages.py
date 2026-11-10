"""交接包用例：解析固定版本来源，再交给导出适配器渲染。"""

from app.modules.handover.application.ports import PackageExporter, RecordRepository
from app.modules.handover.domain.rules import linked_ids


def package_references(store, record_ids):
    queue = [(identifier, None) for identifier in dict.fromkeys(record_ids)]
    references, seen = [], set()
    while queue:
        identifier, version = queue.pop(0)
        row = store.get(identifier, version)
        key = row["id"], row["version"]
        if key in seen:
            continue
        if row["state"] == "archived" or row["kind"] == "package":
            raise ValueError("交接包来源有归档或非业务记录，请先复核选择范围")
        seen.add(key)
        if len(seen) > 1000:
            raise ValueError("交接包超过 1000 条版本，请拆分交接范围")
        references.append({"record_id": identifier, "version": row["version"]})
        evidence_ids = set()
        for evidence in row["payload"].get("evidence", []):
            evidence_ids.add(evidence["record_id"])
            queue.append((evidence["record_id"], evidence["version"]))
        for related in linked_ids(row["payload"]) - evidence_ids:
            # 接收记录保留原包的 ID 与版本，避免把旧包递归嵌套进新包。
            if related != row["payload"].get("package_id"):
                queue.append((related, None))
    return references


def export_package(
    store: RecordRepository, identifier, exporter: PackageExporter, zipped=False, version=None
):
    with store.lock:
        current = store.get(identifier)
        if current["kind"] != "package":
            raise ValueError("请选择交接包")
        # 同步核对当前状态和固定快照，旧链接不能绕过撤回、归档或来源变化。
        package = store.get(identifier, version) if version is not None else current
        if current["state"] != "confirmed" or package["state"] != "confirmed":
            raise ValueError("交接包未确认，请确认后再下载")
        records = [
            store.get(ref["record_id"], ref["version"]) for ref in package["payload"]["records"]
        ]
        blobs = {
            row["id"]: store.blob(row["id"])
            for row in records
            if zipped and row["kind"] == "source"
        }
    return exporter.render(package, records, blobs, zipped)
