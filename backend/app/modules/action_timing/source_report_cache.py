"""只缓存已计算的源码报告；输入和分析器版本完全匹配才复用。"""

import gzip
import hashlib
import json
import logging
import sys
import tempfile
import zlib
from contextlib import suppress
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

logger = logging.getLogger(__name__)
CACHE_FORMAT = 1


def engine_signature():
    folder = Path(__file__).parent
    files = sorted(folder.glob("*.py"))
    files.extend(
        folder.parent / "source_analysis" / name for name in ("workspace.py", "collection.py")
    )
    digest = hashlib.sha256()
    digest.update(
        json.dumps(
            {
                "python": sys.version,
                "packages": {
                    name: version(name) for name in ("tree-sitter", "tree-sitter-c-sharp")
                },
            },
            sort_keys=True,
        ).encode()
    )
    for path in files:
        digest.update(str(path.relative_to(folder.parent)).encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def workspace_roots(workspace):
    return [
        workspace.root,
        *(child.root for _, child in getattr(workspace, "attached", {}).values()),
    ]


def valid_report(report):
    if not isinstance(report, dict) or not isinstance(report.get("source_revision"), str):
        return False
    if (
        not {
            "source_files",
            "source_projects",
            "source_dependencies",
            "package_contracts",
            "source_coverage",
            "scope",
            "notes",
            "assumptions",
        }
        <= report.keys()
    ):
        return False
    if report.get("mode") != "DryCycle" or report.get("basis") != "source_defaults":
        return False
    coverage, rows = report.get("action_coverage"), report.get("rows")
    if not isinstance(coverage, dict) or not isinstance(coverage.get("methods"), list):
        return False
    required = {
        "id",
        "name",
        "class_name",
        "method",
        "group",
        "formula",
        "entry",
        "known_delay_min_ms",
        "known_delay_max_ms",
        "motion_count",
        "wait_count",
        "stages",
        "parameters",
    }
    return isinstance(rows, list) and all(
        isinstance(row, dict)
        and required <= row.keys()
        and isinstance(row["entry"], dict)
        and {"path", "line"} <= row["entry"].keys()
        and isinstance(row["stages"], list)
        and isinstance(row["parameters"], list)
        for row in rows
    )


class SourceReportCache:
    def __init__(self, directory, workspace):
        self.directory = Path(directory).resolve()
        roots = workspace_roots(workspace)
        # 分析器不在业务源码根内写缓存，即使调用方误传了该目录。
        self.enabled = not any(self.directory.is_relative_to(root) for root in roots)
        identity = [str(root.resolve()) for root in roots]
        self.workspace_key = hashlib.sha256(json.dumps(identity).encode()).hexdigest()
        self.path = self.directory / f"{self.workspace_key}.json.gz"
        try:
            self.engine = engine_signature()
        except (OSError, PackageNotFoundError):
            self.enabled = False
            self.engine = ""

    def metadata(self, signature):
        return {
            "format": CACHE_FORMAT,
            "engine": self.engine,
            "workspace": self.workspace_key,
            "source": signature,
        }

    def load(self, signature):
        if not self.enabled:
            return None
        try:
            with gzip.open(self.path, "rt", encoding="utf-8") as stream:
                # 先核对短头部，源码失效时不解压旧的大报告。
                metadata = json.loads(stream.readline(4096))
                if metadata != self.metadata(signature):
                    return None
                pool = {}

                def intern_evidence(value):
                    if {"path", "line", "version", "code"} <= value.keys():
                        key = (value["path"], value["version"], value["code"])
                        if all(isinstance(item, str) for item in key):
                            shared = pool.setdefault(key, key)
                            value.update(zip(("path", "version", "code"), shared, strict=True))
                    return value

                report = json.load(stream, object_hook=intern_evidence)
            return report if valid_report(report) else None
        except (OSError, EOFError, UnicodeError, ValueError, TypeError, zlib.error):
            return None

    def save(self, signature, report):
        if not self.enabled:
            return
        temporary = None
        try:
            self.directory.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=self.directory, suffix=".tmp", delete=False
            ) as file:
                temporary = Path(file.name)
            with gzip.open(temporary, "wt", encoding="utf-8", compresslevel=1) as stream:
                stream.write(json.dumps(self.metadata(signature)) + "\n")
                json.dump(
                    report, stream, ensure_ascii=False, allow_nan=False, separators=(",", ":")
                )
            # 完整写完再替换；并发读取只能看到旧版本或完整的新版本。
            temporary.replace(self.path)
        except (OSError, ValueError, TypeError):
            logger.warning("动作耗时报告缓存未写入，本次源码计算结果仍可使用")
        finally:
            if temporary is not None:
                with suppress(OSError):
                    temporary.unlink(missing_ok=True)
