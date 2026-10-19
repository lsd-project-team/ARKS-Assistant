"""公开登录资源由可信构建清单固定；其余静态文件一律通过会话授权。"""

import hashlib
import json
import re
from pathlib import Path, PurePosixPath

LOGIN_IMAGES = {"brand/arks-assistant-icon.png", "brand/arks-login-mark.png"}


def public_name(name):
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_@./-]+", name):
        return False
    parts = name.split("/")
    return not any(part in {"", ".", ".."} for part in parts) and (
        name == "index.html" or name in LOGIN_IMAGES or name.startswith("assets/")
    )


class StaticAssets:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.public = self.load()

    def load(self):
        manifest = self.directory / "public-assets.json"
        if not manifest.exists():
            # 老版本或仅API部署没有白名单；不能退回公开整个assets目录。
            return frozenset()
        try:
            if manifest.is_symlink() or manifest.stat().st_size > 2 * 1024 * 1024:
                raise ValueError
            value = json.loads(manifest.read_text(encoding="utf-8"))
            files = value["files"]
            if (
                type(value["schema_version"]) is not int
                or value["schema_version"] != 1
                or not isinstance(files, dict)
                or not 0 < len(files) <= 4096
            ):
                raise ValueError
            for name, digest in files.items():
                if (
                    not public_name(name)
                    or not isinstance(digest, str)
                    or not re.fullmatch(r"[a-f0-9]{64}", digest)
                ):
                    raise ValueError
                file = self.directory / PurePosixPath(name)
                if file.resolve() != file or not file.is_file() or file.stat().st_nlink != 1:
                    raise ValueError
                if hashlib.sha256(file.read_bytes()).hexdigest() != digest:
                    raise ValueError
            if "index.html" not in files:
                raise ValueError
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise ValueError("登录资源白名单无效，请重新构建完整前端后启动") from error
        return frozenset("/" + name for name in files)

    def allows(self, path):
        return ("/index.html" if path == "/" else path) in self.public

    @staticmethod
    def cache_control(path):
        return "public, max-age=31536000, immutable" if path.startswith("/assets/") else "no-store"
