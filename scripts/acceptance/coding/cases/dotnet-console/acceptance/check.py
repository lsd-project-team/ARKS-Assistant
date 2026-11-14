"""独立验收：直接运行控制台程序分析样例日志，不依赖 Agent 自写的自测工程。"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def run(project, args, timeout=120):
    return subprocess.run(
        ["dotnet", "run", "--project", str(project), "--", *args],
        cwd=project.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def main():
    root = Path.cwd()
    projects = [
        path
        for path in root.rglob("*.csproj")
        if "tests" not in path.parts
        and "bin" not in path.parts
        and "obj" not in path.parts
        and "SelfTest" not in path.name
    ]

    def runnable(path):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return 0
        if re.search(r"<OutputType>\s*(?:Win)?Exe\s*</OutputType>", text, re.I):
            return 2
        if (path.parent / "Program.cs").is_file() and "Library" not in text:
            return 1
        return 0

    projects = sorted(projects, key=lambda path: (-runnable(path), str(path)))
    if not projects or runnable(projects[0]) == 0:
        print("FAIL 找不到可运行的 Exe 工程 csproj")
        return 1
    project = projects[0]
    build = subprocess.run(
        ["dotnet", "build", str(project)],
        cwd=project.parent,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    check("dotnet build", build.returncode == 0, (build.stdout + build.stderr)[-400:])
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "sample.log"
        log.write_text(
            "2026-01-02 10:00:00 INFO hello\n"
            "2026-01-02 10:01:00 WARN warn\n"
            "2026-01-02 10:02:00 ERROR err\n"
            "bad line without fields\n",
            encoding="utf-8",
        )
        result = run(project, [str(log)])
        output = result.stdout + result.stderr
        check("基础分析退出码 0", result.returncode == 0, output[-300:])
        check("统计到 3 条有效行", re.search(r"总行数\s*[:：]\s*3", output) is not None, output[-400:])
        check(
            "首末时间正确",
            "2026-01-02 10:00:00" in output and "2026-01-02 10:02:00" in output,
            output[-500:],
        )
        check("坏行被单独统计", re.search(r"坏行数\s*[:：]\s*1", output) is not None, output[-400:])

        log2 = Path(tmp) / "two-valid.log"
        log2.write_text(
            "2026-01-02 11:00:00 INFO one\n"
            "2026-01-02 11:01:00 WARN two\n"
            "not-a-timestamp INFO bad\n",
            encoding="utf-8",
        )
        result = run(project, [str(log2)])
        output = result.stdout + result.stderr
        check(
            "2 条有效 + 1 坏行：总数 2",
            re.search(r"总行数\s*[:：]\s*2", output) is not None,
            output[-400:],
        )
        check(
            "2 条有效 + 1 坏行：坏行 1",
            re.search(r"坏行数\s*[:：]\s*1", output) is not None,
            output[-300:],
        )

        log3 = Path(tmp) / "bad-level.log"
        log3.write_text(
            "2026-01-02 12:00:00 INFO ok\n"
            "2026-01-02 12:01:00 BOGUS bad-level\n"
            "2026-01-02 12:02:00 WARN ok\n",
            encoding="utf-8",
        )
        result = run(project, [str(log3)])
        output = result.stdout + result.stderr
        check(
            "非法等级算坏行：总数 2",
            re.search(r"总行数\s*[:：]\s*2", output) is not None,
            output[-400:],
        )
        check(
            "非法等级算坏行：坏行 1",
            re.search(r"坏行数\s*[:：]\s*1", output) is not None,
            output[-300:],
        )

        result = run(project, [str(log), "--level", "ERROR"])
        output = result.stdout + result.stderr
        check("等级过滤退出码 0", result.returncode == 0, output[-300:])
        check(
            "等级过滤只保留 ERROR",
            re.search(r"INFO\s*:\s*0", output) is not None
            and re.search(r"ERROR\s*:\s*1", output) is not None,
            output[-500:],
        )

        result = run(project, [str(Path(tmp) / "missing.log")])
        check("缺文件退出码 2", result.returncode == 2, str(result.returncode))
    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
