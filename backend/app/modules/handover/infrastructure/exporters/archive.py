"""交接包导出适配器，不查询数据库。"""

import io
import json
import zipfile

from .word import render_word


def render_package(package, records, blobs, zipped=False):
    content = render_word(package, records)
    if not zipped:
        return content
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("handover.docx", content)
        archive.writestr(
            "manifest.json",
            json.dumps({"package": package, "records": records}, ensure_ascii=False, indent=2),
        )
        for row in records:
            if row["kind"] == "source":
                blob = blobs[row["id"]]
                archive.writestr(
                    f"sources/{row['id']}/v{row['version']}/{blob['name']}", blob["content"]
                )
    return stream.getvalue()


class DocumentPackageExporter:
    def render(self, package, records, blobs, zipped=False) -> bytes:
        return render_package(package, records, blobs, zipped)
