"""逐页验收：7 个页面截图/文本、数据库统计数字、CSV 导出。"""

import csv
import hashlib
import sqlite3
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "backend"))
from app.modules.coding import ui_checks  # noqa: E402

FAILS = []
PAGES = ["产能统计", "工况统计", "故障统计", "故障分类及趋势", "故障分析", "设置", "信息导出"]


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def totals(db, classification):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    week = 0
    for i in range(7):
        day = (date(2022, 4, 4) + timedelta(days=i)).isoformat()
        week += con.execute("select coalesce(sum(count),0) from cap where date=?", (day,)).fetchone()[0]
    month = con.execute(
        "select coalesce(sum(count),0) from cap where substr(date,1,7)='2022-04'"
    ).fetchone()[0]
    shift = con.execute("select coalesce(sum(count),0) from cap").fetchone()[0]
    con.close()
    con = sqlite3.connect(f"file:{classification}?mode=ro", uri=True)
    faults = con.execute("select count(*) from Info").fetchone()[0]
    classes = con.execute("select count(*) from Class").fetchone()[0]
    categories = con.execute("select count(*) from Category").fetchone()[0]
    rows = con.execute("select id,class,category,name from Info").fetchall()
    con.close()
    return int(week), int(month), int(shift), faults, classes, categories, rows


def main():
    root = Path.cwd()
    project = root / "CapacityStats" / "CapacityStats.csproj"
    build = subprocess.run(["dotnet", "build", str(project)], cwd=root, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=600)
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-800:])
    exes = list((root / "CapacityStats" / "bin" / "Debug").rglob("CapacityStats.exe"))
    check("生成 exe", bool(exes), "找不到 CapacityStats.exe")
    if not exes:
        return 1
    exe = exes[0]
    week, month, shift, faults, classes, categories, info_rows = totals(
        root / "data" / "AKRS.capacity.db", root / "data" / "AKRS.Classification.db"
    )
    tokens = [
        [f"WEEK {week}", f"MONTH {month}"],
        [f"SHIFT {shift}"],
        [f"FAULT {faults}"],
        [f"CLASS {classes}"],
        [f"CATEGORY {categories}"],
        [],
        [],
    ]
    hashes = []
    for index, page in enumerate(PAGES):
        shot = root / "shots" / f"p{index}.png"
        result = subprocess.run([str(exe), "--screenshot", str(shot), str(index)],
                                cwd=exe.parent, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=120)
        output = (result.stdout or "") + (result.stderr or "")
        layout = Path(str(shot) + ".layout.txt")
        if layout.is_file():
            output += layout.read_text(encoding="utf-8", errors="replace")
        check(f"页面 {index} 截图", result.returncode == 0 and shot.is_file(), output[-300:])
        check(f"页面 {index} 标题", f"PAGE {page}" in output, page)
        for token in tokens[index]:
            check(f"页面 {index} {token}", token in output, "文本未出现")
        if shot.is_file():
            stats = ui_checks.analyze_screenshot(shot)
            check(f"页面 {index} 非空白", stats["stddev"] >= 5.0, str(stats))
            hashes.append(hashlib.sha1(shot.read_bytes()).hexdigest())

    check("页面截图互不相同", len(set(hashes)) == len(hashes), f"{len(set(hashes))}/{len(hashes)}")

    export = root / "export"
    export.mkdir(exist_ok=True)
    result = subprocess.run([str(exe), "--export", str(export)], cwd=exe.parent,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace", timeout=120)
    check("导出命令", result.returncode == 0, (result.stdout + result.stderr)[-300:])
    capacity_csv = export / "capacity.csv"
    faults_csv = export / "faults.csv"
    check("capacity.csv", capacity_csv.is_file(), "缺少文件")
    if capacity_csv.is_file():
        with capacity_csv.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        expected = []
        con = sqlite3.connect(f"file:{root / 'data' / 'AKRS.capacity.db'}?mode=ro", uri=True)
        for i in range(7):
            day = (date(2022, 4, 4) + timedelta(days=i)).isoformat()
            expected.append((day, int(con.execute(
                "select coalesce(sum(count),0) from cap where date=?", (day,)).fetchone()[0])))
        con.close()
        actual = [(row.get("date"), int(row.get("count", -1))) for row in rows]
        check("capacity.csv 数据", actual == expected, f"actual={actual}")
    check("faults.csv", faults_csv.is_file(), "缺少文件")
    if faults_csv.is_file():
        with faults_csv.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        check("faults.csv 行数", len(rows) == len(info_rows), f"{len(rows)} != {len(info_rows)}")

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
