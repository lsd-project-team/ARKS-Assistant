"""独立验收：构建并运行 CLI，验证补货与既有命令。"""

import subprocess
import tempfile
from pathlib import Path

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def main():
    root = Path.cwd()
    cli = next(
        (
            path
            for path in root.rglob("*.csproj")
            if "Cli" in path.name and "tests" not in path.parts
        ),
        None,
    )
    if cli is None:
        print("FAIL 找不到 CLI 工程")
        return 1
    build = subprocess.run(
        ["dotnet", "build", str(cli)],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    check("CLI 构建", build.returncode == 0, (build.stdout + build.stderr)[-400:])

    def run(*args, timeout=120):
        return subprocess.run(
            ["dotnet", "run", "--project", str(cli), "--", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    with tempfile.TemporaryDirectory() as tmp:
        state = str(Path(tmp) / "state.json")
        added = run(state, "add", "A", "Widget", "10", "2.5")
        check("add 退出码 0", added.returncode == 0, added.stderr[-300:])
        check("add 输出", "ADDED SKU=A" in added.stdout, added.stdout)
        run(state, "add", "B", "Bolt", "2", "5")
        low = run(state, "low", "3")
        check("低库存包含 B", "LOW SKU=B" in low.stdout and "LOW SKU=A" not in low.stdout, low.stdout)

        restock = run(state, "restock", "B", "4")
        check("restock 退出码 0", restock.returncode == 0, restock.stderr[-300:])
        check("restock 输出新数量", "RESTOCKED SKU=B QTY=6" in restock.stdout, restock.stdout)

        low = run(state, "low", "3")
        check("补货后无低库存", "LOW none" in low.stdout, low.stdout)

        value = run(state, "value")
        check("总值正确", "VALUE=55" in value.stdout, value.stdout)

        removed = run(state, "remove", "A", "3")
        check("remove 仍可用", removed.returncode == 0 and "REMOVED SKU=A QTY=7" in removed.stdout, removed.stdout)
        value = run(state, "value")
        check("移除后总值", "VALUE=47.5" in value.stdout, value.stdout)

        missing = run(state, "restock", "NOPE", "1")
        check("缺 SKU 退出码 2", missing.returncode == 2, str(missing.returncode))
        bad = run(state, "restock", "B", "0")
        check("非法数量退出码 2", bad.returncode == 2, str(bad.returncode))

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
