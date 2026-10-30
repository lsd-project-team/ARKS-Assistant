"""只接管空临时目录；输出协议不携带账号、Cookie或资料正文。"""

import hashlib
import json
import os
import re
import uuid
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[3]
MARKER = ".arks-linux-runtime-smoke"


class SmokeFailure(RuntimeError):
    pass


def require(condition, code):
    if not condition:
        raise SmokeFailure(code)


def prepare_root(value):
    require(bool(value), "temporary_root_required")
    path = Path(value)
    require(path.is_absolute(), "temporary_root_not_absolute")
    require(not path.is_symlink(), "temporary_root_is_link")
    root = path.resolve()
    require(path.absolute() == root, "temporary_root_has_link_or_parent")
    require(
        not root.is_relative_to(PROJECT) and not PROJECT.is_relative_to(root),
        "temporary_root_overlaps_application",
    )
    require(
        not root.exists() or (root.is_dir() and not any(root.iterdir())), "temporary_root_not_empty"
    )
    root.mkdir(parents=True, exist_ok=True)
    token = uuid.uuid4().hex
    (root / MARKER).write_text(token, encoding="ascii")
    return root, token


def owns(root, token):
    require(root.is_dir() and not root.is_symlink(), "temporary_root_identity_changed")
    require((root / MARKER).read_text(encoding="ascii") == token, "temporary_root_identity_changed")


def environment(root, data, source, origin, host):
    # 不继承正式目录、供应商密钥、MCP、代理或调用者PYTHONPATH。
    names = (
        "PATH",
        "SystemRoot",
        "WINDIR",
        "LANG",
        "LC_ALL",
        "LD_LIBRARY_PATH",
        "DOTNET_ROOT",
        "ARKS_DOTNET_PATH",
        "ARKS_ROSLYN_HELPER",
    )
    result = {name: os.environ[name] for name in names if name in os.environ}
    home = root / "runtime-home"
    home.mkdir(exist_ok=True)
    temporary = root / "tmp"
    temporary.mkdir(exist_ok=True)
    result.update(
        {
            "PYTHONPATH": str(PROJECT / "backend"),
            "PYTHONUNBUFFERED": "1",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONUTF8": "1",
            "TRUNK_AGENT_DATA_DIR": str(data),
            "TRUNK_AGENT_WORKSPACE": str(source),
            "ARKS_ALLOWED_ORIGINS": origin,
            "ARKS_TRUSTED_HOSTS": f"{host},localhost,127.0.0.1",
            "HOME": str(home),
            "DOTNET_CLI_HOME": str(home),
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
            "DOTNET_CLI_TELEMETRY_OPTOUT": "1",
            "DOTNET_NOLOGO": "1",
            "DOTNET_SKIP_FIRST_TIME_EXPERIENCE": "1",
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
            "NUMEXPR_NUM_THREADS": "1",
            "TOKENIZERS_PARALLELISM": "false",
        }
    )
    return result


def tree_hash(root):
    result = hashlib.sha256()
    for file in sorted(root.rglob("*")):
        require(not file.is_symlink(), "fixture_source_link")
        if file.is_file():
            result.update(file.relative_to(root).as_posix().encode())
            result.update(b"\0" + hashlib.sha256(file.read_bytes()).digest())
    return result.hexdigest()


def write_report(root, token, checks, hashes, error=""):
    owns(root, token)
    # 所有名称由脚本提供，禁止用异常正文或HTTP正文填入错误与检查项。
    names = [*checks, *hashes, *([error] if error else [])]
    require(all(re.fullmatch(r"[a-z0-9_]+", name) for name in names), "unsafe_report_name")
    require(all(type(value) is bool for value in checks.values()), "unsafe_report_value")
    require(
        all(re.fullmatch(r"[a-f0-9]{64}", value) for value in hashes.values()), "unsafe_report_hash"
    )
    result = {"ok": not error and all(checks.values()), "checks": checks, "hashes": hashes}
    if error:
        result["error"] = error
    (root / "report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
