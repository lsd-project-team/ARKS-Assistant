"""独立验收：构建从零生成的 CLI，并与 sqlite 计算结果对比。"""

import sqlite3
import subprocess
from datetime import date, timedelta
from pathlib import Path

FAILS = []


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


def expected_week(db, day):
    monday = day - timedelta(days=day.weekday())
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    lines, total = [], 0
    for offset in range(7):
        current = monday + timedelta(days=offset)
        value = con.execute(
            "select coalesce(sum(count),0) from cap where date=?", (current.isoformat(),)
        ).fetchone()[0]
        lines.append(f"DAY {current.isoformat()} {value}")
        total += value
    con.close()
    return lines + [f"TOTAL {total}"]


def expected_month(db, month):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    total = con.execute(
        "select coalesce(sum(count),0) from cap where substr(date,1,7)=?", (month,)
    ).fetchone()[0]
    con.close()
    return [f"TOTAL {total}"]


def main():
    root = Path.cwd()
    msbuild = find_msbuild()
    if not msbuild:
        print("FAIL 找不到 MSBuild")
        return 1
    projects = [
        path for path in root.rglob("*.csproj")
        if not any(part in {"bin", "obj", "refs"} for part in path.parts)
    ]
    if not projects:
        check("找到工程文件", False, "没有 .csproj")
        return 1
    project = projects[0]
    build = subprocess.run(
        [msbuild, str(project), "/p:Configuration=Debug", "/m", "/nologo", "/v:m"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    check("项目构建", build.returncode == 0, (build.stdout + build.stderr)[-600:])

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
    week_day = date(2026, 3, 10)
    result = subprocess.run(
        [str(exe), str(db), "week", week_day.isoformat()],
        cwd=exe_dir, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    actual = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    check("week 退出码 0", result.returncode == 0, result.stderr[-300:])
    check("week 每日/总计", actual == expected_week(db, week_day), f"actual={actual}")

    result = subprocess.run(
        [str(exe), str(db), "month", "2026-02"],
        cwd=exe_dir, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    actual = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    check("month 总计", result.returncode == 0 and actual == expected_month(db, "2026-02"),
          f"actual={actual} err={result.stderr[-200:]}")

    result = subprocess.run(
        [str(exe), str(db), "week", "bad-date"],
        cwd=exe_dir, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    check("非法日期退出码 2", result.returncode == 2, str(result.returncode))

    result = subprocess.run(
        [str(exe), str(root / "data" / "missing.db"), "month", "2026-02"],
        cwd=exe_dir, capture_output=True, text=True, encoding="utf-8",
        errors="replace", timeout=120,
    )
    check("缺数据库退出码 2", result.returncode == 2, str(result.returncode))

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
