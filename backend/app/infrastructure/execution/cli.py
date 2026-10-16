"""Docker CLI 的固定参数边界；不接受 shell 或任意 Docker flags。"""

import json
import os
import re
import shutil
import subprocess

IMAGE_ID = re.compile(r"(?:[A-Za-z0-9._:/-]+@)?sha256:[a-f0-9]{64}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
CONTEXT = re.compile(r"[A-Za-z0-9_.-]{1,128}\Z")
LABEL = "io.arks.executor"


class ExecutionError(RuntimeError):
    pass


def command(executor, *args):
    context = executor.get("context", "default")
    if not isinstance(context, str) or not CONTEXT.fullmatch(context):
        raise ExecutionError("Docker context 名称不合法")
    executable = shutil.which("docker")
    if not executable:
        raise ExecutionError("未找到 Docker CLI，请准备隔离执行节点")
    return [executable, "--context", context, *args]


def options():
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}


def call(executor, *args, timeout=30, stdin=None):
    try:
        result = subprocess.run(
            command(executor, *args),
            input=stdin,
            capture_output=True,
            timeout=timeout,
            shell=False,
            **options(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExecutionError("隔离节点连接失败或超时") from exc
    if result.returncode:
        # Docker 连接错误可能包含证书路径或远端主机，日志只保留通用分类。
        raise ExecutionError(f"Docker {args[0]} 失败，请检查节点、镜像与平台配置")
    return result.stdout


def object_result(executor, *args):
    try:
        return json.loads(call(executor, *args))
    except (ValueError, TypeError) as exc:
        raise ExecutionError("隔离节点返回了无效响应") from exc


def validate_executor(executor):
    if executor.get("kind") != "container":
        raise ExecutionError("此入口只接受容器沙箱，不会回退宿主执行")
    if executor.get("platform") not in {"linux", "windows"}:
        raise ExecutionError("执行平台必须为 linux 或 windows")
    if not IMAGE_ID.fullmatch(str(executor.get("image", ""))):
        raise ExecutionError("执行镜像必须固定为 sha256 digest，不能使用浮动标签")


def probe_executor(executor):
    """只探测已有镜像；不拉取、不构建、不执行项目。"""
    result = {"available": False, "platform": executor.get("platform"), "image_id": ""}
    try:
        validate_executor(executor)
        info = object_result(executor, "info", "--format", "{{json .}}")
        if info.get("OSType") != executor["platform"]:
            raise ExecutionError("执行节点系统与配置平台不匹配，需要对应的独立执行节点")
        if executor["platform"] == "windows":
            raise ExecutionError("Windows 尚缺独立监督身份与受保护证明，当前禁止执行")
        images = object_result(executor, "image", "inspect", executor["image"])
        image = images[0]
        config = image.get("Config") or {}
        labels = config.get("Labels") or {}
        if image.get("Os") != executor["platform"]:
            raise ExecutionError("镜像系统与配置平台不匹配")
        if (
            labels.get(f"{LABEL}.version") != "2"
            or labels.get(f"{LABEL}.platform") != executor["platform"]
        ):
            raise ExecutionError("镜像尚未使用本项目可信执行模板准备")
        expected = ["/usr/local/bin/python", "-I", "/opt/arks/supervisor.py"]
        if executor["platform"] == "windows":
            expected = ["python", "C:\\arks\\supervisor.py"]
        if (
            config.get("Entrypoint") != expected
            or config.get("Volumes")
            or config.get("User") != "0:0"
        ):
            raise ExecutionError("镜像入口或内置挂载不符合可信执行模板")
        result.update(available=True, image_id=image["Id"], error="")
    except (ExecutionError, IndexError, KeyError, TypeError) as exc:
        result["error"] = str(exc) if isinstance(exc, ExecutionError) else "镜像配置不完整"
    return result
