"""构建诊断解析：MSBuild 文件行号诊断、中英文汇总与测试计数。"""

from app.modules.coding.diagnostics import parse_diagnostics, parse_tests

OUTPUT = """
C:\\project\\Program.cs(10,5): error CS1002: 应输入 ; [C:\\project\\App.csproj]
C:\\project\\MainForm.cs(20,9): warning CS0168: 变量已声明但从未使用 [C:\\project\\App.csproj]
MSBUILD : error MSB1009: 项目文件不存在。
    0 个警告
    1 个错误
"""

CLEAN = """
  正在确定要还原的项目...
  所有项目均是最新的，无法还原。
  App -> C:\\project\\bin\\Debug\\net8.0-windows\\App.dll

生成成功。
    0 个警告
    0 个错误
"""


def test_parse_file_diagnostics_and_chinese_summary():
    result = parse_diagnostics(OUTPUT, 1)
    assert result["ok"] is False
    assert result["error_count"] == 2
    assert result["warning_count"] == 1
    assert {row["code"] for row in result["errors"]} == {"CS1002", "MSB1009"}
    error = next(row for row in result["errors"] if row["code"] == "CS1002")
    assert error["file"].endswith("Program.cs")
    assert (error["line"], error["column"]) == (10, 5)
    assert "错误 1" in result["summary"] and "警告 0" in result["summary"]


def test_clean_build_is_ok():
    result = parse_diagnostics(CLEAN, 0)
    assert result["ok"] is True
    assert result["error_count"] == 0 and result["warning_count"] == 0
    assert "错误 0" in result["summary"] and "警告 0" in result["summary"]


def test_english_summary():
    output = "Build succeeded.\n    2 Warning(s)\n    0 Error(s)\n"
    result = parse_diagnostics(output, 0)
    assert result["ok"] is True
    assert "警告 2" in result["summary"]


def test_timeout_and_test_counts():
    assert "超时" in parse_diagnostics("", -1)["summary"]
    tests = parse_tests(
        "PASS 1\nPASS 2\n16 passed, 1 failed in 3.2s\n", 1
    )
    assert tests == {"passed": 16, "failed": 1, "ok": False}
    assert parse_tests("16 passed\n", 0)["ok"] is True


def test_chinese_self_test_output_is_counted():
    output = "\n".join(
        [f"[PASS] {index}. 用例" for index in range(1, 14)] + ["通过 13 项，失败 0 项。"]
    )
    counts = parse_tests(output, 0)
    assert counts["passed"] == 13 and counts["failed"] == 0 and counts["ok"] is True


def test_fail_lines_and_short_fail_summary_are_counted():
    output = (
        "[PASS] 基础解析\n[PASS] 等级过滤\n[FAIL] 空文件 -> 应为 0\n\n"
        "自测结果: 7 PASS, 1 FAIL, 共 8 项\n"
    )
    counts = parse_tests(output, 1)
    assert counts["passed"] == 7 and counts["failed"] == 1 and counts["ok"] is False
