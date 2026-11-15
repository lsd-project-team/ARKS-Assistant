"""独立验收：多页面截图、PAGE 标题、WEEK/MONTH 与 --export 数据。"""

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
PAGES = ["产能统计", "工况统计", "故障统计", "设置", "信息导出"]


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def load(csv_path):
    rows = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            rows[row["date"]] = int(row["count"])
    return rows


def main():
    root = Path.cwd()
    build = subprocess.run(
        ["dotnet", "build"], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=300,
    )
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-800:])

    rows = load(root / "data" / "capacity.csv")
    monday = date(2026, 3, 9)
    week_rows = [(monday + timedelta(days=i), rows.get((monday + timedelta(days=i)).isoformat(), 0))
                 for i in range(7)]
    week_total = sum(value for _, value in week_rows)
    month_total = sum(value for key, value in rows.items() if key.startswith("2026-03"))

    for index, page in enumerate(PAGES):
        shot = root / "shots" / f"p{index}.png"
        layout = root / "shots" / f"p{index}.png.layout.txt"
        result = subprocess.run(
            ["dotnet", "run", "--project", "CapacityStats.csproj", "--",
             "--screenshot", str(shot), str(index)],
            cwd=root, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300,
        )
        check(f"页面 {index} 截图", result.returncode == 0 and shot.is_file() and layout.is_file(),
              (result.stdout + result.stderr)[-300:])
        if not layout.is_file():
            continue
        text = layout.read_text(encoding="utf-8", errors="replace")
        check(f"页面 {index} 标题", f'text="PAGE {page}"' in text, page)
        stats = ui_checks.analyze_screenshot(shot)
        check(f"页面 {index} 非空白",
              stats["width"] >= 800 and stats["height"] >= 600 and stats["stddev"] >= 5.0,
              str(stats))
        if index == 0:
            check("窗口标题", re.search(r'FORM .*text="产能统计"', text) is not None, text[:120])
            check("WEEK 文本", re.search(rf"WEEK\s+{week_total}\b", text) is not None,
                  f"expected WEEK {week_total}")
            check("MONTH 文本", re.search(rf"MONTH\s+{month_total}\b", text) is not None,
                  f"expected MONTH {month_total}")

    export = root / "export.csv"
    result = subprocess.run(
        ["dotnet", "run", "--project", "CapacityStats.csproj", "--", "--export", str(export)],
        cwd=root, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=300,
    )
    check("导出命令", result.returncode == 0 and export.is_file(),
          (result.stdout + result.stderr)[-300:])
    if export.is_file():
        with export.open(encoding="utf-8", newline="") as handle:
            exported = list(csv.DictReader(handle))
        actual = [(row.get("date"), int(row.get("count", -1))) for row in exported]
        expected = [(day.isoformat(), value) for day, value in week_rows]
        check("导出数据", actual == expected, f"actual={actual}")

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
