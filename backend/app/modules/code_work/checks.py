"""需求测试配置与固定C#验证宿主；不接收Shell命令。"""

import json
import re
import struct
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from app.infrastructure.storage.files import digest
from app.modules.code_work.files import atomic_bytes

RESOURCES = Path(__file__).parent / "harness"


class RequirementWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(default="", pattern=r"^(|[a-f0-9]{32})$")
    version: str = Field(default="", max_length=64)
    name: str = Field(min_length=1, max_length=160)
    expectation: str = Field(min_length=1, max_length=2000)
    code: str = Field(min_length=1, max_length=30_000)
    enabled: bool = True


def validation_version(state):
    cases = [
        {key: item[key] for key in ("id", "name", "expectation", "code", "enabled")}
        for item in state.get("requirements", [])
    ]
    host = digest(b"".join(path.read_bytes() for path in sorted(RESOURCES.glob("*.cs"))))
    return digest(
        json.dumps(
            {"requirements": cases, "desktop": state.get("desktop_flow", False), "host": host},
            sort_keys=True,
        ).encode()
    )


def managed(file):
    """读取PE的CLR目录标识，避免把原生DLL误传给C#编译器。"""
    with file.open("rb") as stream:
        header = stream.read(64)
        if len(header) < 64 or header[:2] != b"MZ":
            return False
        stream.seek(struct.unpack_from("<I", header, 60)[0])
        header = stream.read(256)
    if header[:4] != b"PE\0\0" or len(header) < 256:
        return False
    magic = struct.unpack_from("<H", header, 24)[0]
    if magic not in {0x10B, 0x20B}:
        return False
    offset = 24 + (96 if magic == 0x10B else 112) + 14 * 8
    return bool(struct.unpack_from("<I", header, offset)[0])


def prepare_harness(root, output, state, compiler):
    csc = Path(compiler).parent / "Roslyn/csc.exe"
    if not csc.is_file():
        raise ValueError("MSBuild目录缺少Roslyn/csc.exe，不能编译需求与界面验证宿主")
    generated = root / "test-host"
    generated.mkdir()
    cases = [item for item in state.get("requirements", []) if item["enabled"]]
    methods, registrations = [], []
    for case in cases:
        if not re.fullmatch(r"[a-f0-9]{32}", case["id"]):
            raise ValueError("需求测试标识无效")
        method = "Case_" + case["id"]
        methods.append("static void " + method + "() {\n" + case["code"] + "\n}")
        registrations.append("{ " + json.dumps(case["id"]) + ", " + method + " }")
    code = (
        """using System; using System.Linq; using System.Collections.Generic;
using System.Reflection; using System.Threading; using System.Windows.Forms; using HarmonyLib;
using static CodeWork.Harness;
namespace CodeWork { internal static class RequirementCases {
internal static readonly Dictionary<string, Action> All = new Dictionary<string, Action> {
"""
        + ",\n".join(registrations)
        + "\n};\n"
        + "\n".join(methods)
        + "\n} }"
    )
    atomic_bytes(generated / "RequirementCases.cs", code.encode("utf-8-sig"))
    atomic_bytes(
        output / "code-work-cases.json", json.dumps(cases, ensure_ascii=False).encode("utf-8")
    )
    executable = output / "CodeWork.Harness.exe"
    references = [str(file) for file in sorted(output.glob("*.dll")) if managed(file)]
    references.append(str(output / "AKRS.ZX2200.exe"))
    arguments = [
        "/nologo",
        "/target:exe",
        "/langversion:latest",
        "/platform:anycpu",
        '/out:"' + str(executable) + '"',
        '/reference:"System.Windows.Forms.dll"',
        '/reference:"System.Drawing.dll"',
        '/reference:"System.Xml.dll"',
    ]
    arguments += ['/reference:"' + path + '"' for path in references]
    arguments += ['"' + str(path) + '"' for path in sorted(RESOURCES.glob("*.cs"))]
    arguments += ['"' + str(generated / "RequirementCases.cs") + '"']
    response = generated / "compile.rsp"
    atomic_bytes(response, "\n".join(arguments).encode("utf-8-sig"))
    config = output / "AKRS.ZX2200.exe.config"
    if config.is_file():
        atomic_bytes(output / "CodeWork.Harness.exe.config", config.read_bytes())
    return [str(csc), "@" + str(response)], executable


def read_report(path, kind, state):
    if not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError("验证报告缺失或超出大小限制")
    report = json.loads(path.read_text(encoding="utf-8-sig"))
    if report.get("kind") != kind or not isinstance(report.get("results"), list):
        raise ValueError("验证报告格式无效")
    rows = report["results"]
    if not rows or any(
        not isinstance(item, dict)
        or item.get("status") != "passed"
        or type(item.get("assertions")) is not int
        or item["assertions"] < 1
        for item in rows
    ):
        raise ValueError("存在失败或没有执行断言的检查")
    if kind == "requirements":
        expected = {item["id"] for item in state.get("requirements", []) if item["enabled"]}
        if {item.get("id") for item in rows} != expected or len(rows) != len(expected):
            raise ValueError("需求测试报告与本次用例不一致")
    elif [item.get("id") for item in rows] != [
        "loaded",
        "reset",
        "start",
        "pause",
        "continue",
        "production",
        "stop",
    ]:
        raise ValueError("桌面流程报告未完整覆盖固定步骤")
    if kind == "desktop":
        for index, row in enumerate(rows):
            name = f"code-work-ui-{index:02}.png"
            image = path.parent / name
            if (
                row.get("screenshot") != name
                or not image.is_file()
                or image.stat().st_size > 20_000_000
            ):
                raise ValueError("桌面步骤截图缺失或超出限制")
            data = image.read_bytes()
            if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
                raise ValueError("桌面步骤截图格式无效")
            width, height = struct.unpack_from(">II", data, 16)
            if not (200 <= width <= 5000 and 200 <= height <= 5000):
                raise ValueError("桌面步骤截图尺寸无效")
    return report
