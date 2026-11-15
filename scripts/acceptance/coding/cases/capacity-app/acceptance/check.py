"""独立验收：构建真实 WinForms 应用并检查 --title-suffix 的窗口标题。"""

import subprocess
import time
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


def window_title(pid):
    try:
        completed = subprocess.run(
            [
                "powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
                f"(Get-Process -Id {pid}).MainWindowTitle",
            ],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
        )
        return (completed.stdout or "").strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def run_app(exe, args):
    process = subprocess.Popen(
        [str(exe), *args], cwd=str(exe.parent),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        time.sleep(8)
        if process.poll() is not None:
            return None, f"启动后退出，exit={process.returncode}"
        return window_title(process.pid), ""
    finally:
        try:
            process.kill()
        except OSError:
            pass


def main():
    root = Path.cwd()
    msbuild = find_msbuild()
    if not msbuild:
        print("FAIL 找不到 MSBuild")
        return 1
    solution = next(root.glob("*.sln"), None)
    if solution is None:
        print("FAIL 找不到 sln")
        return 1
    build = subprocess.run(
        [msbuild, str(solution), "/p:Configuration=Debug", "/m", "/nologo", "/v:m"],
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
    )
    check("解决方案构建", build.returncode == 0, (build.stdout + build.stderr)[-600:])

    exe = root / "CapacityStatistics" / "bin" / "Debug" / "CapacityStatistics.exe"
    check("应用可执行文件存在", exe.is_file(), str(exe))
    if not exe.is_file():
        return 1

    title, error = run_app(exe, [])
    check("默认标题保持", title is not None and "产能统计" in title and "TEST123" not in title,
          f"title={title!r} {error}")

    title, error = run_app(exe, ["--title-suffix", "TEST123"])
    check("title-suffix 生效", title is not None and "TEST123" in title,
          f"title={title!r} {error}")

    title, error = run_app(exe, ["--title-suffix", "A B"])
    check("title-suffix 支持空格", title is not None and "A B" in title,
          f"title={title!r} {error}")

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
