"""受边界保护的 Roslyn 服务；项目配置静态读取，不运行用户项目的构建任务。"""

import json
import os
import queue
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from langchain_core.tools import tool

from app.config import PROJECT_ROOT, dump_json
from app.workspace import content_version

DOTNET = PROJECT_ROOT / ".tools/dotnet/dotnet.exe"
HELPER = PROJECT_ROOT / "backend/tools/SourceAnalysis/bin/Release/net8.0/SourceAnalysis.dll"


class CSharpAnalysis:
    def __init__(self, workspace):
        self.workspace, self.lock, self.process = workspace, threading.RLock(), None

    def close(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()
                self.process.wait(timeout=10)
            self.process = None

    def project(self, target):
        for parent in [target.parent, *target.parents]:
            if not parent.is_relative_to(self.workspace.root):
                break
            found = sorted(parent.glob("*.csproj"))
            if found:
                return found[0]
        return None

    def manifest(self, project, seen, notes):
        identity = self.workspace.relative(project) if project else "loose-source"
        if identity in seen:
            raise ValueError("项目引用循环，不能完整建立语义关系")
        seen.add(identity)
        folder = project.parent if project else self.workspace.root
        root = ET.parse(project).getroot() if project else None
        elements = list(root.iter()) if root is not None else []

        def tag(node):
            return node.tag.split("}")[-1]

        explicit = [
            node.attrib["Include"]
            for node in elements
            if tag(node) == "Compile" and "Include" in node.attrib
        ]
        sdk = root is not None and bool(root.attrib.get("Sdk"))
        if any(node.get("Condition") for node in elements):
            notes.append(f"{identity}: MSBuild 条件未执行，使用静态配置；条件依赖可能未知")
        if any(tag(node) in {"Import", "PackageReference"} for node in elements):
            notes.append(f"{identity}: 不执行导入和包还原，缺失依赖将标记为未知")
        removes = [
            node.get("Remove", "").replace("\\", "/") for node in elements if tag(node) == "Compile"
        ]
        candidates = list(folder.rglob("*.cs")) if sdk or not project else []
        for pattern in explicit:
            if "$" in pattern:
                notes.append(f"{identity}: 无法解析 Compile 属性 {pattern}")
                continue
            candidates.extend(folder.glob(pattern.replace("\\", "/")))
        files = []
        for target in sorted(set(candidates)):
            if not target.resolve().is_relative_to(self.workspace.root):
                notes.append(f"{identity}: 源码路径超出工作区，已排除")
                continue
            relative = self.workspace.relative(target)
            try:
                if any(target.match(pattern) for pattern in removes if pattern):
                    continue
                source = self.workspace.read(relative)
                files.append({key: source[key] for key in ("path", "version", "content")})
            except (ValueError, OSError):
                continue
        if len(files) > 1500 or sum(len(file["content"]) for file in files) > 30_000_000:
            raise ValueError("项目超过语义索引范围，请缩小工作区")
        references, dependency_ids, dependencies = [], [], []
        for node in elements:
            if tag(node) not in {"ProjectReference", "HintPath"}:
                continue
            value = node.get("Include") if tag(node) == "ProjectReference" else node.text
            if not value:
                continue
            target = (folder / value.replace("\\", "/")).resolve()
            if not target.is_relative_to(self.workspace.root) or not target.is_file():
                notes.append(f"{identity}: 依赖缺失或超出工作区：{value}")
                continue
            if tag(node) == "HintPath":
                references.append(str(target))
            else:
                nested = self.manifest(target, seen, notes)
                dependencies.extend(nested)
                dependency_ids.append(nested[-1]["id"])
        defines = sorted(
            {
                part
                for node in elements
                if tag(node) == "DefineConstants"
                for part in (node.text or "").split(";")
                if part and "$" not in part
            }
        )
        record = dict(
            id=identity,
            files=files,
            references=references,
            project_references=dependency_ids,
            defines=defines,
        )
        # 依赖文件与预处理符号也参与版本，防止调用关系缓存沿用旧绑定。
        fingerprint = {
            **record,
            "dependency_versions": [item["version"] for item in dependencies],
            "reference_versions": [content_version(Path(path).read_bytes()) for path in references],
        }
        record["version"] = content_version(dump_json(fingerprint).encode())
        seen.remove(identity)
        return [*dependencies, record]

    def analyze(self, path, line):
        path = path.removeprefix("/workspace/")
        started = time.perf_counter()
        target = self.workspace.resolve(path)
        source = self.workspace.read(path)
        if target.suffix.lower() != ".cs" or not 1 <= line <= source["line_count"]:
            raise ValueError("语义工具需要 C# 文件和有效行号")
        if not DOTNET.is_file() or not HELPER.is_file():
            return {"analysis": "unavailable", "reason": "请运行 Setup.ps1 准备 Roslyn 分析器"}
        notes = []
        with self.lock:
            projects = self.manifest(self.project(target), set(), notes)
            projects = list({item["id"]: item for item in projects}.values())
            if (
                len(projects) > 24
                or sum(len(item["content"]) for project in projects for item in project["files"])
                > 50_000_000
            ):
                return {"analysis": "partial", "reason": "项目引用超过有界索引范围"}
            if not self.process or self.process.poll() is not None:
                self.process = subprocess.Popen(
                    [str(DOTNET), str(HELPER)],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    encoding="utf-8",
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
            payload = dict(
                projects=projects, project=projects[-1]["id"], path=source["path"], line=line
            )
            self.process.stdin.write(dump_json(payload) + "\n")
            self.process.stdin.flush()
            replies = queue.Queue()
            worker = self.process
            threading.Thread(
                target=lambda: replies.put(worker.stdout.readline()), daemon=True
            ).start()
            try:
                result = json.loads(replies.get(timeout=90))
            except queue.Empty as error:
                worker.terminate()
                worker.wait(timeout=10)
                raise ValueError("语义分析超过 90 秒处理期限，当前关系仍为未知") from error
            if "error" in result:
                result = {"analysis": "unknown", "reason": result["error"]}
        result.update(
            version=source["version"],
            configuration_notes=notes,
            duration_ms=round((time.perf_counter() - started) * 1000, 1),
        )
        if notes:
            result["completeness"] = (
                "partial: static project configuration; see configuration_notes"
            )
        return result

    def tools(self):
        @tool
        async def csharp_relations(path: str, line: int) -> str:
            """Resolve C# overloads, interface candidates, callers and callees with Roslyn.

            Missing dependencies remain unknown. Static binding is not proof a branch ran.
            Read target declarations with read_source before citing their implementation.
            """
            import asyncio

            return dump_json(await asyncio.to_thread(self.analyze, path, line))

        from app.agent_tools import safe_source_tools

        return safe_source_tools([csharp_relations])
