"""项目目录内的通用文件读写；路径限制在项目根，保留原编码与换行。"""

import base64
import codecs
import fnmatch
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.infrastructure.storage.files import digest, is_link, safe_path

MAX_FILE_BYTES = 2_000_000
MAX_BINARY_BYTES = 10_000_000
MAX_LIST_ENTRIES = 2_000
MAX_SEARCH_RESULTS = 200
MAX_HITS_PER_FILE = 20
EXCLUDED = {
    ".git",
    ".vs",
    ".svn",
    ".idea",
    ".venv",
    "venv",
    "bin",
    "obj",
    "packages",
    "node_modules",
    "dist",
    "publish",
    "build",
    "out",
    "target",
    "coverage",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    ".gradle",
    ".next",
}
BINARY_SUFFIXES = {
    ".dll",
    ".exe",
    ".pdb",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".zip",
    ".7z",
    ".rar",
    ".pdf",
    ".sqlite3",
    ".db",
    ".nupkg",
}


def project_root(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("项目目录不存在，请先创建或选择目录")
    return root


def resolve(root, relative=""):
    """把项目内相对路径解析为绝对路径；拒绝绝对路径和 .. 逃逸。"""
    relative = (relative or "").replace("\\", "/").strip()
    if Path(relative).is_absolute():
        raise ValueError("请使用项目内的相对路径")
    return safe_path(project_root(root), relative or ".", allow_root=True)


def relative(root, path):
    return Path(path).resolve().relative_to(project_root(root)).as_posix()


def _decode(data):
    for bom, encoding in (
        (codecs.BOM_UTF8, "utf-8-sig"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
    ):
        if data.startswith(bom):
            return data.decode(encoding), encoding
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ValueError("文件不是可识别的文本编码（支持 UTF-8 / UTF-16 / GB18030）")


def _looks_binary(path, data):
    if path.suffix.lower() in BINARY_SUFFIXES:
        return True
    sample = data[:8000]
    return b"\x00" in sample


def read_text(root, path, start_line=1, end_line=400):
    target = resolve(root, path)
    if not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    data = target.read_bytes()
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"文件超过 {MAX_FILE_BYTES // 1_000_000} MB，请改用命令读取")
    if _looks_binary(target, data):
        raise ValueError("这是二进制文件，不能按文本读取")
    text, encoding = _decode(data)
    lines = text.replace("\r\n", "\n").split("\n")
    start = max(1, int(start_line))
    end = min(len(lines), max(start, int(end_line)))
    numbered = "\n".join(f"{index:>5} {lines[index - 1]}" for index in range(start, end + 1))
    return {
        "path": relative(root, target),
        "start_line": start,
        "end_line": end,
        "total_lines": len(lines),
        "encoding": encoding,
        "version": digest(data),
        "content": numbered,
    }


def read_binary(root, path, limit=32 * 1024 * 1024):
    """按原字节读取项目内文件；图片查看使用，不做文本解码。"""
    target = resolve(root, path)
    if not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    size = target.stat().st_size
    if size > limit:
        raise ValueError(f"文件超过 {limit // (1024 * 1024)} MB，不能直接查看")
    return relative(root, target), target.read_bytes()


def write_text(root, path, content, expected_hash=""):
    target = resolve(root, path)
    if target.is_dir():
        raise ValueError("目标是目录，不能写入")
    exists = target.is_file()
    original = None
    if exists:
        if not expected_hash:
            raise ValueError("覆盖已有文件必须带上一次读取的 version，避免覆盖他人修改")
        original = target.read_bytes()
        if digest(original) != expected_hash:
            raise ValueError("文件已被修改，请重新读取后再写")
    if len(content.encode("utf-8")) > MAX_FILE_BYTES:
        raise ValueError("写入内容超过 2 MB 限制")
    data, _encoding = _encode_like(original, content)
    atomic_bytes(target, data)
    return {
        "path": relative(root, target),
        "version": digest(data),
        "bytes": len(data),
        "created": not exists,
    }


def _normalized(text):
    return text.replace("\r\n", "\n")


def _encode_like(original, content):
    """按原文件的编码、BOM 和换行写回；新文件使用 UTF-8 + LF。"""
    text = _normalized(content)
    if original is None:
        return text.encode("utf-8"), "utf-8"
    decoded, detected = _decode(original)
    if detected.startswith("utf-16"):
        encoding = "utf-16"
    elif detected == "utf-8-sig":
        encoding = "utf-8"
    else:
        encoding = detected
    bom = b""
    if original.startswith(codecs.BOM_UTF8):
        bom = codecs.BOM_UTF8
    elif detected.startswith("utf-16"):
        bom = original[:2]
    if "\r\n" in decoded:
        text = text.replace("\n", "\r\n")
    if encoding == "utf-8":
        return bom + text.encode("utf-8"), encoding
    if encoding == "gb18030":
        return text.encode("gb18030"), encoding
    return bom + text.encode("utf-16-le" if bom == codecs.BOM_UTF16_LE else "utf-16-be"), encoding


def edit_text(root, path, edits, expected_hash=""):
    """在已有文件中按精确文本替换；一次读取、一次原子写回。"""
    target = resolve(root, path)
    if not target.is_file():
        raise FileNotFoundError(f"文件不存在：{path}")
    if not expected_hash:
        raise ValueError("编辑已有文件必须带上一次读取的 version")
    original = target.read_bytes()
    if digest(original) != expected_hash:
        raise ValueError("文件已被修改，请重新读取后再写")
    text, _encoding = _decode(original)
    body = _normalized(text)
    replacements = 0
    for index, edit in enumerate(edits, 1):
        old = _normalized(str(edit.get("old", edit.get("old_string", ""))))
        new = _normalized(str(edit.get("new", edit.get("new_string", ""))))
        if not old:
            raise ValueError(f"第 {index} 处替换的原文不能为空")
        count = body.count(old)
        if count == 0:
            raise ValueError(f"第 {index} 处没有找到要替换的原文，请重新读取文件确认")
        if count > 1 and not edit.get("replace_all"):
            raise ValueError(
                f"第 {index} 处匹配到 {count} 个位置，请提供更长的上下文或设置 replace_all"
            )
        body = body.replace(old, new, -1 if edit.get("replace_all") else 1)
        replacements += count if edit.get("replace_all") else 1
    data, _encoding = _encode_like(original, body)
    atomic_bytes(target, data)
    return {
        "path": relative(root, target),
        "version": digest(data),
        "bytes": len(data),
        "replacements": replacements,
    }


def write_binary(root, path, content_base64, expected_hash=""):
    """写入图片、图标等二进制资源（内容用 base64 传递）。"""
    target = resolve(root, path)
    if target.is_dir():
        raise ValueError("目标是目录，不能写入")
    try:
        data = base64.b64decode(content_base64, validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError("二进制内容必须是有效的 base64") from error
    if len(data) > MAX_BINARY_BYTES:
        raise ValueError("二进制内容超过 10 MB 限制")
    exists = target.is_file()
    original = None
    if exists:
        if not expected_hash:
            raise ValueError("覆盖已有文件必须带上一次读取的 version")
        original = target.read_bytes()
        if digest(original) != expected_hash:
            raise ValueError("文件已被修改，请重新读取后再写")
    atomic_bytes(target, data)
    return {
        "path": relative(root, target),
        "version": digest(data),
        "bytes": len(data),
        "created": not exists,
    }


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".coding-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def create_directory(root, path):
    target = resolve(root, path)
    if target.exists():
        raise ValueError("目录或文件已存在")
    target.mkdir(parents=True)
    return {"path": relative(root, target)}


def move(root, path, destination):
    source = resolve(root, path)
    target = resolve(root, destination)
    if not source.exists():
        raise FileNotFoundError(f"路径不存在：{path}")
    if target.exists():
        raise ValueError("目标已存在，不能覆盖")
    target.parent.mkdir(parents=True, exist_ok=True)
    source.rename(target)
    return {"from": relative(root, source), "to": relative(root, target)}


def delete(root, path, recursive=False):
    target = resolve(root, path)
    if not target.exists():
        raise FileNotFoundError(f"路径不存在：{path}")
    if target == project_root(root):
        raise ValueError("不能删除项目根目录")
    if target.is_dir():
        if not recursive:
            raise ValueError("删除目录需要显式 recursive=true")
        import shutil

        shutil.rmtree(target)
    else:
        target.unlink()
    return {"path": relative(root, target) if target.exists() else path}


def list_tree(root, path=".", depth=2):
    base = resolve(root, path)
    if not base.is_dir():
        raise ValueError("不是目录")
    rows = []
    base_depth = len(base.relative_to(project_root(root)).parts)

    def walk(directory):
        nonlocal rows
        for entry in sorted(
            directory.iterdir(), key=lambda item: (item.is_file(), item.name.lower())
        ):
            if entry.name in EXCLUDED or is_link(entry):
                continue
            current = len(entry.relative_to(project_root(root)).parts)
            if current - base_depth > depth:
                continue
            if entry.is_dir():
                rows.append(f"{entry.relative_to(project_root(root)).as_posix()}/")
                if len(rows) < MAX_LIST_ENTRIES:
                    walk(entry)
            else:
                rows.append(entry.relative_to(project_root(root)).as_posix())
            if len(rows) >= MAX_LIST_ENTRIES:
                return

    walk(base)
    return {
        "path": relative(root, base) if base != project_root(root) else ".",
        "entries": rows[:MAX_LIST_ENTRIES],
    }


def _walk_files(root, base):
    """按目录剪枝遍历文件，跳过构建产物、版本库和链接。"""
    if base.is_file():
        yield base
        return
    for folder, directories, names in os.walk(base, followlinks=False):
        directories[:] = sorted(
            name
            for name in directories
            if name not in EXCLUDED and not is_link(Path(folder) / name)
        )
        for name in sorted(names):
            target = Path(folder) / name
            if name in EXCLUDED or is_link(target):
                continue
            yield target


def _rg_results(root, base, query, glob, limit):
    executable = shutil.which("rg")
    if not executable:
        return None
    arguments = [
        executable,
        "--line-number",
        "--no-heading",
        "--color",
        "never",
        "--fixed-strings",
        "--ignore-case",
        "--max-count",
        str(MAX_HITS_PER_FILE),
    ]
    for name in sorted(EXCLUDED):
        arguments += ["--glob", f"!**/{name}/**"]
    if glob:
        arguments += ["--glob", glob]
    arguments += ["--", query, str(base)]
    try:
        result = subprocess.run(
            arguments,
            capture_output=True,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode not in (0, 1):
        return None
    rows, root_path = [], project_root(root)
    for line in result.stdout.decode("utf-8", "replace").splitlines():
        match = re.match(r"^(.*):(\d+):(.*)$", line)
        if not match:
            continue
        try:
            path = Path(match.group(1)).resolve().relative_to(root_path).as_posix()
        except (OSError, ValueError):
            continue
        rows.append({"path": path, "line": int(match.group(2)), "text": match.group(3)[:300]})
        if len(rows) >= min(limit, MAX_SEARCH_RESULTS):
            break
    return rows


def search_text(root, query, path=".", glob="", limit=100):
    query = query.strip()
    if not query:
        raise ValueError("搜索内容不能为空")
    base = resolve(root, path)
    if base.is_file() and glob and not fnmatch.fnmatch(base.name, glob):
        return {"query": query, "results": []}
    rows = _rg_results(root, base, query, glob, limit)
    if rows is not None:
        return {"query": query, "results": rows}
    rows, scanned = [], 0
    for file in _walk_files(root, base):
        if len(rows) >= min(limit, MAX_SEARCH_RESULTS):
            break
        if glob and not fnmatch.fnmatch(file.name, glob):
            continue
        scanned += 1
        if scanned > 5000 or file.stat().st_size > MAX_FILE_BYTES:
            continue
        try:
            data = file.read_bytes()
            if _looks_binary(file, data):
                continue
            text, _ = _decode(data)
        except (ValueError, OSError):
            continue
        hits = 0
        for number, line in enumerate(text.replace("\r\n", "\n").split("\n"), 1):
            if query.lower() not in line.lower():
                continue
            rows.append(
                {
                    "path": file.relative_to(project_root(root)).as_posix(),
                    "line": number,
                    "text": line.strip()[:300],
                }
            )
            hits += 1
            if hits >= MAX_HITS_PER_FILE or len(rows) >= min(limit, MAX_SEARCH_RESULTS):
                break
    return {"query": query, "results": rows[:MAX_SEARCH_RESULTS]}


def find_files(root, pattern, path=".", limit=100):
    pattern = pattern.strip() or "*"
    base = resolve(root, path)
    rows = []
    for file in _walk_files(root, base):
        rel = file.relative_to(project_root(root)).as_posix()
        if fnmatch.fnmatch(file.name, pattern) or fnmatch.fnmatch(rel, pattern):
            rows.append(rel)
            if len(rows) >= max(1, min(limit, 500)):
                break
    return {"pattern": pattern, "entries": rows}


def detect_project(root):
    """按目录中的工程文件给出语言和构建/测试命令建议；识别失败不影响编码。"""
    root = project_root(root)
    try:
        names = {entry.name for entry in root.iterdir()}
    except OSError:
        return {}
    if any(name.endswith((".sln", ".csproj")) for name in names):
        return {"language": ".NET", "build": "dotnet build", "test": "dotnet test"}
    if "package.json" in names:
        scripts = {}
        try:
            scripts = json.loads((root / "package.json").read_text(encoding="utf-8")).get(
                "scripts", {}
            )
        except (OSError, ValueError):
            scripts = {}
        return {
            "language": "JavaScript/TypeScript",
            "build": "npm run build" if "build" in scripts else "",
            "test": "npm test" if "test" in scripts else "",
        }
    if (
        names & {"pyproject.toml", "pytest.ini", "setup.cfg", "setup.py"}
        or (root / "tests").is_dir()
    ):
        return {"language": "Python", "build": "", "test": "python -m pytest"}
    if "Cargo.toml" in names:
        return {"language": "Rust", "build": "cargo build", "test": "cargo test"}
    if "go.mod" in names:
        return {"language": "Go", "build": "go build ./...", "test": "go test ./..."}
    if "pom.xml" in names:
        return {"language": "Java", "build": "mvn package", "test": "mvn test"}
    if any(name.startswith("build.gradle") for name in names):
        return {"language": "Java/Kotlin", "build": "gradle build", "test": "gradle test"}
    if "CMakeLists.txt" in names:
        return {"language": "C/C++", "build": "cmake --build build", "test": ""}
    return {}


def tree_snapshot(root, depth=2):
    return json.dumps(list_tree(root, ".", depth), ensure_ascii=False)
