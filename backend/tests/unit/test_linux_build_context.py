"""构建上下文使用真实临时文件，防止把本机业务数据或凭据带入发布镜像。"""

import os
import subprocess
import sys

import pytest

from app.core.config import PROJECT_ROOT

sys.path.insert(0, str(PROJECT_ROOT))
from scripts.deployment.build_linux import FILES, TREES, prepare_context  # noqa: E402


@pytest.fixture
def checkout(tmp_path):
    root = tmp_path / "checkout"
    for name in FILES:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"trusted application file")
    for name in TREES:
        path = root / name
        path.mkdir(parents=True, exist_ok=True)
        (path / "fixture.txt").write_bytes(b"application artifact")
    (root / "frontend/dist/index.html").write_text("<html>fixture</html>", encoding="utf-8")
    return root


def test_context_includes_expected_artifacts_but_excludes_formal_state(checkout, tmp_path):
    for name in (
        "data/settings.private.json",
        "trunk/Business.cs",
        ".ssh/id_ed25519",
        ".env",
        "backend/.venv/secret",
    ):
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"must not leave checkout")
    cache = checkout / "backend/app/__pycache__"
    cache.mkdir()
    (cache / "private.pyc").write_bytes(b"not application source")
    context = tmp_path / "context"
    manifest = prepare_context(checkout, context)
    assert "backend/app/fixture.txt" in manifest
    assert "frontend/dist/index.html" in manifest
    assert "backend/uv.lock" in manifest
    assert not (context / "data").exists() and not (context / "trunk").exists()
    assert not (context / ".ssh").exists() and not (context / "backend/.venv").exists()
    assert not (context / "backend/app/__pycache__").exists()
    assert len(manifest["backend/uv.lock"]) == 64


def test_missing_prebuilt_ui_is_error_without_looking_at_business_source(checkout, tmp_path):
    (checkout / "frontend/dist/index.html").unlink()
    with pytest.raises(ValueError, match="已构建前端"):
        prepare_context(checkout, tmp_path / "context")
    assert not (tmp_path / "context").exists()


@pytest.mark.parametrize(
    "name",
    ["backend/app/.env", "resources/knowledge/settings.private.json", "frontend/dist/.ssh/key"],
)
def test_private_config_inside_artifacts_aborts_context(checkout, tmp_path, name):
    path = checkout / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"private")
    with pytest.raises(ValueError, match="私有配置|凭据或业务数据"):
        prepare_context(checkout, tmp_path / "context")
    assert not (tmp_path / "context").exists()


def test_hardlinked_input_cannot_carry_external_mutable_bytes(checkout, tmp_path):
    private = tmp_path / "external"
    private.write_bytes(b"private")
    link = checkout / "backend/app/linked.py"
    os.link(private, link)
    with pytest.raises(ValueError, match="无链接"):
        prepare_context(checkout, tmp_path / "context")
    assert private.read_bytes() == b"private"


def directory_link(link, target):
    if os.name == "nt":
        # 路径经独立环境变量传入固定脚本，不把临时目录名拼进宿主命令。
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                "New-Item -ItemType Junction -Path $env:ARKS_CONTEXT_LINK "
                "-Target $env:ARKS_CONTEXT_TARGET | Out-Null",
            ],
            check=True,
            capture_output=True,
            timeout=20,
            env={**os.environ, "ARKS_CONTEXT_LINK": str(link), "ARKS_CONTEXT_TARGET": str(target)},
        )
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.mark.parametrize(
    "ancestor",
    ["backend/tools/SourceAnalysis", "backend/tools", "backend", "frontend", "resources", ""],
)
def test_linked_ancestors_of_explicit_files_and_trees_are_rejected_before_copy(
    checkout, tmp_path, ancestor
):
    folder = checkout / ancestor
    outside = tmp_path / "outside-artifacts"
    # 只移动当前测试建立的目录，拒绝对计算出的越界目标执行目录移动。
    assert folder.resolve().is_relative_to(tmp_path.resolve())
    assert outside.resolve().is_relative_to(tmp_path.resolve())
    folder.rename(outside)
    marker = next(path for path in outside.rglob("*") if path.is_file())
    marker.write_bytes(b"external file must never enter build context")
    directory_link(folder, outside)
    context = tmp_path / "context"
    try:
        with pytest.raises(ValueError, match="链接"):
            prepare_context(checkout, context)
        assert not context.exists()
        assert marker.read_bytes() == b"external file must never enter build context"
    finally:
        folder.rmdir() if os.name == "nt" else folder.unlink()
