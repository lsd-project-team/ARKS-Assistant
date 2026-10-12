"""主目录保留旧路径，附加目录使用稳定身份前缀，避免同名文件混淆。"""

from pathlib import Path

from app.csharp_analysis import CSharpAnalysis
from app.workspace import Workspace


def source_prefix(source_id):
    return f"@sources/{source_id}/"


class SourceCollection(Workspace):
    def __init__(self, root, folders):
        super().__init__(root)
        self.primary = Workspace(root)
        self.attached = {
            item["source_id"]: (item["label"], Workspace(Path(item["root"]))) for item in folders
        }

    def locate(self, path):
        normalized = path.replace("\\", "/")
        if normalized.startswith("@sources/"):
            source_id, _, relative = normalized[len("@sources/") :].partition("/")
            if source_id not in self.attached:
                raise FileNotFoundError("此源码目录已解除关联，请从历史引用打开原目录")
            return self.attached[source_id][1], relative, source_prefix(source_id)
        return self.primary, normalized, ""

    def resolve(self, relative=""):
        workspace, path, _ = self.locate(relative)
        return workspace.resolve(path)

    def relative(self, path):
        if path.is_relative_to(self.root):
            return self.primary.relative(path)
        for source_id, (_, workspace) in self.attached.items():
            if path.is_relative_to(workspace.root):
                return source_prefix(source_id) + workspace.relative(path)
        raise ValueError("路径超出项目的所有源码目录")

    def tree(self, path=""):
        if not path:
            groups = [
                {"path": source_prefix(key).rstrip("/"), "name": label, "is_dir": True, "size": 0}
                for key, (label, _) in self.attached.items()
            ]
            return groups + self.primary.tree()
        workspace, relative, prefix = self.locate(path)
        return [{**row, "path": prefix + row["path"]} for row in workspace.tree(relative)]

    def read(self, path):
        workspace, relative, prefix = self.locate(path)
        source = workspace.read(relative)
        return {**source, "path": prefix + source["path"]}

    def symbols(self, path):
        workspace, relative, _ = self.locate(path)
        return workspace.symbols(relative)

    def files(self):
        yield from self.primary.files()
        for _, workspace in self.attached.values():
            yield from workspace.files()

    def find_files(self, query, limit=100):
        results = self.primary.find_files(query, limit)
        for source_id, (_, workspace) in self.attached.items():
            if len(results) >= limit:
                break
            results.extend(
                {**row, "path": source_prefix(source_id) + row["path"]}
                for row in workspace.find_files(query, limit - len(results))
            )
        return results

    def search(self, query, glob="*", limit=100):
        results = []
        truncated = False
        for prefix, workspace in [
            ("", self.primary),
            *[(source_prefix(key), workspace) for key, (_, workspace) in self.attached.items()],
        ]:
            result = workspace.search(query, glob, limit + 1)
            results.extend({**row, "path": prefix + row["path"]} for row in result["matches"])
            truncated |= result["truncated"] or len(results) > limit
        return {"matches": results[:limit], "truncated": truncated, "engine": "project-directories"}


class ProjectAnalysis(CSharpAnalysis):
    def __init__(self, workspace):
        super().__init__(workspace)
        self.analyzers = {"": CSharpAnalysis(workspace.primary)}
        self.analyzers.update(
            {
                source_prefix(key): CSharpAnalysis(child)
                for key, (_, child) in workspace.attached.items()
            }
        )

    def analyze(self, path, line):
        _, relative, prefix = self.workspace.locate(path.removeprefix("/workspace/"))
        result = self.analyzers[prefix].analyze(relative, line)

        # Roslyn 返回目录内的相对路径；统一补上附加目录前缀供后续读取和引用。
        def rebase(value):
            if isinstance(value, list):
                return [rebase(item) for item in value]
            if isinstance(value, dict):
                return {
                    key: prefix + item
                    if key == "path" and isinstance(item, str) and item
                    else rebase(item)
                    for key, item in value.items()
                }
            return value

        return rebase(result)

    def close(self):
        for analyzer in self.analyzers.values():
            analyzer.close()
