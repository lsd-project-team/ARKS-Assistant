"""独立验收：MSBuild 构建直连 SQLite 的 WinForms 应用，核对页面/统计/导出。"""

import csv
import re
import sqlite3
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


def find_msbuild():
    vswhere = Path(r"C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe")
    if vswhere.is_file():
        completed = subprocess.run(
            [str(vswhere), "-latest", "-products", "*", "-requires",
             "Microsoft.Component.MSBuild", "-find", "MSBuild\\**\\Bin\\MSBuild.exe"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        for line in (completed.stdout or "").splitlines():
            candidate = Path(line.strip())
            if candidate.is_file():
                return str(candidate)
    for candidate in (
        Path(r"D:\VisualStudio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"),
        Path(r"C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"),
    ):
        if candidate.is_file():
            return str(candidate)
    return ""


def week_rows(db):
    monday = date(2026, 3, 9)
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = []
    for offset in range(7):
        day = monday + timedelta(days=offset)
        value = con.execute(
            "select coalesce(sum(count),0) from cap where date=?", (day.isoformat(),)
        ).fetchone()[0]
        rows.append((day.isoformat(), int(value)))
    con.close()
    return rows


def month_total(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    value = con.execute(
        "select coalesce(sum(count),0) from cap where substr(date,1,7)='2026-03'"
    ).fetchone()[0]
    con.close()
    return int(value)


def main():
    root = Path.cwd()
    msbuild = find_msbuild()
    if not msbuild:
        print("FAIL 找不到 MSBuild")
        return 1
    projects = [path for path in root.rglob("*.csproj") if "bin" not in path.parts and "obj" not in path.parts]
    check("找到工程", bool(projects), "缺少 csproj")
    if not projects:
        return 1
    project = projects[0]
    build = subprocess.run(
        [msbuild, str(project), "/p:Configuration=Debug", "/m", "/nologo", "/v:m"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
    )
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-800:])
    exe_dir = project.parent / "bin" / "Debug"
    exes = sorted(exe_dir.glob("*.exe")) if exe_dir.is_dir() else []
    check("生成 exe", bool(exes), str(exe_dir))
    if not exes:
        return 1
    exe = exes[0]
    interop = root / "refs" / "SQLite.Interop.dll"
    if interop.is_file() and not (exe_dir / "SQLite.Interop.dll").is_file():
        (exe_dir / "SQLite.Interop.dll").write_bytes(interop.read_bytes())

    db = root / "data" / "capacity.db"
    rows = week_rows(db)
    week = sum(value for _, value in rows)
    month = month_total(db)

    for index, page in enumerate(PAGES):
        shot = root / "shots" / f"p{index}.png"
        layout = root / "shots" / f"p{index}.png.layout.txt"
        result = subprocess.run(
            [str(exe), "--screenshot", str(shot), str(index)],
            cwd=exe_dir, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=120,
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
            check("WEEK 文本", re.search(rf"WEEK\s+{week}\b", text) is not None,
                  f"expected WEEK {week}")
            check("MONTH 文本", re.search(rf"MONTH\s+{month}\b", text) is not None,
                  f"expected MONTH {month}")

    export = root / "export.csv"
    result = subprocess.run(
        [str(exe), "--export", str(export)], cwd=exe_dir, capture_output=True,
        text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    check("导出命令", result.returncode == 0 and export.is_file(),
          (result.stdout + result.stderr)[-300:])
    if export.is_file():
        with export.open(encoding="utf-8", newline="") as handle:
            exported = [(row.get("date"), int(row.get("count", -1))) for row in csv.DictReader(handle)]
        check("导出数据", exported == rows, f"actual={exported}")

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
