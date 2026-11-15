"""独立验收：从零 WinForms 应用的构建、截图、标题/导航/图表日期/周月统计。"""

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
    monday = date(2026, 3, 9)
    week = sum(rows.get((monday + timedelta(days=i)).isoformat(), 0) for i in range(7))
    month = sum(value for key, value in rows.items() if key.startswith("2026-03"))
    return week, month


def main():
    root = Path.cwd()
    build = subprocess.run(
        ["dotnet", "build"], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-800:])

    week, month = expected(root / "data" / "capacity.csv")
    result = subprocess.run(
        ["dotnet", "run", "--project", "CapacityStats.csproj", "--",
         "--screenshot", "shots/ui0.png", "0"],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300,
    )
    check("截图命令", result.returncode == 0, (result.stdout + result.stderr)[-800:])
    shot = root / "shots" / "ui0.png"
    layout = root / "shots" / "ui0.png.layout.txt"
    check("截图与控件树", shot.is_file() and layout.is_file(), "缺少截图/布局")
    if not (shot.is_file() and layout.is_file()):
        return 1
    text = layout.read_text(encoding="utf-8", errors="replace")

    check("窗口标题", re.search(r'FORM .*text="产能统计"', text) is not None, text[:200])
    for label in ["产能统计", "工况统计", "故障统计", "设置", "信息导出"]:
        check(f"导航 {label}", f'text="{label}"' in text)
    sources = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in root.rglob("*.cs")
        if "bin" not in path.parts and "obj" not in path.parts
    )
    drawn_range = (
        "2026-03-09" in sources
        and "2026-03-15" in sources
        and "yyyy-MM-dd" in sources
    )
    for offset in range(7):
        day = (date(2026, 3, 9) + timedelta(days=offset)).isoformat()
        check(
            f"日期 {day}",
            f'text="{day}"' in text or day in sources or drawn_range,
            "控件文本与绘制代码都没有该日期",
        )
    check("WEEK 文本", re.search(rf"WEEK\s+{week}\b", text) is not None, f"expected WEEK {week}")
    check("MONTH 文本", re.search(rf"MONTH\s+{month}\b", text) is not None, f"expected MONTH {month}")
    stats = ui_checks.analyze_screenshot(shot)
    check("截图非空白", stats["width"] >= 800 and stats["height"] >= 600 and stats["stddev"] >= 5.0, str(stats))

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
