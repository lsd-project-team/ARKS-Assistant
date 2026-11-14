"""独立验收：Python 服务 + Node 客户端双运行时检查。"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from service import User, list_payload, to_payload  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def main():
    payload = to_payload(User(1, "Ada", "Lovelace"))
    check("to_payload 增加 full_name", payload.get("full_name") == "Ada Lovelace", str(payload))
    check("保留 id/first/last", payload.get("id") == 1 and payload.get("first") == "Ada")

    unicode_payload = to_payload(User(2, "张", "三"))
    check("unicode full_name", unicode_payload.get("full_name") == "张 三", str(unicode_payload))
    check("list_payload 仍可用", len(list_payload([User(3, "A", "B")])) == 1)

    script = Path(__file__).resolve().parent / "check.mjs"
    result = subprocess.run(
        ["node", str(script)],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    check("Node 客户端验收", result.returncode == 0, f"exit={result.returncode}")

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
