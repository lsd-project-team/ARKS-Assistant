"""原始附件与导出文件响应。"""

from urllib.parse import quote

from fastapi.responses import Response

from app.modules.handover.domain.materials import original_media_type


def attachment(content, filename, media_type, *, inline=False):
    preview_type = original_media_type(filename) if inline else None
    disposition = "inline" if preview_type else "attachment"
    return Response(
        content,
        media_type=preview_type or media_type,
        headers={
            "Content-Disposition": f"{disposition}; filename*=UTF-8''{quote(filename, safe='')}",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "SAMEORIGIN",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )
