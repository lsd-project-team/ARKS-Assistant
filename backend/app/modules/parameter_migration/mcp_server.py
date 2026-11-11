"""通过 stdio 提供固定版本工艺确认清单的只读查询。"""

import argparse
import re
import unicodedata
from collections import Counter
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Annotated

from mcp.server import MCPServer
from mcp_types import ToolAnnotations
from openpyxl import load_workbook
from pydantic import Field

WORKBOOK_NAME = "传输字段保护默认状态工艺确认表.xlsx"
WORKBOOK_SHA256 = "51161cf93f2b191ef9432f56dcf9b466fdcfc0c560bd92c09867117d89255763"
SHEET = "工艺确认清单"
HEADERS = (
    "库",
    "字段名",
    "默认保护",
    "类别",
    "中文说明",
    "工艺确认（可改，填 是/否）",
    "与程序现状是否一致",
    "备注",
)
ROW_COUNT = 535
DISPENSING_LIBRARIES = {"Dispenser", "EpoxyApplication"}
DISPENSING_ALIASES = {"点胶", "点胶模块", "点胶参数", "点胶相关参数", "点胶相关"}
FIELD_ALIASES = {
    "点胶正压": {"EpoxyApplication.DispensePressure"},
    "点胶负压": {"EpoxyApplication.Vacuum"},
    "点胶压力": {"EpoxyApplication.DispensePressure", "EpoxyApplication.Vacuum"},
}
DECISION_LABELS = {
    "recipe_shared": "按原表可随配方跨设备下发",
    "protected": "程序登记一致，按原表保护规则不直接复用源机值",
    "pending": "暂不能确认直接复用",
}


def load_rules(path: Path) -> list[tuple[int, tuple[str | None, ...]]]:
    data = path.read_bytes()
    if sha256(data).hexdigest() != WORKBOOK_SHA256:
        raise ValueError("工作簿与原 535 条基准文件的 SHA-256 不一致")
    book = load_workbook(BytesIO(data), read_only=True)
    try:
        raw_rows = book[SHEET].values
        next(raw_rows)
        next(raw_rows)
        if next(raw_rows) != HEADERS:
            raise ValueError("工艺确认清单表头不符合原表")
        rows = list(enumerate(raw_rows, start=4))
        if len(rows) != ROW_COUNT or len({values[:2] for _, values in rows}) != ROW_COUNT:
            raise ValueError("工艺确认清单的行数或库名与字段名组合不符合原表")
        return rows
    finally:
        book.close()


def normalize(value: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value).casefold())


def is_dispensing(cells) -> bool:
    return cells[0] in DISPENSING_LIBRARIES or "点胶" in cells[4]


def find_rules(rows, query: str, library: str):
    query = normalize(query)
    library = normalize(library)
    if library in DISPENSING_ALIASES:
        candidates = [(row, cells) for row, cells in rows if is_dispensing(cells)]
    elif library:
        candidates = [(row, cells) for row, cells in rows if normalize(cells[0]) == library]
        if not candidates:
            return "unknown_library", []
    else:
        candidates = rows
    if query in DISPENSING_ALIASES:
        return "group", [(row, cells) for row, cells in candidates if is_dispensing(cells)]
    if query in {normalize(cells[0]) for _, cells in candidates}:
        return "group", [(row, cells) for row, cells in candidates if normalize(cells[0]) == query]
    exact, partial = [], []
    for row, cells in candidates:
        key = f"{cells[0]}.{cells[1]}"
        terms = tuple(map(normalize, (key, cells[1], cells[4])))
        if query in terms or key in FIELD_ALIASES.get(query, ()):
            exact.append((row, cells))
        elif any(query in term for term in terms):
            partial.append((row, cells))
    return ("exact", exact) if exact else ("partial", partial)


def decision_for(cells) -> tuple[str, str, str]:
    protection, category, confirmed, registration = (cells[index] for index in (2, 3, 5, 6))
    # 原表将默认保护、工艺确认与程序对照分开，冲突和未登记不能被默认值覆盖。
    if registration != "一致":
        detail = "需核对该字段的工艺确认和目标机程序保护登记。"
        if "未找到" in registration:
            detail = "需先核对目标机软件版本及对应字段，再确认保护登记和工艺要求。"
        if protection == "是":
            detail += "按原表的默认保护计划，应保留目标机值。"
        return "pending", "暂不能确认直接复用", detail
    if confirmed == "是" or (not confirmed and protection == "是"):
        action = {
            "机器参数·坐标": "核对目标机坐标或现场示教结果。",
            "机器参数·标定": "使用目标机自己的标定结果。",
            "设备专属": "核对目标机硬件和配置。",
            "示教状态": "使用目标机的现场示教状态。",
            "运行时": "使用目标机的运行状态。",
        }.get(category, "使用目标机已有值。")
        return "protected", "按原表保护规则不直接复用源机值", action
    if category == "配方共用":
        return (
            "recipe_shared",
            "按原表可随配方跨设备下发",
            "用于具体两台设备时，需核对目标机的产品、工艺或配置是否适用。",
        )
    return "pending", "暂不能确认直接复用", "需补充工艺确认或该参数在目标机上的适用依据。"


def rule_result(row: int, cells) -> dict:
    code, conclusion, condition = decision_for(cells)
    return {
        "parameter": f"{cells[0]}.{cells[1]}",
        "decision": code,
        "conclusion": conclusion,
        "target_check": condition,
        "source": f"{WORKBOOK_NAME} / {SHEET}!A{row}:H{row}（第 {row} 行）",
        "excel_row": row,
        "original_cells": dict(zip(HEADERS, cells, strict=True)),
    }


def create_server(path: Path) -> MCPServer:
    rows = load_rules(path)
    server = MCPServer("ZX2200 参数复用 MCP")

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False))
    def lookup(
        query: Annotated[str, Field(min_length=1, max_length=120)],
        library: Annotated[str, Field(max_length=100)] = "",
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=12)] = 8,
    ) -> dict:
        """回答 ZX2200 参数迁移、能否直接复用、下发或覆盖目标机、默认传输保护等问题。

        此工具是原 535 条 Excel 规则的查询入口，回答这类问题时先调用。query 传参数中文名、
        程序字段名、库.字段名、库名或“点胶”。library 可填准确库名或点胶模块。原表依据必须向用户
        引用工作表名和实际 Excel 行号，并说明原始默认保护、类别和登记状态。工艺确认空白
        就说明尚未填写。回答首句沿用结果的 conclusion，紧接 target_check，避免改变确定性。
        pending 的首句是“暂不能确认直接复用”，不要写成“不能直接复用”或“可以直接复用”。
        recipe_shared 是配方规则，指定目标机仍需核对条件。ambiguous 按各项结论说明同名差异，
        不替用户选库。unknown_library 或 scoped_not_found 先去掉 library 重查。全表
        not_found 回答“原清单未覆盖，暂不能判断能否直接复用”，不要推断该
        字段是否存在或能否传输，也不要用其他字段充当本题依据。按原清单回答时无需查源码。
        模块汇总直接采用 decision_summary（全部匹配项）。其中待确认也可能默认保护为“是”，
        不把 protected 的数量当作默认保护总数。按需用 next_offset 继续取明细。
        单条复用问答简短回答：先写结论和核对事项，再写原表的默认保护、类别、程序登记状态及
        行号，到此结束。原表记录不能写成实机验证、传输承诺或修改原表和程序的要求。
        """
        if not normalize(query):
            raise ValueError("请输入参数名称或模块名称")
        match, found = find_rules(rows, query, library)
        if not found and match != "unknown_library":
            match = "scoped_not_found" if normalize(library) else "not_found"
        elif match != "group" and len(found) > 1:
            match = "ambiguous"
        page = found[offset : offset + limit]
        summary = Counter(decision_for(cells)[0] for _, cells in found)
        conclusion = {
            "not_found": "原清单未覆盖，暂不能判断能否直接复用",
            "ambiguous": "清单中匹配多个字段，需结合库和字段名核对",
            "unknown_library": "没有匹配的库名，请去掉库筛选重查",
            "scoped_not_found": "指定范围内没有匹配项，可去掉库筛选查询整张表",
        }.get(match)
        if match == "ambiguous" and set(summary) == {"protected", "pending"}:
            conclusion = "匹配多个字段。部分按原表规则保护，其余暂不能确认直接复用，需核对所属库。"
        if len(found) == 1 and match != "group":
            conclusion = decision_for(found[0][1])[1]
        return {
            "dataset": {
                "file": WORKBOOK_NAME,
                "sheet": SHEET,
                "row_count": ROW_COUNT,
                "sha256": WORKBOOK_SHA256,
            },
            "query": query,
            "match": match,
            "conclusion": conclusion,
            "total_matches": len(found),
            "summary": dict(summary),
            "decision_summary": {DECISION_LABELS[code]: count for code, count in summary.items()},
            "default_protection_counts": dict(Counter(cells[2] for _, cells in found)),
            "next_offset": offset + limit if offset + limit < len(found) else None,
            "items": [rule_result(row, cells) for row, cells in page],
        }

    return server


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", required=True, type=Path)
    create_server(parser.parse_args().workbook).run(transport="stdio")
