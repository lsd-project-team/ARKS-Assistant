"""源码读取、文本检索与 C# 语法符号；所有入口共享根目录边界。"""

import base64
import fnmatch
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from itertools import islice
from pathlib import Path, PurePosixPath

import tree_sitter_c_sharp
from tree_sitter import Language, Parser

from app.version_cache import VersionCache

IGNORED = {
    ".git",
    ".vs",
    "bin",
    "obj",
    "packages",
    "node_modules",
    "__pycache__",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
MAX_FILE_BYTES = 2_000_000


def content_version(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_source(data: bytes) -> tuple[str, str]:
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), "UTF-16"
    if b"\x00" in data:
        raise ValueError("该文件是二进制文件，不能作为文本打开")
    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding), encoding.upper()
        except UnicodeDecodeError:
            continue
    raise ValueError("无法识别该文件编码")


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.id = content_version(str(self.root).encode())[:32]
        self.source_id = self.id
        self.source_cache = VersionCache()
        self.symbol_cache = VersionCache(max_bytes=8_000_000)

    def resolve(self, relative: str = "") -> Path:
        normalized = relative.replace("\\", "/")
        segments = PurePosixPath(normalized).parts
        if ":" in normalized or normalized.startswith("/") or ".." in segments:
            raise ValueError("只能访问工作区内的相对路径")
        if any(segment in IGNORED for segment in segments):
            raise ValueError("该目录已从源码工作区排除")
        target = (self.root / normalized).resolve()
        # resolve 后再验证，阻止目录联接或符号链接绕过工作区边界。
        if not target.is_relative_to(self.root):
            raise ValueError("路径超出源码工作区")
        return target

    def relative(self, path: Path) -> str:
        return path.relative_to(self.root).as_posix()

    def tree(self, path: str = "") -> list[dict]:
        folder = self.resolve(path)
        if not folder.is_dir():
            raise ValueError("目录不存在")
        entries = []
        for child in folder.iterdir():
            if child.name in IGNORED or child.is_symlink():
                continue
            if not child.resolve().is_relative_to(self.root):
                continue
            entries.append(
                {
                    "path": self.relative(child),
                    "name": child.name,
                    "is_dir": child.is_dir(),
                    "size": child.stat().st_size,
                }
            )
        return sorted(entries, key=lambda item: (not item["is_dir"], item["name"].casefold()))

    def read(self, path: str) -> dict:
        target = self.resolve(path)
        if not target.is_file():
            raise FileNotFoundError("源码文件不存在")
        if target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("文件超过 2 MB，请通过搜索定位需要的片段")
        data = target.read_bytes()
        version = content_version(data)
        content, encoding = self.source_cache.get_or_create(
            (self.relative(target), version), lambda: decode_source(data), len(data) * 4
        )
        return {
            "path": self.relative(target),
            "source_workspace_id": self.source_id,
            "content": content,
            "encoding": encoding,
            "version": version,
            "line_count": len(content.splitlines()),
        }

    def files(self):
        for folder, directories, names in os.walk(self.root, followlinks=False):
            directories[:] = [
                name
                for name in directories
                if name not in IGNORED and not (Path(folder) / name).is_symlink()
            ]
            for name in names:
                target = Path(folder) / name
                if not target.is_symlink() and target.resolve().is_relative_to(self.root):
                    yield target

    def find_files(self, query: str, limit: int = 100) -> list[dict]:
        matches = (
            {"path": self.relative(path), "name": path.name}
            for path in self.files()
            if query.casefold() in self.relative(path).casefold()
        )
        return list(islice(matches, limit))

    def search(self, query: str, glob: str = "*", limit: int = 100) -> dict:
        if not query or len(query) > 300:
            raise ValueError("搜索词长度必须在 1 到 300 之间")
        # GB18030 的中文字节不能直接匹配 UTF-8 查询，先按文件编码解码。
        if not query.isascii():
            return self._search_python(query, glob, limit)
        executable = shutil.which("rg")
        if executable:
            result = self._ripgrep(executable, query, glob, limit)
            if result is not None:
                return result
        return self._search_python(query, glob, limit)

    def _ripgrep(self, executable: str, query: str, glob: str, limit: int):
        arguments = [
            executable,
            "--json",
            "--fixed-strings",
            "--ignore-case",
            "--hidden",
            "--max-count",
            str(limit + 1),
            "--glob",
            glob,
        ]
        for directory in IGNORED:
            arguments.extend(["--glob", f"!**/{directory}/**"])
        arguments.extend(["--", query, "."])
        try:
            result = subprocess.run(
                arguments, cwd=self.root, capture_output=True, timeout=12, check=False
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if result.returncode not in (0, 1):
            return None
        matches = []
        for row in result.stdout.decode("utf-8", errors="replace").splitlines():
            event = json.loads(row)
            if event["type"] != "match":
                continue
            data = event["data"]
            path = data["path"].get("text", "").replace("\\", "/").removeprefix("./")
            try:
                self.resolve(path)
            except ValueError:
                continue
            text = data["lines"].get("text")
            if text is None:
                try:
                    text, _ = decode_source(base64.b64decode(data["lines"]["bytes"]))
                except (KeyError, ValueError):
                    continue
            matches.append(
                {
                    "path": path,
                    "line": data["line_number"],
                    "text": text.strip()[:500],
                }
            )
            if len(matches) > limit:
                break
        return {"matches": matches[:limit], "truncated": len(matches) > limit, "engine": "ripgrep"}

    def _search_python(self, query: str, glob: str, limit: int) -> dict:
        matches = []
        for target in self.files():
            path = self.relative(target)
            if not fnmatch.fnmatch(path, glob) and not fnmatch.fnmatch(target.name, glob):
                continue
            try:
                source = self.read(path)
            except (ValueError, OSError):
                continue
            for line, text in enumerate(source["content"].splitlines(), 1):
                if query.casefold() in text.casefold():
                    matches.append({"path": path, "line": line, "text": text.strip()[:500]})
                if len(matches) > limit:
                    return {"matches": matches[:limit], "truncated": True, "engine": "python"}
        return {"matches": matches, "truncated": False, "engine": "python"}

    def symbols(self, path: str) -> dict:
        source = self.read(path)
        if not path.lower().endswith(".cs"):
            return {"symbols": [], "version": source["version"]}
        parsed = self.symbol_cache.get_or_create(
            (source["path"], source["version"]),
            lambda: self._parse_symbols(source),
            len(source["content"].encode("utf-8")) * 2,
        )
        # 返回的数据可由调用者排序，不允许影响其他窗口共享的缓存。
        return {**parsed, "symbols": [dict(item) for item in parsed["symbols"]]}

    @staticmethod
    def _parse_symbols(source):
        from app.csharp_analysis import DOTNET, HELPER

        command = (
            [str(DOTNET), str(HELPER)]
            if DOTNET.is_file() and HELPER.is_file()
            else [sys.executable, "-m", "app.symbol_parser"]
        )
        try:
            response = subprocess.run(
                command,
                input=json.dumps({**source, "action": "syntax"}) + "\n",
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=20,
                cwd=Path(__file__).resolve().parents[1],
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            if response.returncode == 0:
                parsed = json.loads(response.stdout)
                for item in parsed.get("symbols", []):
                    item["kind"] = re.sub(r"(?<!^)(?=[A-Z])", "_", item["kind"]).lower()
                return {**parsed, "version": source["version"]}
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        return {
            "symbols": [],
            "version": source["version"],
            "has_syntax_errors": True,
            "analysis": "unavailable",
            "reason": "语法解析失败，需按显式行号补读源码",
        }

    @staticmethod
    def _native_symbols(source):
        parser = Parser(Language(tree_sitter_c_sharp.language()))
        tree = parser.parse(source["content"].encode("utf-8"))
        symbols = []
        pending = [tree.root_node]
        kinds = {
            "class_declaration",
            "interface_declaration",
            "method_declaration",
            "constructor_declaration",
            "enum_declaration",
            "property_declaration",
        }
        while pending:
            node = pending.pop()
            if node.type in kinds:
                name = node.child_by_field_name("name")
                if name:
                    symbols.append(
                        {
                            "name": name.text.decode(),
                            "kind": node.type,
                            "line": node.start_point.row + 1,
                            "end_line": node.end_point.row + 1,
                        }
                    )
            pending.extend(reversed(node.children))
        return {
            "symbols": symbols,
            "version": source["version"],
            "has_syntax_errors": tree.root_node.has_error,
        }
