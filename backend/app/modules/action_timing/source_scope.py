"""在已授权源码根内读取 ZX2200 与依赖工程，不加载程序集或执行 MSBuild。"""

import fnmatch
import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SourceScope:
    documents: list
    primary_project: str | None
    projects: list
    references: list
    files: list
    versions: list

    @property
    def revision(self):
        return hashlib.sha256(
            json.dumps(self.versions, ensure_ascii=False, sort_keys=True).encode()
        ).hexdigest()


def _elements(root, name):
    return [node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == name]


def _child_text(root, name):
    return next((node.text or "" for node in _elements(root, name)), "")


def _relative_target(project, value):
    value = value.replace("\\", "/")
    if not value or "$" in value or ":" in value or value.startswith("/"):
        return None
    return (project.parent / value).resolve()


def load_scope(workspace):
    files = sorted(workspace.files())
    by_path = {str(path.resolve()).casefold(): workspace.relative(path) for path in files}
    project_paths = [path for path in files if path.suffix.lower() == ".csproj"]
    manifests = {}
    for path in project_paths:
        source = workspace.read(workspace.relative(path))
        try:
            root = ET.fromstring(source["content"])
        except ET.ParseError as error:
            raise ValueError(f"工程文件无法解析：{source['path']}") from error
        manifests[str(path.resolve()).casefold()] = (path, source, root)
    candidates = [path for path in project_paths if path.name == "AKRS.ZX2200.csproj"]
    preferred = [
        "AKRS.ZX2200.csproj",
        "AKRS.ZX2200/AKRS.ZX2200.csproj",
        "trunk/AKRS.ZX2200/AKRS.ZX2200.csproj",
    ]
    selected = next(
        (path for name in preferred for path in candidates if workspace.relative(path) == name),
        None,
    )
    if selected is None and candidates:
        primary = [
            path
            for path in candidates
            if not workspace.relative(path).startswith("@sources/")
            and "output" not in workspace.relative(path).split("/")
        ]
        unique = primary or candidates
        if len(unique) != 1:
            raise ValueError("关联了多份ZX2200源码，请选择单一源码版本所属项目，避免混算")
        selected = unique[0]

    # 附加源码根的物理目录不必相邻；只在已授权目录里按唯一程序集身份定位依赖。
    assemblies = {}
    for identity, (_, _, root) in manifests.items():
        assembly = _child_text(root, "AssemblyName")
        if assembly:
            assemblies.setdefault(assembly.casefold(), []).append(identity)

    documents, projects, references, inventory, versions = [], [], [], [], []
    loaded, included = set(), set()

    def read_document(path, role, assembly):
        relative = by_path[str(path.resolve()).casefold()]
        if relative in included:
            return
        included.add(relative)
        generated = path.name.lower().endswith((".designer.cs", ".g.cs"))
        inventory.append(
            {
                "path": relative,
                "role": role,
                "project": assembly,
                "status": "generated" if generated else "indexed",
            }
        )
        if generated:
            return
        source = workspace.read(relative)
        versions.append((relative, source["version"]))
        documents.append({**source, "project": assembly, "role": role})

    def visit(identity, role):
        if identity in loaded:
            return
        loaded.add(identity)
        path, source, root = manifests[identity]
        versions.append((source["path"], source["version"]))
        assembly = _child_text(root, "AssemblyName") or path.stem
        compile_items = [
            node.get("Include", "").replace("\\", "/")
            for node in _elements(root, "Compile")
            if node.get("Include")
        ]
        projects.append({"path": source["path"], "assembly": assembly, "role": role})
        exact_targets = {
            target
            for item in compile_items
            if "*" not in item and (target := _relative_target(path, item)) is not None
        }
        patterns = [item for item in compile_items if "*" in item]
        for file in files:
            if file.suffix.lower() != ".cs":
                continue
            if compile_items:
                exact = file.resolve() in exact_targets
                local = (
                    file.relative_to(path.parent).as_posix()
                    if file.is_relative_to(path.parent)
                    else None
                )
                wildcard = local is not None and any(
                    fnmatch.fnmatchcase(local, item) for item in patterns
                )
                if not exact and not wildcard:
                    continue
            elif not file.is_relative_to(path.parent):
                continue
            read_document(file, role, assembly)
        for reference in _elements(root, "ProjectReference"):
            value = reference.get("Include", "")
            target = _relative_target(path, value)
            key = str(target).casefold() if target else ""
            if key not in manifests:
                name = Path(value.replace("\\", "/")).stem.casefold()
                matches = assemblies.get(name, [])
                key = matches[0] if len(matches) == 1 else ""
            references.append(
                {
                    "from": source["path"],
                    "name": Path(value.replace("\\", "/")).stem,
                    "kind": "project",
                    "status": "source" if key in manifests else "missing",
                    "path": manifests[key][1]["path"] if key in manifests else value,
                }
            )
            if key in manifests:
                visit(key, "dependency")
        for reference in _elements(root, "Reference"):
            hint = _child_text(reference, "HintPath")
            target = _relative_target(path, hint)
            key = str(target).casefold() if target else ""
            references.append(
                {
                    "from": source["path"],
                    "name": reference.get("Include", "").split(",")[0],
                    "kind": "assembly",
                    "status": "binary" if key in by_path else "external",
                    "path": by_path.get(key, hint),
                }
            )

    if selected is not None:
        visit(str(selected.resolve()).casefold(), "business")
    else:
        for path in files:
            if path.suffix.lower() == ".cs" and "output" not in workspace.relative(path).split("/"):
                read_document(path, "business", "standalone")
    for path in files:
        if path.suffix.lower() != ".cs" or by_path[str(path.resolve()).casefold()] in included:
            continue
        owner = next(
            (
                (identity, manifest)
                for identity, manifest in manifests.items()
                if path.is_relative_to(manifest[0].parent)
            ),
            None,
        )
        identity, manifest = owner if owner else ("", None)
        inventory.append(
            {
                "path": workspace.relative(path),
                "role": "excluded",
                "project": _child_text(manifest[2], "AssemblyName") if manifest else "",
                "status": "not_compiled" if identity in loaded else "unreferenced_project",
            }
        )
    if (
        len(documents) > 4000
        or sum(len(item["content"].encode()) for item in documents) > 80_000_000
    ):
        raise ValueError("源码范围超过分析上限，请选择 ZX2200 及关联依赖目录")
    return SourceScope(
        documents,
        workspace.relative(selected) if selected else None,
        projects,
        references,
        inventory,
        versions,
    )
