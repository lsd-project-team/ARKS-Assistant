"""资料接入容量约束及原文件预览类型。"""

from pathlib import PurePosixPath

MAX_UPLOAD = 32 * 1024 * 1024
MAX_TEXT = 100000

# 仅这些原文件交给浏览器直接显示；其余格式按附件下载，不执行或转换文件内容。
INLINE_MEDIA_TYPES = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "gif": "image/gif",
    "webp": "image/webp",
    **{
        extension: "text/plain"
        for extension in (
            "txt",
            "md",
            "cs",
            "cpp",
            "c",
            "h",
            "json",
            "yaml",
            "yml",
            "xml",
            "ini",
            "log",
        )
    },
}


def original_media_type(filename):
    return INLINE_MEDIA_TYPES.get(PurePosixPath(filename).suffix.lstrip(".").lower())
