"""编码验收 CI：多轮跑用例、汇总报告、失败即非零退出。

用法：
    backend\\.venv\\Scripts\\python.exe scripts\\acceptance\\coding\\ci.py --rounds 2
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
ALL_CASES = [
    "python-cli",
    "dotnet-console",
    "bugfix-python",
    "refactor-python",
    "bugfix-multi",
    "web-static",
]


def latest_run(case, started):
    root = ROOT / "output" / "acceptance"
    candidates = [
        path
        for path in root.glob(f"coding-{case}-*")
        if path.is_dir() and path.stat().st_mtime >= started
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=",".join(ALL_CASES))
    parser.add_argument("--rounds", type=int, default=1)
    parser.add_argument("--port", type=int, default=8791)
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    cases = [item.strip() for item in args.cases.split(",") if item.strip()]
    stamp = time.strftime("%Y%m%d-%H%M%S")
    report_dir = ROOT / "output" / "acceptance" / f"coding-ci-{stamp}"
    report_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for round_index in range(1, args.rounds + 1):
        for case in cases:
            started = time.time()
            completed = subprocess.run(
                [
                    sys.executable,
                    str(BASE / "run.py"),
                    "--case",
                    case,
                    "--port",
                    str(args.port),
                    "--timeout",
                    str(args.timeout),
                    "--keep",
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            elapsed = round(time.time() - started)
            run_dir = latest_run(case, started)
            grade = {}
            result = {}
            if run_dir:
                try:
                    grade = json.loads(
                        (run_dir / "grade.json").read_text(encoding="utf-8")
                    )
                except (OSError, ValueError):
                    grade = {}
                try:
                    result = json.loads(
                        (run_dir / "result.json").read_text(encoding="utf-8")
                    )
                except (OSError, ValueError):
                    result = {}
            checks = grade.get("checks", {})
            row = {
                "round": round_index,
                "case": case,
                "exit": completed.returncode,
                "status": result.get("status", ""),
                "grade": bool(grade.get("ok")),
                "selftest": bool(checks.get("selftest", {}).get("ok")),
                "acceptance": bool(checks.get("acceptance", {}).get("ok")),
                "seconds": elapsed,
                "run_dir": str(run_dir) if run_dir else "",
            }
            rows.append(row)
            print(
                f"[ci] round={round_index} {case} exit={row['exit']} "
                f"status={row['status']} grade={row['grade']} "
                f"acceptance={row['acceptance']} {elapsed}s"
            )
            if not row["grade"] and completed.stdout:
                print((completed.stdout or "")[-400:])
    passed = [row for row in rows if row["exit"] == 0 and row["grade"]]
    report = {
        "ok": len(passed) == len(rows),
        "rows": rows,
        "passed": len(passed),
        "total": len(rows),
    }
    (report_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    lines = [
        f"# 编码验收 CI（{stamp}）",
        "",
        f"轮次：{args.rounds}；用例：{len(cases)}；通过：{len(passed)}/{len(rows)}",
        "",
        "| 轮 | 用例 | 状态 | 评分 | 独立验收 | 自测 | 耗时 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            f"| {row['round']} | {row['case']} | {row['status']} | "
            f"{'PASS' if row['grade'] else 'FAIL'} | "
            f"{'PASS' if row['acceptance'] else 'FAIL'} | "
            f"{'PASS' if row['selftest'] else 'WARN'} | {row['seconds']}s |"
        )
    (report_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[ci] report {report_dir} {len(passed)}/{len(rows)}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
