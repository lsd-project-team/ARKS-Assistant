"""独立验收：构建 WinForms 应用、生成两页截图并做布局断言。"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "backend"))

from app.modules.coding import ui_checks  # noqa: E402

FAILS = []


def check(name, condition, detail=""):
    print(("PASS " if condition else "FAIL ") + name + ("" if condition else f": {detail}"))
    if not condition:
        FAILS.append(name)


def run(args, timeout=240):
    return subprocess.run(
        args,
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def main():
    root = Path.cwd()
    build = run(["dotnet", "build"])
    check("dotnet build", build.returncode == 0, (build.stdout + build.stderr)[-400:])

    shots = []
    outputs = []
    for index in range(2):
        relative = f"shots/ci_tab{index}.png"
        result = run(
            ["dotnet", "run", "--project", "App.csproj", "--", "--screenshot", relative, str(index)]
        )
        check(f"截图 tab{index} 退出码 0", result.returncode == 0, (result.stdout + result.stderr)[-400:])
        target = root / relative
        if target.is_file():
            shots.append(relative)
        layout = root / f"{relative}.layout.txt"
        outputs.append(layout.read_text(encoding="utf-8", errors="replace") if layout.is_file() else "")
        check(f"截图 tab{index} 已生成", target.is_file(), relative)

    report = ui_checks.evaluate_layout(
        ui_checks.parse_layout("\n".join(outputs)),
        [ui_checks.analyze_screenshot(root / shot) for shot in shots],
    )
    check("布局断言", report["ok"], "；".join(report["issues"]))
    check("页签数量为 2", all(
        sum(1 for row in ui_checks.parse_layout(text) if row["type"] == "TabPage") == 2
        for text in outputs
    ))
    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
