"""独立验收：构建从零生成的 WinForms 看板，核对界面结构与周/月统计文本。"""

import csv
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "backend"))
from app.modules.coding import ui_checks  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def expected(csv_path):
    rows = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["date"]] = int(row["count"])
    monday = date(2026, 3, 10) - timedelta(days=date(2026, 3, 10).weekday())
    week = sum(rows.get((monday + timedelta(days=i)).isoformat(), 0) for i in range(7))
    month = sum(value for key, value in rows.items() if key.startswith("2026-03"))
    return week, month


def main():
    root = Path.cwd()
    build = subprocess.run(
        ["dotnet", "build"], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-600:])

    week, month = expected(root / "data" / "capacity.csv")
    result = subprocess.run(
        ["dotnet", "run", "--project", "App.csproj", "--", "--screenshot", "shots/ui0.png", "0"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300,
    )
    check("截图命令", result.returncode == 0, (result.stdout + result.stderr)[-600:])
    shot = root / "shots" / "ui0.png"
    layout = root / "shots" / "ui0.png.layout.txt"
    check("截图与控件树", shot.is_file() and layout.is_file(), "缺少截图/布局文件")
    if not (shot.is_file() and layout.is_file()):
        return 1

    text = layout.read_text(encoding="utf-8", errors="replace")
    rows = ui_checks.parse_layout(text)
    report = ui_checks.evaluate_layout(rows, [ui_checks.analyze_screenshot(shot)])
    check("界面结构", report["ok"], "；".join(report["issues"]))

    form_match = re.search(r"FORM \S+ bounds=\{[^}]*\} text=\"(.*?)\"", text)
    title = form_match.group(1) if form_match else ""
    check("窗口标题", "产能统计" in title, f"title={title!r}")

    check("WEEK 文本", re.search(rf"WEEK\s+{week}\b", text) is not None,
          f"expected WEEK {week}")
    check("MONTH 文本", re.search(rf"MONTH\s+{month}\b", text) is not None,
          f"expected MONTH {month}")

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
