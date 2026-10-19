"""从只读源码建立网格边界验收案例；不调用模型、不修改业务原件。"""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = "AKRS.ZX2200/Infrastructure/Utils/MathAdvanceHelper.cs"
CALLER = "AKRS.ZX2200/CalibSystem/GlobalCalibration/BondCompensateCalibration.cs"

PROJECT = """<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType><TargetFramework>net8.0</TargetFramework>
    <LangVersion>7.3</LangVersion><ImplicitUsings>disable</ImplicitUsings>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <UseAppHost>false</UseAppHost><NuGetAudit>false</NuGetAudit>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="MathAdvanceHelper.cs" />
    <Compile Include="DataTypes.cs" /><Compile Include="Program.cs" />
  </ItemGroup>
</Project>
"""

# 原方法只访问点的X/Y和构造函数。私有点类型不可在此替代为完整SDK验证。
DATA_TYPES = """namespace AKRS.Base { internal class NamespacePlaceholder {} }
namespace AKRS.Galaxy2.Infrastructure.CommonModel
{
    public class AKRSPoint2D
    {
        public double X { get; set; }
        public double Y { get; set; }
        public AKRSPoint2D(double x, double y) { X = x; Y = y; }
    }
    public class AKRSPoint3D
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public AKRSPoint3D(double x, double y, double z) { X = x; Y = y; Z = z; }
    }
}
"""

PROGRAM = """using System;
using System.Collections.Generic;
using System.Text.Json;
using AKRS.Galaxy2.Infrastructure.CommonModel;
using AKRS.ZX2200.Infrastructure.Utils;

class Program
{
    static int Main()
    {
        var grid = new AKRSPoint2D[2, 3];
        for (int row = 0; row < 2; row++)
            for (int column = 0; column < 3; column++)
                grid[row, column] = new AKRSPoint2D(100 + column, 200 + row);
        var origin = new AKRSPoint3D(10, 20, 999);
        var cases = new[] {
            new { name="minimum_corner", x=10.0, y=20.0, expectedX=100.0, expectedY=200.0 },
            new { name="first_cell", x=10.2, y=20.2, expectedX=100.0, expectedY=200.0 },
            new { name="last_cell_nonsquare", x=15.5, y=25.5, expectedX=102.0, expectedY=201.0 },
            new { name="inner_grid_line", x=12.0, y=23.0, expectedX=101.0, expectedY=201.0 },
            new { name="outside_left", x=9.0, y=21.0, expectedX=9.0, expectedY=21.0 },
            new { name="outside_bottom", x=11.0, y=19.0, expectedX=11.0, expectedY=19.0 },
            new { name="outside_right", x=16.1, y=21.0, expectedX=16.1, expectedY=21.0 },
            new { name="outside_top", x=11.0, y=26.1, expectedX=11.0, expectedY=26.1 },
            new { name="exact_right", x=16.0, y=20.5, expectedX=16.0, expectedY=20.5 },
            new { name="exact_top", x=10.5, y=26.0, expectedX=10.5, expectedY=26.0 },
            new { name="exact_upper_corner", x=16.0, y=26.0, expectedX=16.0, expectedY=26.0 }
        };
        var results = new List<object>();
        int passed = 0;
        foreach (var item in cases)
        {
            try
            {
                var result = MathAdvanceHelper.PlaneInterpolate(item.x, item.y, grid, origin, 2, 3);
                bool ok = result.X == item.expectedX && result.Y == item.expectedY;
                if (ok) passed++;
                results.Add(new { item.name, ok, actualX=result.X, actualY=result.Y, error="" });
            }
            catch (Exception error)
            {
                results.Add(new { item.name, ok=false, error=error.GetType().Name });
            }
        }
        Console.WriteLine("GRID_CASE:" + JsonSerializer.Serialize(
            new { total=cases.Length, passed, failed=cases.Length-passed, results }));
        return passed == cases.Length ? 0 : 1;
    }
}
"""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_case(destination):
    from .code_work_quality.safety import checked_path

    destination = checked_path(destination)
    source, caller = ROOT / "trunk" / SOURCE, ROOT / "trunk" / CALLER
    for path in (source, caller):
        for current in (path, *path.parents):
            if current.is_symlink() or current.is_junction():
                raise ValueError("案例输入不能包含链接")
        if not path.is_file() or path.stat().st_nlink != 1:
            raise ValueError("案例输入必须是普通单链接文件")
    content = source.read_bytes()
    # 对照仅证明新需求可执行，不替代模型解题；只生成独立测试副本。
    replacements = {
        "x > startPos.X +": "x >= startPos.X +",
        "y > startPos.Y +": "y >= startPos.Y +",
    }
    control = content
    for before, after in replacements.items():
        if control.count(before.encode()) != 1:
            raise ValueError("源码守卫已变化，请重新审阅案例，不自动猜测补丁")
        control = control.replace(before.encode(), after.encode())
    destination.mkdir(parents=True, exist_ok=False)
    for variant in ("original", "reference-control"):
        folder = destination / variant
        folder.mkdir()
        (folder / "Case.csproj").write_text(PROJECT, encoding="utf-8")
        (folder / "Program.cs").write_text(PROGRAM, encoding="utf-8")
        (folder / "DataTypes.cs").write_text(DATA_TYPES, encoding="utf-8")
        (folder / "NuGet.Config").write_text(
            "<configuration><packageSources><clear /></packageSources></configuration>",
            encoding="utf-8",
        )
        if variant == "original":
            (folder / "MathAdvanceHelper.cs").write_bytes(content)
        else:
            (folder / "MathAdvanceHelper.cs").write_bytes(control)
    record = {
        "schema_version": 1,
        "source": SOURCE,
        "source_sha256": hashlib.sha256(content).hexdigest(),
        "caller": CALLER,
        "caller_sha256": digest(caller),
        "cases": 11,
        "requirement": "右/上边界按范围外返回输入坐标，正常网格单元行为保持不变",
        "limits": "只验证索引和返回值；点类为测试替身，未验证私有DLL和.NET4.8全工程",
        "external_model_called": False,
    }
    (destination / "case.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    suite = {
        "schema_version": 1,
        "id": "calibration-grid-boundary-v1",
        "cases": [
            {
                "id": "calibration-grid-boundary",
                "kind": "change",
                "question": (
                    "请用read_source核对MathAdvanceHelper.cs的PlaneInterpolate。"
                    "合成网格为2行3列，起点(10,20)，X/Y间距分别为2和3；"
                    "精确右界x=16、上界y=26及右上角应按范围外返回输入坐标。"
                    "请定位原方法的边界异常，并在隔离副本修复；正常单元及已有范围外行为保持不变。"
                    "验收标准：Program.cs全部11例通过；仅修改MathAdvanceHelper.cs，"
                    "不修改测试、点值替身、工程文件或原件，不重写成其他插值算法。"
                    "读取并引用原件，报告修改ID、差异及实际验证结果；"
                    "没有执行命令时保留未验证，不能把.NET8单位方法测试说成.NET4.8全工程构建。"
                ),
                "expected_sources": {
                    "MathAdvanceHelper.cs": record["source_sha256"],
                    "Program.cs": digest(destination / "original/Program.cs"),
                },
                "rubric": {
                    "cause": "解释精确上界对应索引等于数组长度，不把函数名当已实现完整插值",
                    "change": "边界按需求处理，正常单元及已有范围外行为不变，只改指定方法文件",
                    "evidence": "引用当前原件及固定修改，原件保持不变，不以未执行命令冒充验证",
                    "limits": "明确点值替身、.NET8及未验证私有DLL/设备/工艺边界",
                },
            }
        ],
    }
    (destination / "cases.json").write_text(
        json.dumps(suite, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if (
        digest(source) != record["source_sha256"]
        or digest(caller) != record["caller_sha256"]
    ):
        raise ValueError("准备期间原件发生变化，案例不能作为当前版本依据")
    return record


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "backend"))
    if len(sys.argv) != 2:
        raise SystemExit(
            "用法：python -m scripts.verification.calibration_grid_case <新目录>"
        )
    print(json.dumps(create_case(Path(sys.argv[1])), ensure_ascii=False))
