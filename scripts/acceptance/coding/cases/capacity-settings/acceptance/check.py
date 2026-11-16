"""验收设置持久化：set/get、JSON 合并、重启读取、设置页显示。"""

import json
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


def run(exe, args):
    result = subprocess.run([str(exe), *args], cwd=exe.parent, capture_output=True, timeout=120)
    raw = (result.stdout or b"") + (result.stderr or b"")
    for encoding in ("gb18030", "utf-8"):
        text = raw.decode(encoding, errors="replace")
        if "\ufffd" not in text:
            break
    return result.returncode, text.strip()


def main():
    root = Path.cwd()
    projects = [p for p in root.rglob("*.csproj") if "SelfTest" not in p.name]
    if not projects:
        print("FAIL 找不到工程")
        return 1
    build = subprocess.run(["dotnet", "build", str(projects[0])], cwd=root,
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=600)
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-600:])
    exes = [p for p in root.rglob("bin/Debug/**/CapacityStats.exe") if "obj" not in p.parts]
    check("生成 exe", bool(exes), "没有 CapacityStats.exe")
    if not exes:
        return 1
    exe = exes[0]
    settings = exe.parent / "settings.json"
    if settings.is_file():
        settings.unlink()

    code, _ = run(exe, ["--set-setting", "shift.day", "07:00:00"])
    check("set shift.day", code == 0, str(code))
    code, value = run(exe, ["--get-setting", "shift.day"])
    check("get shift.day", code == 0 and value == "07:00:00", f"code={code} value={value!r}")

    code, _ = run(exe, ["--set-setting", "shift.night", "19:00:00"])
    code2, value2 = run(exe, ["--get-setting", "shift.night"])
    code3, day = run(exe, ["--get-setting", "shift.day"])
    check("合并写入", code == 0 and code2 == 0 and day == "07:00:00", f"{code} {code2} {value2} {day}")

    if settings.is_file():
        data = json.loads(settings.read_text(encoding="utf-8"))
        check("settings.json 内容",
              data.get("shift.day") == "07:00:00" and data.get("shift.night") == "19:00:00",
              str(data))
    else:
        check("settings.json 存在", False, str(settings))

    code, _ = run(exe, ["--get-setting", "missing.key"])
    check("缺失键退出码 2", code == 2, str(code))

    shot = root / "shots" / "settings.png"
    shot.parent.mkdir(exist_ok=True)
    code, output = run(exe, ["--screenshot", str(shot), "5"])
    layout = Path(str(shot) + ".layout.txt")
    if layout.is_file():
        output += layout.read_text(encoding="utf-8", errors="replace")
    check("设置页截图", code == 0 and shot.is_file(), output[-300:])
    check("设置页显示值", "07:00:00" in output, "未显示 shift.day")
    if shot.is_file():
        stats = ui_checks.analyze_screenshot(shot)
        check("截图非空白", stats["stddev"] >= 5.0, str(stats))

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
