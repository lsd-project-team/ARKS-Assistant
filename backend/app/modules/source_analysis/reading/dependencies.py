"""依赖只代表已声明范围；未知符号和旧成果使用保守的项目快照约束。"""

import json
from collections import defaultdict


class DependencyGraph(defaultdict):
    def __init__(self):
        super().__init__(set)
        self.snapshot_guards = defaultdict(set)


def metadata(document):
    value = json.loads(document.dependencies_json)
    if isinstance(value, list):
        # 旧记录没有分析时的依赖快照，不能借用刷新后的 job 版本冒充新成果。
        return {"declared": value, "schema_version": 0}
    return value if isinstance(value, dict) else {"declared": [], "schema_version": 0}


def resolve(declared, paths, files):
    modules, resolved, unresolved = defaultdict(set), set(), set()
    for path, file in files.items():
        modules[file.module].add(path)
    for dependency in [*paths, *declared]:
        normalized = dependency.strip().replace("\\", "/")
        while normalized.startswith("./"):
            normalized = normalized[2:]
        if normalized in files:
            resolved.add(normalized)
        elif normalized in modules:
            resolved.update(modules[normalized])
            # 模块成员还可能新增或删除；不能把当前展开的文件列表视为永久完备依赖。
            unresolved.add(dependency)
        else:
            unresolved.add(dependency)
    return sorted(resolved), sorted(unresolved)


def analysis_metadata(analysis, files, snapshot_version):
    paths, unresolved = resolve(analysis.dependencies, analysis.dependency_paths, files)
    return {
        "schema_version": 1,
        "declared": analysis.dependencies,
        "dependency_paths": analysis.dependency_paths,
        "resolved_paths": paths,
        "unresolved": unresolved,
        # 模型给出的文件路径也不是静态完备证明，只能称为已声明依赖。
        "coverage": "declared_only" if paths and not unresolved else "unknown",
        "snapshot_version": snapshot_version,
    }


def public_metadata(document):
    value = metadata(document)
    return {
        "dependencies": value.get("declared", []),
        "dependency_paths": value.get("resolved_paths", []),
        "unresolved_dependencies": value.get("unresolved", value.get("declared", [])),
        "dependency_coverage": value.get("coverage", "unknown"),
    }


def dependency_graph(files, documents):
    graph = DependencyGraph()
    for document in documents:
        value = metadata(document)
        paths, unresolved = resolve(
            value.get("declared", []), value.get("dependency_paths", []), files
        )
        graph[document.path].update(paths)
        if value.get("schema_version") != 1:
            graph.snapshot_guards[document.path].add(None)
        elif unresolved or not paths:
            graph.snapshot_guards[document.path].add(value.get("snapshot_version"))
    return graph


def guarded_snapshot_matches(graph, paths, current_snapshot):
    return all(
        snapshot is not None and snapshot == current_snapshot
        for path in paths
        for snapshot in graph.snapshot_guards.get(path, set())
    )
