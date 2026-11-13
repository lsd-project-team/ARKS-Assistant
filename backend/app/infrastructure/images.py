"""图片文件的格式校验与发送前压缩；与业务存储无关。"""

import io

from PIL import Image, UnidentifiedImageError

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "GIF": "image/gif", "WEBP": "image/webp"}
# 供应商限制：单边最长 8192 像素，单图最大 32 MB（base64 计入 48 MB 请求体）。
MAX_SIDE = 8192
MAX_IMAGE_BYTES = 32 * 1024 * 1024
# 供应商会把更长的边缩到约 1300 像素；超过该尺寸或体积时先本地压缩，控制请求体。
SEND_MAX_SIDE = 2048
SEND_MAX_BYTES = 4 * 1024 * 1024


def inspect(data):
    """按实际内容判断格式与尺寸；损坏、非图片或超限在入口拒绝。"""
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = image.format or ""
            width, height = image.size
            frames = getattr(image, "n_frames", 1)
            image.verify()
    except UnidentifiedImageError:
        raise ValueError("图片内容不是有效的 JPEG、PNG、GIF 或 WebP 文件") from None
    except Image.DecompressionBombError:
        raise ValueError("图片像素过大，无法安全读取，请缩小后上传") from None
    except (OSError, SyntaxError, ValueError) as error:
        raise ValueError("图片损坏或无法解析，请重新导出后上传") from error
    if image_format not in MEDIA_TYPES:
        raise ValueError("仅支持 JPEG、PNG、GIF 和 WebP 图片")
    if max(width, height) > MAX_SIDE:
        raise ValueError(f"图片单边不能超过 8192 像素（当前 {width}×{height}）")
    return image_format, width, height, frames


def prepare(data):
    """返回发给模型的 media_type 与图片字节，限制单边和体积。"""
    image_format, width, height, _frames = inspect(data)
    if max(width, height) <= SEND_MAX_SIDE and len(data) <= SEND_MAX_BYTES:
        return MEDIA_TYPES[image_format], data
    with Image.open(io.BytesIO(data)) as image:
        image.seek(0)
        mode = "RGBA" if image_format in {"PNG", "GIF", "WEBP"} else "RGB"
        picture = image.convert(mode)
    # 长宽比不变；图片本身已按原图保存，这里只改发给模型的副本。
    picture.thumbnail((SEND_MAX_SIDE, SEND_MAX_SIDE))
    if image_format in {"PNG", "GIF"}:
        media_type, payload = _encode(picture, "PNG")
        if len(payload) > SEND_MAX_BYTES:
            media_type, payload = _encode(picture, "JPEG")
    else:
        media_type, payload = _encode(picture, "JPEG")
    return media_type, payload


def _encode(picture, image_format):
    buffer = io.BytesIO()
    if image_format == "JPEG":
        if picture.mode not in {"RGB", "L"}:
            background = Image.new("RGB", picture.size, "white")
            background.paste(picture, mask=picture.getchannel("A"))
            picture = background
        picture.save(buffer, format="JPEG", quality=88, optimize=True)
        return "image/jpeg", buffer.getvalue()
    picture.save(buffer, format="PNG", optimize=True)
    return "image/png", buffer.getvalue()


def media_type_of_file(path):
    """供图片读取接口声明真实类型；无法识别时返回 None。"""
    try:
        with Image.open(path) as image:
            return MEDIA_TYPES.get(image.format)
    except (UnidentifiedImageError, OSError, ValueError):
        return None
