"""原图只校验格式和大小，不识别、裁切或改写图片内容。"""

import hashlib

MAX_IMAGE_BYTES = 8 * 1024 * 1024


def image_metadata(data: bytes, filename: str, recorded_at: str = "") -> dict:
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise ValueError("原图不能为空，且每张不能超过 8 MB")
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        media_type = "image/png"
    elif data.startswith(b"\xff\xd8\xff"):
        media_type = "image/jpeg"
    elif data.startswith((b"GIF87a", b"GIF89a")):
        media_type = "image/gif"
    elif data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        media_type = "image/webp"
    else:
        raise ValueError("原图仅支持 PNG、JPEG、GIF 或 WebP")
    name = filename.replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not name or len(name) > 250 or any(ord(char) < 32 for char in name):
        raise ValueError("请填写有效的图片文件名")
    if len(recorded_at) > 2000:
        raise ValueError("图片原记录时间过长")
    return {
        "id": hashlib.sha256(data).hexdigest(),
        "name": name,
        "recorded_at": recorded_at,
        "media_type": media_type,
    }
