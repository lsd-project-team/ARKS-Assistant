"""构建/测试输出解析：把 MSBuild、dotnet、pytest 的输出变成结构化诊断。"""

import re

FILE_DIAGNOSTIC = re.compile(
    r"^(?P<file>[A-Za-z]:[^\r\n(]+|[^\r\n(]+)\((?P<line>\d+),(?P<column>\d+)\):\s*"
    r"(?P<severity>error|warning)\s+(?P<code>[A-Z]+[0-9]+):\s*"
    r"(?P<message>.+?)(?:\s+\[[^\]]+\])?\s*$",
    re.MULTILINE,
)
GENERIC_DIAGNOSTIC = re.compile(
    r"(?:^|\s)(?P<severity>error|warning)\s+(?P<code>[A-Z]+[0-9]+):\s*(?P<message>.+?)\s*$",
    re.MULTILINE,
)
ENGLISH_SUMMARY = re.compile(
    r"(?P<errors>\d+)\s+Error\(s\)|(?P<warnings>\d+)\s+Warning\(s\)", re.IGNORECASE
)
CHINESE_SUMMARY = re.compile(r"(?P<count>\d+)\s*个(?:错误|警告)")
TEST_PASSED = re.compile(r"(?P<count>\d+)[ \t]+(?:passed|pass\b|通过)", re.IGNORECASE)
TEST_FAILED = re.compile(r"(?P<count>\d+)[ \t]+(?:failed|fail\b|失败)", re.IGNORECASE)
CHINESE_PASSED = re.compile(r"通过\s*(?P<count>\d+)\s*项")
CHINESE_FAILED = re.compile(r"失败\s*(?P<count>\d+)\s*项")
PASS_LINE = re.compile(r"^\s*\[?PASS\]?(?:\s|:|：)", re.MULTILINE | re.IGNORECASE)
FAIL_LINE = re.compile(r"^\s*\[?FAIL\]?(?:\s|:|：)", re.MULTILINE | re.IGNORECASE)
TAP_PASS = re.compile(r"^(?:#|ℹ)\s*pass\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)
TAP_FAIL = re.compile(r"^(?:#|ℹ)\s*fail\s+(\d+)\s*$", re.MULTILINE | re.IGNORECASE)


def parse_diagnostics(output, exit_code=0):
    """优先取带文件行号的诊断；同一诊断只保留一次。"""
    found, seen = [], set()
    for match in FILE_DIAGNOSTIC.finditer(output):
        row = {
            "file": match.group("file").strip(),
            "line": int(match.group("line")),
            "column": int(match.group("column")),
            "severity": match.group("severity"),
            "code": match.group("code"),
            "message": match.group("message").strip(),
        }
        key = (row["file"], row["line"], row["column"], row["code"], row["message"])
        if key not in seen:
            seen.add(key)
            found.append(row)
    covered = {row["code"] for row in found}
    for match in GENERIC_DIAGNOSTIC.finditer(output):
        if match.group("code") in covered:
            continue
        row = {
            "file": "",
            "line": 0,
            "column": 0,
            "severity": match.group("severity"),
            "code": match.group("code"),
            "message": match.group("message").strip(),
        }
        key = (row["code"], row["message"])
        if key not in seen:
            seen.add(key)
            found.append(row)
    errors = [row for row in found if row["severity"] == "error"]
    warnings = [row for row in found if row["severity"] == "warning"]
    return {
        "ok": exit_code == 0 and not errors,
        "errors": errors,
        "warnings": warnings,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "summary": _summary(output, exit_code, len(errors), len(warnings)),
    }


def _summary(output, exit_code, errors, warnings):
    if exit_code < 0:
        return "命令超时或被取消"
    parts = []
    for match in ENGLISH_SUMMARY.finditer(output):
        if match.group("errors") is not None:
            parts.append(f"错误 {match.group('errors')}")
        elif match.group("warnings") is not None:
            parts.append(f"警告 {match.group('warnings')}")
    if not parts:
        for match in CHINESE_SUMMARY.finditer(output):
            label = "错误" if "错误" in match.group(0) else "警告"
            parts.append(f"{label} {match.group('count')}")
    if parts:
        return f"退出码 {exit_code}；" + "，".join(dict.fromkeys(parts))
    return f"退出码 {exit_code}；错误 {errors}，警告 {warnings}"


def parse_tests(output, exit_code):
    passed = sum(int(item) for item in TEST_PASSED.findall(output))
    failed = sum(int(item) for item in TEST_FAILED.findall(output))
    chinese_passed = sum(int(item) for item in CHINESE_PASSED.findall(output))
    chinese_failed = sum(int(item) for item in CHINESE_FAILED.findall(output))
    lines = len(PASS_LINE.findall(output))
    failed_lines = len(FAIL_LINE.findall(output))
    tap_passed = sum(int(item) for item in TAP_PASS.findall(output))
    tap_failed = sum(int(item) for item in TAP_FAIL.findall(output))
    passed = max(passed, chinese_passed, lines, tap_passed)
    failed = max(failed, chinese_failed, failed_lines, tap_failed)
    return {
        "passed": passed,
        "failed": failed,
        "ok": exit_code == 0 and failed == 0 and passed > 0,
    }


def tail(output, limit=4000):
    text = output or ""
    return text[-limit:]
