"""将受约束的源码服务映射到 Deep Agents 文件协议。"""

import fnmatch

from deepagents.backends.protocol import (
    BackendProtocol,
    DeleteResult,
    EditResult,
    GlobResult,
    GrepResult,
    LsResult,
    ReadResult,
    WriteResult,
)

from app.models import now_iso
from app.workspace import Workspace


class SourceBackend(BackendProtocol):
    def __init__(self, workspace: Workspace):
        self.workspace = workspace

    @staticmethod
    def relative(path: str | None) -> str:
        return (path or "").removeprefix("/")

    def ls(self, path: str) -> LsResult:
        try:
            entries = self.workspace.tree(self.relative(path))
            return LsResult(entries=[{**entry, "path": "/" + entry["path"]} for entry in entries])
        except (OSError, ValueError) as error:
            return LsResult(error=str(error))

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        if limit <= 0:
            return ReadResult(no_lines_requested=True)
        try:
            source = self.workspace.read(self.relative(file_path))
            lines = source["content"].splitlines()
            offset = max(0, offset)
            selected = lines[offset : offset + min(limit, 2000)]
            timestamp = now_iso()
            data = {
                "content": "\n".join(selected),
                "encoding": "utf-8",
                "created_at": timestamp,
                "modified_at": timestamp,
            }
            if not selected:
                return ReadResult(file_data=data)
            end = offset + len(selected)
            return ReadResult(
                file_data=data,
                total_lines=len(lines),
                start_line=offset + 1,
                end_line=end,
                next_offset=end if end < len(lines) else None,
            )
        except (OSError, ValueError) as error:
            return ReadResult(error=str(error))

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
    ) -> GrepResult:
        try:
            relative = self.relative(path)
            self.workspace.resolve(relative)
            result = self.workspace.search(pattern, glob or "*", min(max_count or 100, 100))
            matches = [
                {**match, "path": "/" + match["path"]}
                for match in result["matches"]
                if not relative
                or match["path"].startswith(relative.rstrip("/") + "/")
                or match["path"] == relative
            ]
            return GrepResult(matches=matches, truncated=result["truncated"])
        except (OSError, ValueError) as error:
            return GrepResult(error=str(error))

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        try:
            relative = self.relative(path)
            folder = self.workspace.resolve(relative)
            matches = [
                {"path": "/" + self.workspace.relative(target), "is_dir": False}
                for target in self.workspace.files()
                if (not relative or target.is_relative_to(folder))
                and (
                    fnmatch.fnmatch(self.workspace.relative(target), pattern)
                    or fnmatch.fnmatch(target.name, pattern)
                )
            ]
            return GlobResult(matches=matches[:200])
        except (OSError, ValueError) as error:
            return GlobResult(error=str(error))

    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error="源码工作区只读")

    def edit(
        self, file_path: str, old_string: str, new_string: str, replace_all: bool = False
    ) -> EditResult:
        return EditResult(error="源码工作区只读")

    def delete(self, file_path: str, recursive: bool = False) -> DeleteResult:
        return DeleteResult(error="源码工作区只读")
