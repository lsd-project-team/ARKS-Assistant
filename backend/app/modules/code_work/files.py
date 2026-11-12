"""副本路径、编码与原子保存；不向业务源码写入。"""

import codecs
import json
import os
import shutil
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from app.infrastructure.storage.files import digest, is_link, safe_path
from app.modules.source_analysis.workspace import IGNORED, MAX_FILE_BYTES, decode_source

EXCLUDED = IGNORED | {".svn", "Settings", "SimulationData", "tags", "branches"}
MAX_COPY_BYTES = 4_000_000_000
MAX_COPY_FILES = 30_000
SIMULATION_ENTRY = "Infrastructure/Simulation/OriginalSimulation.cs"
# 旧版固定项目名，只保留给既有副本和历史测试识别；运行路径按目录结构识别主工程。
PROJECT = "AKRS.ZX2200"
PROTECTED = {"Program.cs"}


def main_project(root):
    """按目录结构识别主工程，不再把某个项目名写死在代码里。"""
    base = Path(root)
    if not base.is_dir():
        raise ValueError("源码目录不存在")
    found = [
        directory.name
        for directory in base.iterdir()
        if directory.is_dir()
        and not is_link(directory)
        and (directory / SIMULATION_ENTRY).is_file()
        and (directory / f"{directory.name}.csproj").is_file()
    ]
    if not found:
        raise ValueError(
            "源码目录需包含主工程：工程目录下需有同名 .csproj 和 "
            "Infrastructure/Simulation/OriginalSimulation.cs"
        )
    if len(found) > 1:
        raise ValueError(
            "源码目录包含多个主工程，请每个项目只绑定一个：" + "、".join(sorted(found))
        )
    return found[0]


def atomic_bytes(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".cw-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def save_json(path, value):
    atomic_bytes(path, json.dumps(value, ensure_ascii=False, indent=2).encode("utf-8"))


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def editable_path(root, value, project=None):
    path = safe_path(root, value)
    relative = path.relative_to(Path(root).resolve())
    # 已创建副本可带固定主工程；恢复中的空树按目录结构识别。
    project = project or main_project(root)
    # 编辑范围限于原主工程的业务 C#；启动入口、仿真驱动和工程配置保持固定。
    if (
        not relative.parts
        or relative.parts[0] != project
        or path.suffix.lower() != ".cs"
        or len(relative.parts) < 2
        or relative.parts[1].lower() in {"properties", "infrastructure"}
        and (
            relative.parts[1].lower() == "properties"
            or "simulation" in [p.lower() for p in relative.parts]
        )
        or relative.parts[1].lower() in {name.lower() for name in PROTECTED}
    ):
        raise ValueError("只能修改主工程的业务 C#；启动入口、仿真驱动和工程配置保持固定")
    return path


def encode_text(text, original=b""):
    # 工具使用统一换行匹配，落盘保留原 BOM、中文编码及换行。
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    previous, encoding = decode_source(original) if original else ("", "UTF-8")
    if "\r\n" in previous:
        text = text.replace("\n", "\r\n")
    if original.startswith(codecs.BOM_UTF16_BE):
        data = codecs.BOM_UTF16_BE + text.encode("utf-16-be")
    elif original.startswith(codecs.BOM_UTF16_LE):
        data = codecs.BOM_UTF16_LE + text.encode("utf-16-le")
    elif encoding == "GB18030":
        data = text.encode("gb18030")
    else:
        data = (codecs.BOM_UTF8 if original.startswith(codecs.BOM_UTF8) else b"") + text.encode(
            "utf-8"
        )
    if len(data) > MAX_FILE_BYTES:
        raise ValueError("单个代码文件不能超过 2 MB")
    return data


def copy_tree(source, destination, budget):
    """拒绝联接与硬链接；复制普通文件，不复用可写文件链接。"""
    source = Path(source)
    if not source.is_dir() or is_link(source):
        raise ValueError("副本来源目录不存在或是链接")
    for folder, directories, names in os.walk(source, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED)
        for name in [*directories, *names]:
            if name in EXCLUDED:
                continue
            entry = Path(folder) / name
            if is_link(entry) or (entry.is_file() and entry.stat().st_nlink > 1):
                raise ValueError(f"副本来源含链接：{entry.relative_to(source)}")
        for name in sorted(names):
            if name in EXCLUDED:
                continue
            entry = Path(folder) / name
            if not entry.is_file():
                raise ValueError("副本来源只允许普通文件")
            budget[0] += entry.stat().st_size
            budget[1] += 1
            if budget[0] > MAX_COPY_BYTES or budget[1] > MAX_COPY_FILES:
                raise ValueError("副本超过 4 GB 或 30000 个文件的限制")
            target = destination / entry.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(entry, target)


def code_manifest(root):
    result = {}
    for folder, directories, names in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in EXCLUDED)
        for name in sorted(names):
            if not name.lower().endswith(".cs"):
                continue
            relative = (Path(folder) / name).relative_to(root).as_posix()
            target = safe_path(root, relative)
            result[relative] = digest(target.read_bytes())
    return result


def copy_project_outputs(source, destination, budget, project=None):
    """保留项目引用的离线输出路径；只复制依赖程序自身，不复制重复的依赖树。"""
    source = Path(source).resolve()
    project = project or main_project(source)
    namespace = {"m": "http://schemas.microsoft.com/developer/msbuild/2003"}
    main = source / project
    document = ET.parse(main / f"{project}.csproj")
    for item in document.findall(".//m:ProjectReference[@Include]", namespace):
        reference = (main / item.attrib["Include"].replace("\\", "/")).resolve()
        if not reference.is_relative_to(source):
            raise ValueError("项目引用超出仿真源码目录")
        if not reference.is_file():
            continue  # 保留原工程的缺失引用，由构建日志报告。
        properties = ET.parse(reference)
        assembly = properties.findtext(".//m:AssemblyName", reference.stem, namespace)
        kind = properties.findtext(".//m:OutputType", "Library", namespace)
        name = assembly + (".dll" if kind.lower() == "library" else ".exe")
        if Path(name).name != name or "\\" in name:
            raise ValueError("依赖程序集名称不能包含路径")
        relative = reference.parent.relative_to(source) / "bin/Debug" / name
        origin = source / relative
        if not origin.is_file():
            origin = main / "bin/Debug" / name
        if not origin.is_file():
            continue
        if is_link(origin) or origin.stat().st_nlink > 1:
            raise ValueError("依赖程序集不能是链接")
        budget[0] += origin.stat().st_size
        budget[1] += 1
        if budget[0] > MAX_COPY_BYTES or budget[1] > MAX_COPY_FILES:
            raise ValueError("副本超过 4 GB 或 30000 个文件的限制")
        atomic_bytes(destination / relative, origin.read_bytes())


def snapshot(source, destination):
    budget = [0, 0]
    copy_tree(source, destination, budget)
    project = main_project(source)
    main = Path(source) / project
    copy_tree(main / "bin/Debug", destination / project / "bin/Debug", budget)
    copy_project_outputs(source, destination, budget, project)
    for name in (
        f"{project}.csproj.nuget.g.props",
        f"{project}.csproj.nuget.g.targets",
        "project.assets.json",
        "project.nuget.cache",
    ):
        origin = main / "obj" / name
        if origin.is_file():
            atomic_bytes(destination / project / "obj" / name, origin.read_bytes())


def input_manifest(root):
    return {
        file.relative_to(root).as_posix(): digest(file.read_bytes())
        for file in sorted(Path(root).rglob("*"))
        if file.is_file()
    }
