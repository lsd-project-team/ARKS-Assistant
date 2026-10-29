"""只打包助手源码和已构建前端；白名单上下文不携带data、trunk或本机凭据。"""

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMAGE = re.compile(r"(?:[A-Za-z0-9._:/-]+@)?sha256:[a-f0-9]{64}\Z")
TREES = (
    "backend/app",
    "backend/migrations",
    "frontend/dist",
    "resources/knowledge",
)
FILES = (
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/alembic.ini",
    "backend/tools/SourceAnalysis/SourceAnalysis.csproj",
    "backend/tools/SourceAnalysis/Program.cs",
    "resources/deployment/Dockerfile.linux",
    "resources/deployment/healthcheck.py",
)
SKIP = {"__pycache__", ".pytest_cache", ".ruff_cache"}


def unlinked_path(path):
    # 显式FILES也要检查所有祖先；只检查叶文件会穿过父目录联接读取外部文件。
    path = Path(path).absolute()
    for component in [*reversed(path.parents), path]:
        info = component.lstat()
        if stat.S_ISLNK(info.st_mode) or (
            getattr(info, "st_file_attributes", 0)
            & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        ):
            raise ValueError("构建上下文路径或祖先目录包含链接")
    return info


def regular_file(path):
    info = unlinked_path(path)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("构建上下文只接受无链接的普通文件")


def source_files(root):
    root = Path(root).absolute()
    unlinked_path(root)
    result = [root / name for name in FILES]
    for path in result:
        regular_file(path)
    if not (root / "frontend/dist/index.html").is_file():
        raise ValueError("缺少已构建前端；请先在有权访问业务源码的环境完成标准npm run build")
    for name in TREES:
        tree = root / name
        if not stat.S_ISDIR(unlinked_path(tree).st_mode):
            raise ValueError("助手构建目录缺失或包含链接")
        for folder, directories, files in os.walk(tree, followlinks=False):
            directories[:] = [name for name in directories if name not in SKIP]
            for directory in directories:
                path = Path(folder) / directory
                unlinked_path(path)
            result.extend(Path(folder) / file for file in files if not file.endswith(".pyc"))
    for path in result:
        relative = path.relative_to(root)
        if any(
            part in {".git", ".ssh", ".venv", "data", "trunk"} or part.startswith(".env")
            for part in relative.parts
        ):
            raise ValueError("白名单目录中混入凭据或业务数据目录，未发送构建上下文")
        if path.name in {"settings.private.json", "bootstrap-admin.json"}:
            raise ValueError("白名单目录中混入本机私有配置，未发送构建上下文")
        regular_file(path)
    return sorted(set(result))


def prepare_context(root, destination):
    root = Path(root).absolute()
    manifest = {}
    for source in source_files(root):
        regular_file(source)
        relative = source.relative_to(root).as_posix()
        content = source.read_bytes()
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        manifest[relative] = hashlib.sha256(content).hexdigest()
    return manifest


def docker(*arguments, capture=True):
    return subprocess.run(
        ["docker", *arguments],
        check=True,
        shell=False,
        capture_output=capture,
        text=True,
        timeout=1800,
    )


def trusted_image(identity, role):
    if not IMAGE.fullmatch(identity):
        raise ValueError("基础镜像须是本机已存在的固定sha256身份，构建器不会拉取浮动标签")
    metadata = json.loads(docker("image", "inspect", identity).stdout)[0]
    if metadata["Os"] != "linux" or (metadata.get("Config") or {}).get("Volumes"):
        raise ValueError("基础镜像必须是无内置数据卷的Linux镜像")
    alias = f"arks-app-{role}:{metadata['Id'].removeprefix('sha256:')}"
    docker("image", "tag", metadata["Id"], alias)
    return alias, metadata


def build(python_image, dotnet_image, docker_image):
    images = {
        role: trusted_image(identity, role)
        for role, identity in (
            ("python", python_image),
            ("dotnet", dotnet_image),
            ("docker", docker_image),
        )
    }
    if len({metadata["Architecture"] for _, metadata in images.values()}) != 1:
        raise ValueError("三个基础镜像的CPU架构必须一致")
    with tempfile.TemporaryDirectory(prefix="arks-linux-build-") as temporary:
        context = Path(temporary)
        manifest = prepare_context(ROOT, context)
        identity_file = context / "image.id"
        arguments = [
            "build",
            "--pull=false",
            "--file",
            str(context / "resources/deployment/Dockerfile.linux"),
            "--iidfile",
            str(identity_file),
        ]
        for role, (alias, _) in images.items():
            arguments += ["--build-arg", f"{role.upper()}_IMAGE={alias}"]
        docker(*arguments, str(context), capture=False)
        identity = identity_file.read_text().strip()
    if not IMAGE.fullmatch(identity):
        raise ValueError("构建未返回固定镜像身份")
    output = ROOT / "output"
    output.mkdir(exist_ok=True)
    record = {
        "created_at": datetime.now(UTC).isoformat(),
        "image_id": identity,
        "base_images": {role: metadata["Id"] for role, (_, metadata) in images.items()},
        "context_sha256": hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        "files": manifest,
        "scope": (
            "助手、预构建UI及既有知识资源；不读取trunk、正式data或用户凭据。"
            "知识资源可能包含源码，镜像按内部制品管理。"
        ),
    }
    report = output / ("linux-image-" + datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f") + ".json")
    report.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"image_id": identity, "report": str(report)}, ensure_ascii=False))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for role in ("python", "dotnet", "docker"):
        parser.add_argument(f"--{role}-image", required=True)
    args = parser.parse_args()
    try:
        build(args.python_image, args.dotnet_image, args.docker_image)
    except (OSError, ValueError, subprocess.SubprocessError, KeyError) as error:
        parser.exit(
            1, f"Linux镜像未完成（{type(error).__name__}），核对基础镜像与白名单构建输入。\n"
        )


if __name__ == "__main__":
    main()
