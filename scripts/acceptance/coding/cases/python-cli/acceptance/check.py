"""独立验收：直接跑 csvjson.py，不依赖 Agent 自写的测试。"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def run_cli(args):
    return subprocess.run(
        [sys.executable, "csvjson.py", *args],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        source = root / "in.csv"
        source.write_text('a,b\n1,"x,y"\n', encoding="utf-8")
        output = root / "out.json"
        result = run_cli([str(source), str(output), "--indent", "4"])
        check("基础转换退出码 0", result.returncode == 0, result.stderr)
        try:
            data = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            data = None
            check("输出是合法 JSON", False, str(error))
        check("字段与引号逗号", data == [{"a": "1", "b": "x,y"}], str(data))
        raw = output.read_text(encoding="utf-8") if output.is_file() else ""
        check("indent 4 生效", '\n        "a"' in raw, repr(raw[:100]))

        empty = root / "empty.csv"
        empty.write_text("", encoding="utf-8")
        empty_out = root / "empty.json"
        result = run_cli([str(empty), str(empty_out)])
        check("空文件退出码 0", result.returncode == 0, result.stderr)
        try:
            data = json.loads(empty_out.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        check("空文件输出 []", data == [], str(data))

        result = run_cli([str(root / "missing.csv"), str(root / "x.json")])
        check("缺文件退出码 2", result.returncode == 2, str(result.returncode))
    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
