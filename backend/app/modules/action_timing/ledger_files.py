"""读写用户台账文件；只处理数据，不执行公式或外部链接。"""

import csv
import io
import zipfile
from pathlib import PurePath

from openpyxl import Workbook, load_workbook
from pydantic import ValidationError

from app.modules.action_timing.ledger_schemas import MAX_FILE_BYTES, MAX_ROWS, ImportRow, name_key

HEADERS = ("分类", "动作名称", "耗时（秒）", "备注")
DURATION_HEADERS = {
    name_key(label): unit
    for label, unit in (
        ("耗时（秒）", "s"),
        ("耗时（s）", "s"),
        ("耗时（毫秒）", "ms"),
        ("耗时（ms）", "ms"),
        ("耗时", None),
    )
}
MEDIA = {
    "csv": "text/csv; charset=utf-8",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def read_rows(raw, filename, *, unit="auto"):
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("文件超过5MiB，请分批导入")
    suffix = PurePath(filename).suffix.lower()
    if suffix == ".csv":
        rows = _csv_rows(raw)
    elif suffix == ".xlsx":
        rows = _xlsx_rows(raw)
    else:
        raise ValueError("请选择CSV或Excel（.xlsx）文件")
    return _validate_rows(rows, unit=unit, csv_escaped=suffix == ".csv")


def _csv_rows(raw):
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text = raw.decode("gb18030")
        except UnicodeDecodeError as error:
            raise ValueError("CSV编码无法识别，请另存为UTF-8 CSV") from error
    try:
        return list(_limited(csv.reader(io.StringIO(text, newline=""), strict=True)))
    except csv.Error as error:
        raise ValueError("CSV格式错误，请使用导入模板") from error


def _xlsx_rows(raw):
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(item.file_size for item in entries) > 50 * 1024 * 1024:
                raise ValueError("Excel解压后过大，请缩小文件")
        workbook = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        try:
            sheet = workbook.worksheets[0]
            if (sheet.max_row or 0) > MAX_ROWS + 1 or (sheet.max_column or 0) > 20:
                raise ValueError("每次最多导入5000行，表格最多20列")
            result = []
            for cells in _limited(sheet.iter_rows()):
                if any(cell.data_type in {"f", "e"} for cell in cells):
                    raise ValueError("Excel包含公式或错误单元格，请先粘贴为数值后导入")
                result.append([cell.value for cell in cells])
            return result
        finally:
            workbook.close()
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("Excel文件无法读取，请使用有效的.xlsx文件") from error


def _limited(rows):
    for index, row in enumerate(rows):
        if index > MAX_ROWS:
            raise ValueError("每次最多导入5000行，请分批导入")
        yield row


def _text(value):
    return "" if value is None else str(value)


def _import_columns(headers, unit):
    if unit not in {"auto", "s", "ms"}:
        raise ValueError("耗时单位须为秒、毫秒或按表头识别")
    expected = [name_key(value) for value in (HEADERS[0], HEADERS[1], HEADERS[3])]
    durations = [value for value in headers if value in DURATION_HEADERS]
    if any(headers.count(value) != 1 for value in expected) or len(durations) != 1:
        raise ValueError(
            "表头须包含：分类、动作名称、耗时（秒）或耗时（毫秒）、备注；请下载导入模板"
        )
    duration_header = durations[0]
    if any(value and value not in {*expected, duration_header} for value in headers):
        raise ValueError("文件包含模板之外的列，请仅保留分类、动作名称、耗时、备注")
    header_unit = DURATION_HEADERS[duration_header]
    if header_unit and unit != "auto" and header_unit != unit:
        raise ValueError("所选耗时单位与表头不一致，请选择按表头识别或修改表头")
    resolved = header_unit if unit == "auto" else unit
    if resolved is None:
        raise ValueError("耗时列未标明单位，请选择秒或毫秒后重新预览")
    positions = [
        headers.index(value) for value in (expected[0], expected[1], duration_header, expected[2])
    ]
    return positions, resolved


def _validate_rows(rows, *, unit="auto", csv_escaped=False):
    if not rows:
        raise ValueError("文件为空，请先下载并填写模板")
    headers = [name_key(str(value or "")) for value in rows[0]]
    positions, source_unit = _import_columns(headers, unit)
    valid, errors = [], []
    for number, row in enumerate(rows[1:], 2):
        if not any(value is not None and str(value).strip() for value in row):
            continue
        if any(
            value is not None and str(value).strip()
            for position, value in enumerate(row)
            if position not in positions
        ):
            errors.append({"row_number": number, "message": "存在没有表头的数据列，请按模板整理"})
            continue
        values = [row[position] if position < len(row) else None for position in positions]
        category, name, duration, notes = values
        category, name, notes = (
            restore_csv_text(_text(value)) if csv_escaped else _text(value)
            for value in (category, name, notes)
        )
        try:
            item = ImportRow(
                row_number=number,
                category=category,
                name=name,
                duration_seconds=None
                if duration is None or _text(duration).strip() == ""
                else duration,
                notes=notes,
            )
            if source_unit == "ms" and item.duration_seconds is not None:
                # 仅预览解析时换算一次；确认接口收到的行与台账存储均为秒。
                seconds = item.duration_seconds / 1000
                if item.duration_seconds and seconds == 0:
                    raise ValueError("耗时过小，换算为秒后超出可保存范围")
                item.duration_seconds = seconds
            valid.append(item)
        except ValidationError as error:
            labels = {
                "name": "动作名称",
                "category": "分类",
                "duration_seconds": "耗时",
                "notes": "备注",
            }
            detail = "；".join(
                f"{labels.get(item['loc'][0], item['loc'][0])}：{item['msg']}"
                for item in error.errors()
            )
            errors.append({"row_number": number, "message": detail})
        except ValueError as error:
            errors.append({"row_number": number, "message": str(error)})
    if not valid and not errors:
        raise ValueError("文件没有动作数据，请填写后再导入")
    return valid, errors


def export_file(items, format, *, unit="s"):
    if unit not in {"s", "ms"}:
        raise ValueError("耗时单位须为秒或毫秒")
    headers = (HEADERS[0], HEADERS[1], "耗时（毫秒）" if unit == "ms" else HEADERS[2], HEADERS[3])
    rows = [
        [
            row["category"],
            row["name"],
            row["duration_seconds"] * 1000
            if unit == "ms" and row["duration_seconds"] is not None
            else row["duration_seconds"],
            row["notes"],
        ]
        for row in items
    ]
    if format == "csv":
        output = io.StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([csv_text(value) if isinstance(value, str) else value for value in row])
        return ("\ufeff" + output.getvalue()).encode("utf-8")
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "动作耗时"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
        for cell in sheet[sheet.max_row]:
            if isinstance(cell.value, str):
                cell.data_type = "s"
    for key, width in (("A", 18), ("B", 30), ("C", 18), ("D", 50)):
        sheet.column_dimensions[key].width = width
    sheet.freeze_panes = "A2"
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def csv_text(value):
    # 带引号导出的文本在重导入时恢复，避免分类/名称被无意改名。
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@", "'")) else value


def restore_csv_text(value):
    if value.startswith("'") and value[1:].lstrip().startswith(("=", "+", "-", "@", "'")):
        return value[1:]
    return value
