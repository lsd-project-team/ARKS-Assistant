"""编码模块多案例验收：按 case.json 独立评分。"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.coding import diagnostics  # noqa: E402

SKIP = {"bin", "obj", ".git", ".vs", "publish", "node_modules", "__pycache__", ".pytest_cache"}
PLACEHOLDER = re.compile(r"\bTODO\b|\bFIXME\b")


def run(command, cwd, timeout=900):
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            shell=True,
        )
        return completed.returncode, (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired as error:
        return -1, f"命令超时：{error}"
    except OSError as error:
        return -1, f"命令无法启动：{error}"


def files(project):
    for path in project.rglob("*"):
        if path.is_file() and not any(part in SKIP for part in path.parts):
            yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    case_dir = BASE / "cases" / args.case
    case = json.loads((case_dir / "case.json").read_text(encoding="utf-8-sig"))
    project = Path(args.project).resolve()
    run_dir = Path(args.run_dir).resolve()
    checks = {}

    code, build_output = run(case["build"], project)
    parsed = diagnostics.parse_diagnostics(build_output, code)
    checks["build"] = {
        "ok": code == 0,
        "exit_code": code,
        "summary": parsed["summary"] if "dotnet" in case["build"] else f"退出码 {code}",
        "errors": parsed["errors"][:20],
        "warnings": parsed["warnings"][:20],
    }
    if "dotnet" in case["build"]:
        checks["build"]["ok"] = code == 0 and parsed["error_count"] == 0 and parsed["warning_count"] == 0

    code, test_output = run(case["test"], project)
    counts = diagnostics.parse_tests(test_output, code)
    checks["selftest"] = {
        "ok": code == 0 and counts["failed"] == 0 and counts["passed"] >= case["min_tests"],
        "exit_code": code,
        "passed": counts["passed"],
        "failed": counts["failed"],
        "required": case["min_tests"],
        "tail": test_output[-1200:],
        "note": "Agent 自写的测试；仅作交付质量告警，不决定验收",
    }

    if case.get("acceptance_command"):
        acceptance_command = case["acceptance_command"]
    elif case.get("acceptance"):
        script = (case_dir / case["acceptance"]).resolve()
        runner = "node" if script.suffix.lower() in {".mjs", ".js"} else "python"
        acceptance_command = f'{runner} "{script}"'
    else:
        acceptance_command = ""
    if acceptance_command:
        code, acceptance_output = run(acceptance_command, project)
        checks["acceptance"] = {
            "ok": code == 0,
            "exit_code": code,
            "tail": acceptance_output[-1500:],
            "command": acceptance_command,
        }
    else:
        checks["acceptance"] = {"ok": True, "note": "无独立验收脚本"}

    missing = [name for name in case["require_files"] if not (project / name).is_file()]
    checks["files"] = {"ok": not missing, "missing": missing}

    protected = case.get("protected", [])
    changed = []
    for relative in protected:
        seed = case_dir / "seed" / relative
        target = project / relative
        if not seed.is_file() or not target.is_file():
            changed.append(f"{relative}（缺失）")
            continue
        if hashlib.sha256(seed.read_bytes()).hexdigest() != hashlib.sha256(
            target.read_bytes()
        ).hexdigest():
            changed.append(relative)
    checks["protected"] = {"ok": not changed, "changed": changed}

    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in files(project)
        if path.suffix.lower() in {".py", ".cs", ".csproj", ".md", ".json", ".js", ".html"}
        and path.name != "任务书.md"
    )
    placeholders = sorted({match.group(0) for match in PLACEHOLDER.finditer(text)})
    checks["quality"] = {
        "ok": not placeholders,
        "placeholders": placeholders,
        "readme": any(path.name.lower().startswith("readme") for path in files(project)),
    }
    checks["quality"]["ok"] = checks["quality"]["ok"] and checks["quality"]["readme"]

    required = ["build", "acceptance", "files", "protected", "quality"]
    overall = all(checks[name].get("ok") for name in required)
    report = {"ok": overall, "case": case["name"], "checks": checks}
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "grade.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    lines = [
        f"# 编码验收：{case['title']}",
        "",
        f"项目：`{project}`",
        f"结论：{'通过' if overall else '未通过'}",
        "",
        "| 检查项 | 结果 | 说明 |",
        "| --- | --- | --- |",
    ]
    for name, label in [
        ("build", "构建"),
        ("acceptance", "独立验收"),
        ("selftest", "自测（告警）"),
        ("files", "必需文件"),
        ("protected", "测试文件未被修改"),
        ("quality", "代码规范"),
    ]:
        row = checks[name]
        detail = ""
        if name == "build":
            detail = row.get("summary", "")
        elif name == "acceptance":
            detail = "通过" if row.get("ok") else (row.get("tail") or "")[-160:]
        elif name == "selftest":
            detail = f"通过 {row['passed']}（要求 {row['required']}），失败 {row['failed']}"
        elif name == "files":
            detail = "缺少：" + "、".join(row["missing"]) if row["missing"] else "齐全"
        elif name == "protected":
            detail = "被修改：" + "、".join(row["changed"]) if row["changed"] else "未改动"
        elif name == "quality":
            detail = "占位：" + "、".join(row["placeholders"]) if row["placeholders"] else "无"
        lines.append(f"| {label} | {'通过' if row['ok'] else '失败'} | {detail} |")
    (run_dir / "grade.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({name: value.get("ok") for name, value in checks.items()}, ensure_ascii=False))
    print("OVERALL", "PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
