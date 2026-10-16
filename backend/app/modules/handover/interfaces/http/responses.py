"""原始附件与导出文件响应。"""

from urllib.parse import quote

from fastapi.responses import Response


def attachment(content, filename, media_type):
    return Response(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
