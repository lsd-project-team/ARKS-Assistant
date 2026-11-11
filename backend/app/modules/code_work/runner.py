"""固定 Windows 编译与 Simulation 自检，不接受模型生成的命令。"""

import json
import os
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from threading import Semaphore

from app.core.identifiers import now_iso
from app.infrastructure.storage.files import digest, safe_path
from app.modules.code_work.checks import prepare_harness, read_report, validation_version
from app.modules.code_work.files import PROJECT, atomic_bytes, code_manifest, save_json

_capacity = Semaphore(1)
MAX_LOG_BYTES = 8_000_000


def stop_process(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        # 只终止本次持有 Popen 句柄的进程树，不根据历史状态里的 PID 操作。
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=15,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        process.kill()
    process.wait(timeout=15)


def execute(arguments, cwd, log, stop, deadline):
    if stop.is_set():
        raise InterruptedError("验证已停止")
    with log.open("wb") as stream:
        process = subprocess.Popen(
            arguments,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            shell=False,
        )
        try:
            while process.poll() is None:
                if stop.is_set():
                    raise InterruptedError("验证已停止")
                if time.monotonic() >= deadline:
                    raise TimeoutError("编译或仿真超过本次验证时限")
                if log.stat().st_size > MAX_LOG_BYTES:
                    raise ValueError("验证日志超过 8 MB，已停止执行")
                time.sleep(0.15)
            return process.returncode
        finally:
            stop_process(process)


def log_text(path, limit=120_000):
    if not path.is_file():
        return ""
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = data.decode("gb18030", errors="replace")
    return ("（仅显示日志末尾）\n" + text[-limit:]) if len(text) > limit else text


def verify_workspace(service, thread_id, folder, state, stop):
    job = state["verification"]
    acquired = False
    root = None
    try:
        while not acquired:
            if stop.is_set():
                raise InterruptedError("验证已停止")
            acquired = _capacity.acquire(timeout=0.2)
        config = service.environment.load()
        compiler = service.environment.compiler()
        deadline = time.monotonic() + config.timeout_seconds
        work = folder / "source"
        for path, version in state["locked"].items():
            if digest(safe_path(work, path).read_bytes()) != version:
                raise ValueError("仿真入口或工程配置已变化，不能执行此副本")
        manifest = code_manifest(work)
        expected = {
            **state["baseline"],
            **{path: change["version"] for path, change in state["changes"].items()},
        }
        if manifest != expected:
            raise ValueError("副本存在未记录的外部修改，请恢复后重新验证")
        job["code_version"] = digest(str(sorted(manifest.items())).encode())
        job["validation_version"] = validation_version(state)
        job["requirements"] = [
            dict(item) for item in state.get("requirements", []) if item["enabled"]
        ]
        job["desktop_flow"] = state.get("desktop_flow", False)
        if shutil.disk_usage(folder).free < 1_000_000_000:
            raise ValueError("编译与仿真验证需要至少 1 GB 可用空间")
        build_root = getattr(service, "build_root", folder)
        if build_root != folder and folder.resolve().parent.parent != build_root.resolve():
            raise ValueError("候选构建目录不属于当前副本")
        # 合并候选复用所属副本的短构建根，避免.NET Framework资源文件超过MAX_PATH。
        root = build_root / "checks" / job["id"][:10]
        root.mkdir(parents=True)
        # 每个对话只保留本次与上次输出，避免反复编译无限积累大型 DLL。
        history = sorted(root.parent.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
        for previous in history[2:]:
            if (
                re.fullmatch(r"[a-f0-9]{10}", previous.name)
                and previous.is_dir()
                and previous.resolve().parent == root.parent.resolve()
            ):
                try:
                    shutil.rmtree(previous)
                except OSError:
                    job["cleanup_warning"] = "旧构建输出被占用，本次保留；不影响新版本验证"
        project = work / PROJECT
        output = root / "Simulation"

        def step(name, args, *, report=None, pattern=None):
            job["status"] = "testing" if report else "building"
            row = {"name": name, "status": "running", "exit_code": None, "log": ""}
            job["steps"].append(row)
            service.update_job(folder, state)
            log = root / f"step-{len(job['steps'])}.log"
            code = execute(args, project, log, stop, deadline)
            text = log_text(report or log)
            row.update(exit_code=code, log=text, status="passed" if code == 0 else "failed")
            if pattern:
                match = re.search(pattern, text)
                if not match or int(match[1]) < 1:
                    row["status"] = "failed"
                elif match:
                    row["checks"] = int(match[1])
            service.update_job(folder, state)
            if row["status"] != "passed":
                raise ValueError(name + "未通过，请查看日志")

        drivers = root / "drivers"
        step(
            "编译虚拟驱动检查",
            [
                compiler,
                str(project / "Infrastructure/Simulation/Tests/VirtualMotionDrivers.Tests.csproj"),
                "/t:Build",
                "/nologo",
                "/v:minimal",
                "/nodeReuse:false",
                "/p:UseSharedCompilation=false",
                "/p:Configuration=Debug",
                f"/p:OutputPath={drivers}/",
                f"/p:IntermediateOutputPath={root}/driver-obj/",
                f"/p:BaseIntermediateOutputPath={root}/driver-obj/",
            ],
        )
        step(
            "虚拟驱动检查",
            [str(drivers / "VirtualMotionDrivers.Tests.exe")],
            report=root / "step-2.log",
            pattern=r"PASS: (\d+) virtual driver checks",
        )

        # 新业务文件通过本次生成的固定导入项编译，不允许模型改写项目 targets。
        imports = ET.Element("Project", xmlns="http://schemas.microsoft.com/developer/msbuild/2003")
        target = ET.SubElement(
            imports,
            "Target",
            Name="IncludeNewWorkFiles",
            BeforeTargets="CoreCompile",
            Condition=f"'$(MSBuildProjectName)' == '{PROJECT}'",
        )
        group = ET.SubElement(target, "ItemGroup")
        project_document = ET.parse(project / f"{PROJECT}.csproj")
        included = {
            item.attrib.get("Include", "").replace("\\", "/").lower()
            for item in project_document.iter()
            if item.tag.rsplit("}", 1)[-1] == "Compile"
        }
        for path, change in state["changes"].items():
            if change["kind"] == "added" and path[len(PROJECT) + 1 :].lower() not in included:
                ET.SubElement(group, "Compile", Include=str(safe_path(work, path)))
        import_path = root / "new-files.targets"
        ET.ElementTree(imports).write(import_path, encoding="utf-8", xml_declaration=True)
        obj = root / "obj"
        obj.mkdir()
        for name in (
            f"{PROJECT}.csproj.nuget.g.props",
            f"{PROJECT}.csproj.nuget.g.targets",
            "project.assets.json",
            "project.nuget.cache",
        ):
            origin = project / "obj" / name
            if origin.is_file():
                (obj / name).write_bytes(origin.read_bytes())
        step(
            "编译修改后的原工程",
            [
                compiler,
                str(project / f"{PROJECT}.csproj"),
                "/t:Build",
                "/nologo",
                "/v:minimal",
                "/nodeReuse:false",
                "/p:UseSharedCompilation=false",
                "/p:Configuration=Simulation",
                "/p:Platform=AnyCPU",
                "/p:BuildProjectReferences=false",
                f"/p:OutputPath={output}/",
                f"/p:OutDir={output}/",
                f"/p:IntermediateOutputPath={obj}/Simulation/",
                f"/p:BaseIntermediateOutputPath={obj}/",
                f"/p:MSBuildProjectExtensionsPath={obj}/",
                f"/p:ReferencePath={project}/bin/Debug",
                f"/p:CustomBeforeMicrosoftCommonTargets={import_path}",
            ],
        )
        executable = output / f"{PROJECT}.exe"
        if not executable.is_file():
            raise ValueError("编译没有生成原工程程序，未执行仿真")
        step(
            "原工程 Simulation 自检",
            [str(executable), "--simulation-self-test"],
            report=output / "original-simulation-checks.txt",
            pattern=r"^PASS: (\d+) original-project integration checks\.",
        )
        if job["requirements"] or job["desktop_flow"]:
            arguments, harness = prepare_harness(root, output, state, compiler)
            step("编译需求与界面验证宿主", arguments)

            def checks(kind, name):
                report_path = output / f"code-work-{kind}.json"
                try:
                    step(name, [str(harness), kind], report=report_path)
                    report = read_report(report_path, kind, state)
                    job[kind + "_results"] = report["results"]
                    job["steps"][-1]["checks"] = sum(row["assertions"] for row in report["results"])
                except Exception as error:
                    job["steps"][-1]["status"] = "failed"
                    job["steps"][-1]["log"] += "\n" + str(error)
                    if report_path.is_file() and report_path.stat().st_size <= 2_000_000:
                        try:
                            failed_report = json.loads(report_path.read_text(encoding="utf-8-sig"))
                            if failed_report.get("kind") == kind and isinstance(
                                failed_report.get("results"), list
                            ):
                                job[kind + "_results"] = failed_report["results"]
                        except (ValueError, OSError):
                            pass
                    raise
                finally:
                    service.update_job(folder, state)

            if job["requirements"]:
                checks("requirements", "本次需求断言验证")
            if job["desktop_flow"]:
                checks("desktop", "原桌面按钮与生产流程验证")
        if code_manifest(work) != manifest:
            raise ValueError("验证期间代码发生变化，本次结果不能用于当前代码")
        job["status"] = "passed"
        job["executable_version"] = digest(executable.read_bytes())
        job["scope"] = (
            "虚拟驱动及示例载具业务流程；复用已有依赖 DLL。"
            "未验证真实视觉、测高、力控、标定和设备安全。"
        )
    except InterruptedError as error:
        job.update(status="cancelled", error=str(error))
        if job["steps"] and job["steps"][-1]["status"] == "running":
            job["steps"][-1]["status"] = "cancelled"
    except Exception as error:
        job.update(status="failed", error=str(error))
        if job["steps"] and job["steps"][-1]["status"] == "running":
            job["steps"][-1]["status"] = "failed"
    finally:
        if acquired:
            _capacity.release()
        job["finished_at"] = now_iso()
        report_folder = folder / "reports" / job["id"]
        report_folder.mkdir(parents=True, exist_ok=True)
        artifacts = []
        if root:
            for file in sorted((root / "Simulation").glob("code-work-*")):
                if (
                    file.is_file()
                    and (
                        re.fullmatch(r"code-work-ui-\d{2}\.png", file.name)
                        or file.name in {"code-work-requirements.json", "code-work-desktop.json"}
                    )
                    and file.stat().st_size <= 20_000_000
                ):
                    data = file.read_bytes()
                    atomic_bytes(report_folder / file.name, data)
                    artifacts.append(
                        {
                            "name": file.name,
                            "kind": "image" if file.suffix == ".png" else "report",
                            "version": digest(data),
                        }
                    )
        job["artifacts"] = artifacts
        save_json(report_folder / "verification.json", job)
        state.setdefault("verification_history", []).append(
            {
                key: job.get(key)
                for key in (
                    "id",
                    "run_id",
                    "revision",
                    "status",
                    "started_at",
                    "finished_at",
                    "attempt",
                )
            }
            | {"report_version": digest((report_folder / "verification.json").read_bytes())}
        )
        service.update_job(folder, state)
