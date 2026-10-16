import io
import stat
import zipfile
from pathlib import PurePosixPath

MAX_EXPANDED = 64 * 1024 * 1024


def safe_archive(data):
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as error:
        raise ValueError("附件不是有效的 ZIP 或 Word 文档") from error
    entries = archive.infolist()
    if len({item.filename for item in entries}) != len(entries):
        archive.close()
        raise ValueError("压缩包存在重复文件名，无法可靠定位固定版本")
    if len(entries) > 2000 or sum(item.file_size for item in entries) > MAX_EXPANDED:
        archive.close()
        raise ValueError("压缩包展开后超过 64 MB 或 2000 项，请缩小交接范围")
    for item in entries:
        path = PurePosixPath(item.filename.replace("\\", "/"))
        if (
            path.is_absolute()
            or ".." in path.parts
            or ":" in item.filename
            or stat.S_ISLNK(item.external_attr >> 16)
        ):
            archive.close()
            raise ValueError("压缩包包含不安全路径或符号链接")
        if item.flag_bits & 1:
            archive.close()
            raise ValueError("暂不支持加密压缩包")
    return archive
