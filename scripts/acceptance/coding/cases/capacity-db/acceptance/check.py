"""独立验收：构建真实 DB 库，并编译一个 MSBuild 检查程序直接调用新方法。"""

import subprocess
import tempfile
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
        cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300,
    )
    check("DB 库构建", build.returncode == 0, (build.stdout + build.stderr)[-500:])

    dll = root / "src" / "AKRS.Capacity.DB" / "bin" / "Debug" / "AKRS.Capacity.DB.dll"
    sqlite = root / "refs" / "System.Data.SQLite.dll"
    check("DB dll 存在", dll.is_file(), str(dll))
    if not dll.is_file() or not sqlite.is_file():
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        checker = Path(tmp)
        (checker / "Checker.csproj").write_text(
            "<Project ToolsVersion=\"15.0\" "
            "xmlns=\"http://schemas.microsoft.com/developer/msbuild/2003\">\n"
            "  <PropertyGroup>\n"
            "    <OutputType>Exe</OutputType>\n"
            "    <TargetFrameworkVersion>v4.8</TargetFrameworkVersion>\n"
            "    <AssemblyName>Checker</AssemblyName>\n"
            "  </PropertyGroup>\n"
            "  <ItemGroup>\n"
            f"    <Reference Include=\"AKRS.Capacity.DB\"><HintPath>{dll}</HintPath></Reference>\n"
            f"    <Reference Include=\"System.Data.SQLite\"><HintPath>{sqlite}</HintPath></Reference>\n"
            "  </ItemGroup>\n"
            "  <ItemGroup><Compile Include=\"Program.cs\" /></ItemGroup>\n"
            "  <Import Project=\"$(MSBuildToolsPath)\\Microsoft.CSharp.targets\" />\n"
            "</Project>\n",
            encoding="utf-8",
        )
        (checker / "Program.cs").write_text(
            "using System;\n"
            "using AKRS.Capacity.DB;\n"
            "class Checker {\n"
            "  static int fail = 0;\n"
            "  static void C(string name, bool ok) {\n"
            "    Console.WriteLine((ok ? \"PASS \" : \"FAIL \") + name);\n"
            "    if (!ok) fail++;\n"
            "  }\n"
            "  static int Main() {\n"
            "    C(\"null\", FaultClassification.NormalizeName(null) == \"\");\n"
            "    C(\"blank\", FaultClassification.NormalizeName(\"   \") == \"\");\n"
            "    C(\"trim\", FaultClassification.NormalizeName(\"  A   B \") == \"A B\");\n"
            "    C(\"tabs\", FaultClassification.NormalizeName(\"A\\t\\tB\") == \"A B\");\n"
            "    C(\"newline\", FaultClassification.NormalizeName(\"A \\n B\") == \"A B\");\n"
            "    return fail == 0 ? 0 : 1;\n"
            "  }\n"
            "}\n",
            encoding="utf-8",
        )
        compile_result = subprocess.run(
            [msbuild, "Checker.csproj", "/p:Configuration=Debug", "/nologo", "/v:m"],
            cwd=checker, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=300,
        )
        check("检查程序构建", compile_result.returncode == 0,
              (compile_result.stdout + compile_result.stderr)[-500:])
        exe = checker / "bin" / "Debug" / "Checker.exe"
        if exe.is_file():
            run = subprocess.run(
                [str(exe)], cwd=checker, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60,
            )
            print(run.stdout)
            check("NormalizeName 行为", run.returncode == 0, run.stderr[-300:])
        else:
            check("检查程序可执行", False, str(exe))

    print("独立验收：", "PASS" if not FAILS else f"FAIL {len(FAILS)} 项")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
