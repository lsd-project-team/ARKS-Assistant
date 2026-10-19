"""Linux真实运行验收入口；所有数据都归属于显式空临时根。"""

import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

from .http_checks import (
    bootstrap_password,
    csrf_checks,
    frontend,
    login,
    persistent,
    populate,
    request,
)
from .persistence import database_integrity, online_backup, restore
from .safety import (
    PROJECT,
    SmokeFailure,
    environment,
    prepare_root,
    require,
    tree_hash,
    write_report,
)
from .server import reject_duplicate, running

sys.path.insert(0, str(PROJECT / "backend"))
ORIGIN = "https://arks-smoke.example.invalid"
SOURCE = """interface IWorker { void Run(int value); }
class Worker : IWorker {
 public void Run(int value) {}
 public void Run(string value) {}
 public void Start(IWorker worker) {
  if (worker == null) return;
  worker.Run(1);
  Run("text");
 }
}
class Entry { static void Main() { new Worker().Run(3); } }
"""


def fixture(root):
    source = root / "source"
    source.mkdir()
    (source / "Sample.csproj").write_text(
        '<Project Sdk="Microsoft.NET.Sdk"><PropertyGroup><TargetFramework>net8.0'
        "</TargetFramework></PropertyGroup></Project>",
        encoding="utf-8",
    )
    (source / "Entry.cs").write_text(SOURCE, encoding="utf-8")
    return source


def roslyn(source, env):
    # 父脚本也使用净化环境，分析helper不会继承供应商凭据或正式配置路径。
    previous = dict(os.environ)
    os.environ.clear()
    os.environ.update(env)
    try:
        from app.modules.source_analysis.csharp import CSharpAnalysis
        from app.modules.source_analysis.workspace import Workspace

        index = CSharpAnalysis(Workspace(source))
        try:
            result = index.analyze("Entry.cs", 7)
            require(result.get("analysis") == "Roslyn semantic binding", "roslyn_unavailable")
            calls = result["calls"]
            require(
                calls[0]["target"]["symbol"] == "IWorker.Run(int)"
                and calls[0]["possible_implementations"][0]["symbol"] == "Worker.Run(int)"
                and calls[1]["target"]["symbol"] == "Worker.Run(string)",
                "roslyn_call_binding_failed",
            )
            require(not result["diagnostics"], "roslyn_fixture_diagnostics")
            callers = index.analyze("Entry.cs", 3)
            require(
                any(item["caller"]["symbol"] == "Entry.Main()" for item in callers["callers"]),
                "roslyn_callers_missing",
            )
        finally:
            index.close()
    finally:
        os.environ.clear()
        os.environ.update(previous)


def check(checks, name, operation):
    checks[name] = False
    result = operation()
    checks[name] = True
    return result


def execute(root, token, checks, hashes):
    source = fixture(root)
    hashes["source_before"] = tree_hash(source)
    data = root / "data"
    host = urlsplit(ORIGIN).hostname
    env = environment(root, data, source, ORIGIN, host)
    check(checks, "real_roslyn_symbols_calls", lambda: roslyn(source, env))
    with running(env, root / "uvicorn-first.log", host) as client:
        checks["real_uvicorn_health"] = True
        check(checks, "frontend_html_js_css", lambda: frontend(client))
        check(
            checks,
            "unauthenticated_api_rejected",
            lambda: request(client, "GET", "/api/projects", status=401),
        )
        password = bootstrap_password(data)
        check(checks, "company_origin_login", lambda: login(client, password, ORIGIN))
        check(checks, "csrf_origin_host_guards", lambda: csrf_checks(client, ORIGIN))
        saved = check(checks, "http_fixture_and_isolated_edit", lambda: populate(client, source))
        require(saved["source_hash"] == hashes["source_before"], "original_source_changed")
        check(
            checks,
            "duplicate_data_process_rejected",
            lambda: reject_duplicate(env, root / "uvicorn-duplicate.log"),
        )
        archive = check(checks, "online_sqlite_backup", lambda: online_backup(client, root, token))
    check(checks, "sqlite_wal_integrity", lambda: database_integrity(data))
    with running(env, root / "uvicorn-restart.log", host) as client:
        login(client, password, ORIGIN)
        check(
            checks,
            "restart_material_attachment_copy_persistence",
            lambda: persistent(client, saved),
        )
    target = target_token = None
    if configured := os.environ.get("ARKS_LINUX_SMOKE_RESTORE_ROOT"):
        candidate = Path(configured).resolve()
        require(
            not candidate.is_relative_to(root) and not root.is_relative_to(candidate),
            "restore_root_overlaps_smoke_root",
        )
        target, target_token = prepare_root(configured)
        require(root.stat().st_dev != target.stat().st_dev, "restore_volume_not_separate_device")
        checks["restore_separate_mount"] = True
    restored = check(
        checks,
        "backup_restore_temporary_data",
        lambda: restore(archive, root, token, target, target_token),
    )
    restored_env = environment(root, restored, source, ORIGIN, host)
    with running(restored_env, root / "uvicorn-restored.log", host) as client:
        login(client, password, ORIGIN)
        check(checks, "restored_http_material_attachment_copy", lambda: persistent(client, saved))
    hashes["source_after"] = tree_hash(source)
    require(hashes["source_before"] == hashes["source_after"], "original_source_changed")
    checks["original_source_unchanged"] = True
    checks["no_agent_or_verification_command_started"] = True


def main():
    root = token = None
    checks, hashes = {}, {}
    try:
        require(sys.platform.startswith("linux"), "linux_runtime_required")
        root, token = prepare_root(os.environ.get("ARKS_LINUX_SMOKE_ROOT", ""))
        execute(root, token, checks, hashes)
        write_report(root, token, checks, hashes)
        print("linux_runtime_smoke_passed")
        return 0
    except Exception as error:
        category = str(error) if isinstance(error, SmokeFailure) else "runtime_error"
        if root is not None:
            try:
                write_report(root, token, checks, hashes, category)
            except (OSError, SmokeFailure):
                category = "report_identity_or_io_failed"
        # 不打印HTTP异常正文、初始密码、Cookie、CSRF或数据库原文。
        print(f"linux_runtime_smoke_failed:{category}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
