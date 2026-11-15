"""独立验收：仅依据截图/数据库复刻的应用——构建、启动、UIA 控件文本、截图、源码数据访问。"""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT / "backend"))
from app.modules.coding import ui_checks  # noqa: E402

FAILS = []
NAV = ["产能统计", "工况统计", "故障统计", "故障分类及趋势", "故障分析", "设置", "信息导出"]
BUTTONS = ["周统计", "月统计"]
UIA_SCRIPT = r"""
Add-Type -AssemblyName UIAutomationClient,UIAutomationTypes
$p = Get-Process -Id {pid}
if (-not $p.MainWindowHandle) {{ exit 1 }}
$root = [System.Windows.Automation.AutomationElement]::FromHandle($p.MainWindowHandle)
$all = $root.FindAll([System.Windows.Automation.TreeScope]::Descendants, [System.Windows.Automation.Condition]::TrueCondition)
foreach ($e in $all) {{
  try {{ if ($e.Current.Name) {{ $e.Current.Name }} }} catch {{}}
}}
"""


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
    return str(Path(r"D:\VisualStudio\2022\Community\MSBuild\Current\Bin\MSBuild.exe"))


def main():
    root = Path.cwd()
    projects = [p for p in root.rglob("*.csproj") if "bin" not in p.parts and "obj" not in p.parts]
    if not projects:
        print("FAIL 没有 csproj")
        return 1
    sdk = any("Sdk=" in p.read_text(encoding="utf-8", errors="replace")[:500] for p in projects)
    if sdk:
        build = subprocess.run(["dotnet", "build"], cwd=root, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
    else:
        build = subprocess.run([find_msbuild(), str(projects[0]), "/p:Configuration=Debug", "/m",
                                "/nologo", "/v:m"], cwd=root, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=600)
    check("构建", build.returncode == 0, (build.stdout + build.stderr)[-800:])

    exes = [p for p in root.rglob("bin/Debug/*.exe")
            if "vshost" not in p.name.lower() and "obj" not in p.parts]
    check("生成 exe", bool(exes), "bin/Debug 下没有 exe")
    if not exes:
        return 1
    exe = exes[0]
    process = subprocess.Popen([str(exe)], cwd=str(exe.parent))
    try:
        import time

        time.sleep(6)
        if process.poll() is not None:
            check("应用启动", False, f"exit={process.returncode}")
            return 1
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             f"(Get-Process -Id {process.pid}).MainWindowTitle"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20,
        )
        title = (completed.stdout or "").strip()
        check("窗口标题", "产能统计" in title, f"title={title!r}")

        names = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
             UIA_SCRIPT.format(pid=process.pid)],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        ).stdout
        for label in NAV:
            check(f"导航 {label}", label in names, "UIA 未找到")
        for label in BUTTONS:
            check(f"按钮 {label}", label in names, "UIA 未找到")

        shot = root / "shots" / "app.png"
        shot.parent.mkdir(exist_ok=True)
        capture = r"""
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W { [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r); public struct RECT { public int L,T,R,B; } }
'@
$p = Get-Process -Id {pid}
$r = New-Object W+RECT
[W]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
$w = $r.R - $r.L; $h = $r.B - $r.T
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($r.L, $r.T, 0, 0, (New-Object System.Drawing.Size $w, $h))
$bmp.Save("{shot}", [System.Drawing.Imaging.ImageFormat]::Png)
""".format(pid=process.pid, shot=str(shot))
        subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", capture],
                       capture_output=True, timeout=30)
        check("截图", shot.is_file(), str(shot))
        if shot.is_file():
            stats = ui_checks.analyze_screenshot(shot)
            check("截图非空白", stats["stddev"] >= 5.0, str(stats))

        sources = "\n".join(
            p.read_text(encoding="utf-8", errors="replace")
            for p in root.rglob("*.cs")
            if "bin" not in p.parts and "obj" not in p.parts
        )
        check("读取 cap 表", re.search(r"\bcap\b", sources, re.IGNORECASE) is not None)
        check("SQLite 访问", re.search(r"SQLite|Data Source|SELECT", sources, re.IGNORECASE) is not None)
    finally:
        try:
            process.kill()
        except OSError:
            pass

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
