"""SP900 一次性生成验收的独立评分：不信任 Agent 的自述，直接构建、跑自测、截图与静态检查。

用法：
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance\\sp900\\grade.py --project <目录> --run-dir <目录>
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.coding import diagnostics, ui_checks  # noqa: E402

SKIP = {"bin", "obj", ".git", ".vs", "publish", "node_modules"}
PLACEHOLDER = re.compile(r"TODO|FIXME|占位", re.IGNORECASE)
PLACEHOLDER_COMMENT = re.compile(
    r"^\s*(?://|/\*|\*|#).*?(?:未实现|待实现)", re.MULTILINE
)


def run(command, cwd, timeout=600):
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        return completed.returncode, (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired as error:
        return -1, f"命令超时：{error}\n{error.stdout or ''}"
    except OSError as error:
        return -1, f"命令无法启动：{error}"


def project_files(project):
    for path in project.rglob("*"):
        if not path.is_file() or any(part in SKIP for part in path.parts):
            continue
        if path.suffix.lower() in {".cs", ".csproj", ".sln", ".md", ".xml"}:
            yield path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", required=True)
    parser.add_argument("--run-dir", required=True)
    args = parser.parse_args()
    project = Path(args.project).resolve()
    run_dir = Path(args.run_dir).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    checks = {}

    csproj = next(iter(sorted(project.glob("*.csproj"))), None)
    checks["project_file"] = {
        "ok": csproj is not None,
        "detail": csproj.name if csproj else "项目根目录没有 .csproj",
    }

    if csproj:
        code, output = run(["dotnet", "build", csproj.name], project)
        parsed = diagnostics.parse_diagnostics(output, code)
        checks["build"] = {
            "ok": code == 0 and parsed["error_count"] == 0 and parsed["warning_count"] == 0,
            "exit_code": code,
            "errors": parsed["errors"][:20],
            "warnings": parsed["warnings"][:20],
            "error_count": parsed["error_count"],
            "warning_count": parsed["warning_count"],
            "zero_warnings": parsed["warning_count"] == 0,
            "summary": parsed["summary"],
        }
        tests = sorted((project / "tests").glob("**/*.csproj")) if (project / "tests").is_dir() else []
        if tests:
            test_project = tests[0]
            code, output = run(
                ["dotnet", "run", "--project", str(test_project)], project, timeout=900
            )
            counts = diagnostics.parse_tests(output, code)
            checks["self_test"] = {
                "ok": code == 0 and counts["passed"] >= 8 and counts["failed"] == 0,
                "exit_code": code,
                "passed": counts["passed"],
                "failed": counts["failed"],
                "project": str(test_project.relative_to(project)),
                "tail": output[-1500:],
            }
        else:
            checks["self_test"] = {"ok": False, "detail": "没有 tests/ 下的自测工程"}

        layout_text, shots, shot_errors = "", [], []
        for index in range(2):
            relative = f"shots/grade_tab{index}.png"
            code, output = run(
                [
                    "dotnet",
                    "run",
                    "--project",
                    csproj.name,
                    "--",
                    "--screenshot",
                    relative,
                    str(index),
                ],
                project,
                timeout=600,
            )
            layout_text += output + "\n"
            layout_file = project / (relative + ".layout.txt")
            if layout_file.is_file():
                layout_text += layout_file.read_text(encoding="utf-8", errors="replace")
            png = project / relative
            if png.is_file():
                shots.append(relative)
            else:
                shot_errors.append(f"未生成 {relative}（退出码 {code}）")
        screenshots = [
            ui_checks.analyze_screenshot(project / shot) for shot in shots
        ]
        report = ui_checks.evaluate_layout(ui_checks.parse_layout(layout_text), screenshots)
        checks["ui"] = {
            "ok": report["ok"] and not shot_errors,
            "issues": report["issues"] + shot_errors,
            "notes": report["notes"],
            "counts": report["counts"],
            "screenshots": report["screenshots"],
        }
    else:
        checks["build"] = checks["self_test"] = checks["ui"] = {
            "ok": False,
            "detail": "没有工程文件",
        }

    sources = list(project_files(project))
    text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace") for path in sources if path.suffix != ".png"
    )
    placeholders = sorted(
        {match.group(0) for match in PLACEHOLDER.finditer(text)}
        | {match.group(0).strip() for match in PLACEHOLDER_COMMENT.finditer(text)}
    )
    checks["code_quality"] = {
        "ok": not placeholders,
        "placeholders": placeholders,
        "files": len(sources),
        "readme": any(path.name.lower().startswith("readme") for path in sources),
    }
    if csproj:
        project_text = csproj.read_text(encoding="utf-8", errors="replace")
        checks["code_quality"]["explicit_compile"] = "<Compile Include=" in project_text
        checks["code_quality"]["nullable"] = "<Nullable>enable</Nullable>" in project_text
        checks["code_quality"]["ok"] = (
            checks["code_quality"]["ok"]
            and checks["code_quality"]["explicit_compile"]
            and checks["code_quality"]["nullable"]
            and checks["code_quality"]["readme"]
        )

    hard = ["project_file", "build", "self_test", "ui", "code_quality"]
    overall = all(checks.get(name, {}).get("ok") for name in hard)
    report = {"ok": overall, "checks": checks}
    (run_dir / "grade.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    lines = ["# SP900 一次性生成验收报告", "", f"项目：`{project}`", f"结论：{'通过' if overall else '未通过'}", "", "| 检查项 | 结果 | 说明 |", "| --- | --- | --- |"]
    for name, label in [
        ("project_file", "工程文件"),
        ("build", "构建"),
        ("self_test", "回放自测"),
        ("ui", "界面结构/截图"),
        ("code_quality", "代码规范"),
    ]:
        row = checks.get(name, {})
        detail = row.get("summary") or row.get("detail") or ""
        if name == "self_test" and "passed" in row:
            detail = f"通过 {row['passed']}，失败 {row['failed']}"
        if name == "ui" and row.get("issues"):
            detail = "；".join(row["issues"][:4])
        if name == "code_quality" and row.get("placeholders"):
            detail = "残留：" + "、".join(row["placeholders"])
        lines.append(f"| {label} | {'通过' if row.get('ok') else '失败'} | {detail} |")
    if checks.get("ui", {}).get("screenshots"):
        lines += ["", "## 截图", ""]
        for shot in checks["ui"]["screenshots"]:
            lines.append(f"- `{shot.get('path')}` {shot.get('width')}×{shot.get('height')}")
    (run_dir / "grade.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({name: checks[name].get("ok") for name in hard}, ensure_ascii=False))
    print("OVERALL", "PASS" if overall else "FAIL")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
