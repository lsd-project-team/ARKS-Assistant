"""由管理员显式准备可信模板，不运行用户仓库中的 Dockerfile。"""

import subprocess
import tempfile
from pathlib import Path

from .cli import IMAGE_ID, ExecutionError, call, command, object_result, options, probe_executor


def prepare_executor(base_image, context="default", platform="linux"):
    if platform not in {"linux", "windows"} or not IMAGE_ID.fullmatch(str(base_image)):
        raise ExecutionError("准备镜像必须指定平台和固定 sha256 基础镜像")
    if platform == "windows":
        raise ExecutionError("Windows 独立监督身份尚未验收，当前禁止准备为可用执行镜像")
    executor = {"kind": "container", "context": context, "platform": platform, "image": base_image}
    info = object_result(executor, "info", "--format", "{{json .}}")
    if info.get("OSType") != platform:
        raise ExecutionError("基础镜像准备需要对应平台的执行节点")
    # 基础镜像必须由管理员提前准备；验证运行不会联网拉取依赖。
    base = object_result(executor, "image", "inspect", base_image)[0]
    if base.get("Os") != platform or (base.get("Config") or {}).get("Volumes"):
        raise ExecutionError("基础镜像平台不匹配或声明了额外挂载")
    # BuildKit 把裸 sha256:... 解释成仓库名；创建按内容命名的本地别名，仍固定原镜像。
    alias = f"arks-executor-base:{base['Id'].removeprefix('sha256:')}"

    call(executor, "image", "tag", base["Id"], alias)
    resources = Path(__file__).resolve().parents[4] / "resources" / "execution"
    dockerfile = resources / f"Dockerfile.{platform}"
    if not dockerfile.is_file():
        raise ExecutionError("可信执行镜像模板缺失")
    with tempfile.TemporaryDirectory(prefix="arks-image-") as temporary:
        identity_file = Path(temporary) / "image.id"
        result = subprocess.run(
            command(
                executor,
                "build",
                "--network=none",
                "--pull=false",
                "--build-arg",
                f"BASE_IMAGE={alias}",
                "--file",
                str(dockerfile),
                "--iidfile",
                str(identity_file),
                "--quiet",
                str(resources),
            ),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
            shell=False,
            **options(),
        )
        if result.returncode or not identity_file.is_file():
            raise ExecutionError("可信执行镜像准备失败，请检查基础镜像是否提供 Python 运行时")
        image_id = identity_file.read_text().strip()
    executor["image"] = image_id
    probe = probe_executor(executor)
    if not probe["available"]:
        raise ExecutionError(probe["error"])
    return {"executor": executor, **probe}
