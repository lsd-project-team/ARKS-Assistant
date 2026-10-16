import hashlib

from app.modules.source_analysis.workspace import decode_source

from .archive import safe_archive


def parse_snapshot(data):
    files, previews, skipped = [], [], 0
    with safe_archive(data) as archive:
        for item in archive.infolist():
            if item.is_dir():
                continue
            raw = archive.read(item)
            path = item.filename.replace("\\", "/")
            files.append(
                {"path": path, "sha256": hashlib.sha256(raw).hexdigest(), "size": str(len(raw))}
            )
            try:
                if len(raw) > 2_000_000:
                    raise ValueError("大文件")
                text, _ = decode_source(raw)
                previews.append(f"[文件 {path}]\n{text[:10000]}")
                skipped += int(len(text) > 10000)
            except ValueError:
                skipped += 1
    notes = (
        f"固定源码快照，共 {len(files)} 文件。每文件预览最多 10000 字；{skipped} 项未完整预览。"
        "完整原件可下载，文件哈希用于比对，不代表功能验证通过。"
    )
    return "\n\n".join(previews), "readable", notes, files
