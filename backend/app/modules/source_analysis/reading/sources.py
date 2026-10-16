"""逐根建立源码清单；大文件和长行不依赖工作区的整文件大小限制。"""

import codecs
import hashlib
import os
from pathlib import Path

from app.agents.context.tokens import text_tokens
from app.modules.source_analysis.workspace import IGNORED

TEXT_SUFFIXES = frozenset(
    ".cs .py .js .jsx .ts .tsx .vue .svelte .html .htm .css .scss .less .json .jsonc "
    ".xml .csproj .sln .props .targets .config .yaml .yml .toml .ini .sql .md .txt "
    ".ps1 .sh .bat .cmd .c .h .cpp .hpp .rs .go .java .kt .vb .resx .xaml .razor "
    ".proto .r .swift .fs .fsproj .vbproj .slnx .editorconfig .gitignore".split()
)
TEXT_NAMES = {"dockerfile", "makefile", "cmakelists.txt", ".gitignore", ".editorconfig"}
CHUNK_CHARACTERS = 8000
CHUNK_TOKENS = 3500


def roots(workspace):
    if hasattr(workspace, "primary"):
        yield "", workspace.primary
        for source_id, (_, child) in sorted(workspace.attached.items()):
            yield f"@sources/{source_id}/", child
    else:
        yield "", workspace


def module_name(path):
    parts = path.split("/")
    if path.startswith("@sources/"):
        prefix = "/".join(parts[:2])
        return prefix + ("/" + parts[2] if len(parts) > 3 else "")
    return parts[0] if len(parts) > 1 else "根目录"


def fingerprint(target: Path):
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def source_encoding(target):
    with target.open("rb") as stream:
        sample = stream.read(16384)
    if sample.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if b"\x00" in sample:
        raise ValueError("二进制文件")
    try:
        codecs.getincrementaldecoder("utf-8-sig")().decode(sample, final=False)
        return "utf-8-sig"
    except UnicodeDecodeError:
        codecs.getincrementaldecoder("gb18030")().decode(sample, final=False)
        return "gb18030"


def describe(workspace, path):
    target = workspace.resolve(path)
    if not target.is_file():
        raise FileNotFoundError("源文件不存在")
    return {"source_version": fingerprint(target), "encoding": source_encoding(target)}


def snapshot(workspace):
    records = []
    for prefix, child in roots(workspace):

        def scan_error(error, base=child, lead=prefix):
            try:
                relative = Path(error.filename).relative_to(base.root).as_posix()
            except (ValueError, TypeError):
                relative = "."
            records.append(record(lead + relative, "failed", str(error)))

        for folder, directories, names in os.walk(
            child.root, followlinks=False, onerror=scan_error
        ):
            for name in sorted(list(directories)):
                target = Path(folder) / name
                if name in IGNORED or target.is_symlink() or target.is_junction():
                    path = prefix + target.relative_to(child.root).as_posix() + "/"
                    records.append(record(path, "excluded", "忽略目录或目录链接"))
                    directories.remove(name)
            for name in sorted(names):
                target = Path(folder) / name
                path = prefix + target.relative_to(child.root).as_posix()
                if (
                    target.is_symlink()
                    or target.suffix.lower() not in TEXT_SUFFIXES
                    and (name.lower() not in TEXT_NAMES)
                ):
                    records.append(record(path, "excluded", "文件链接或不支持的文件类型"))
                    continue
                try:
                    records.append({**record(path, "pending"), **describe(workspace, path)})
                except UnicodeError:
                    records.append(record(path, "failed", "无法识别文件编码"))
                except ValueError as error:
                    records.append(record(path, "excluded", str(error)))
                except OSError as error:
                    records.append(record(path, "failed", str(error)))
    return sorted(records, key=lambda row: row["path"])


def record(path, status, error=""):
    return dict(
        path=path,
        module=module_name(path),
        status=status,
        error=error,
        source_version="",
        encoding="utf-8-sig",
        indexed=status == "pending",
    )


def chunks(workspace, path, encoding):
    """字符和 token 双边界，单行再长也切开，续读序号只依赖原始版本。"""
    line, index = 1, 0
    with workspace.resolve(path).open("r", encoding=encoding, newline="") as stream:
        while text := stream.read(CHUNK_CHARACTERS):
            while text:
                size = len(text)
                while text_tokens(text[:size]) > CHUNK_TOKENS:
                    size = max(1, size // 2)
                piece, text = text[:size], text[size:]
                end = line + piece.count("\n") - (1 if piece.endswith("\n") else 0)
                yield dict(index=index, text=piece, start_line=line, end_line=max(line, end))
                line += piece.count("\n")
                index += 1
        if index == 0:
            yield dict(index=0, text="", start_line=1, end_line=1)
