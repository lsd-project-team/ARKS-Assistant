"""聊天参考文档只提取内容，不执行宏、公式、源码或压缩包。"""

import csv
import io
import json
import zipfile
from pathlib import PurePosixPath

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from app.modules.handover.infrastructure.parsers.archive import MAX_EXPANDED, safe_archive
from app.modules.handover.infrastructure.parsers.docx import parse_docx
from app.modules.handover.infrastructure.parsers.pdf import parse_pdf
from app.modules.source_analysis.workspace import decode_source

MAX_UPLOAD = 32 * 1024 * 1024
MAX_CONTENT = 1_000_000
MAX_ATTACHMENTS = 10
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".cs",
    ".cpp",
    ".c",
    ".h",
    ".json",
    ".yaml",
    ".yml",
    ".xml",
    ".ini",
    ".log",
}
EXTENSIONS = TEXT_EXTENSIONS | {".docx", ".pdf", ".zip", ".xlsx", ".csv"}


def filename_for(filename):
    name = PurePosixPath(filename.replace("\\", "/")).name
    if not name or len(name) > 250 or any(ord(char) < 32 for char in name):
        raise ValueError("文件名为空、过长或含控制字符")
    if PurePosixPath(name).suffix.lower() not in EXTENSIONS:
        raise ValueError("支持 DOCX、文本 PDF、XLSX、CSV、ZIP 和常见文本文件；DOC 请转 DOCX")
    return name


class AttachmentLimitError(ValueError):
    """整体资源超限必须拒绝，不能当作单个坏文件跳过。"""


class TextParts:
    def __init__(self):
        self.parts, self.size = [], 0

    def add(self, text):
        self.size += len(text) + 1
        if self.size > MAX_CONTENT:
            raise AttachmentLimitError("文档提取正文超过 100 万字，请按功能范围拆分后上传")
        self.parts.append(text)

    def text(self):
        return "\n".join(self.parts)


def parse_spreadsheet(data, extension):
    parts = TextParts()
    if extension == ".csv":
        text, _ = decode_source(data)
        try:
            dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        try:
            for index, row in enumerate(csv.reader(io.StringIO(text), dialect), 1):
                if index > 20000 or len(row) > 2000:
                    raise ValueError("表格超过 20000 行或 2000 列，请拆分后上传")
                parts.add(f"[行 {index}] " + json.dumps(row, ensure_ascii=False))
        except csv.Error as error:
            raise ValueError("CSV 内容无法解析或单元格过长") from error
        return parts.text(), "readable", "保留行号和列顺序；未执行公式。"
    # 先检查解压体积和路径，再让 openpyxl 读取；不接受宏工作簿或外部链接。
    with safe_archive(data):
        pass
    try:
        with io.BytesIO(data) as source, io.BytesIO(data) as cached_source:
            workbook = load_workbook(source, read_only=True, data_only=False, keep_links=False)
            cached = None
            try:
                cached = load_workbook(
                    cached_source, read_only=True, data_only=True, keep_links=False
                )
                count = 0
                for sheet in workbook:
                    if (sheet.max_row or 0) > 20000 or (sheet.max_column or 0) > 2000:
                        raise ValueError("工作表超过 20000 行或 2000 列，请拆分后上传")
                    parts.add(f"[工作表 {sheet.title!r}，状态 {sheet.sheet_state}]")
                    if (sheet.max_row or 0) * (sheet.max_column or 0) > 1_000_000:
                        raise ValueError("工作表范围超过 100 万个单元格，请缩小有效范围")
                    for row, values in zip(
                        sheet.iter_rows(), cached[sheet.title].iter_rows(), strict=True
                    ):
                        cells = []
                        for column, (cell, value) in enumerate(zip(row, values, strict=True), 1):
                            if cell.value is None:
                                continue
                            count += 1
                            if count > 100000:
                                raise ValueError("工作簿超过 100000 个非空单元格，请拆分后上传")
                            address = f"{get_column_letter(column)}{cell.row}"
                            content = str(cell.value)
                            if cell.data_type == "f":
                                content += f"（公式缓存值：{value.value!r}；未重新计算）"
                            cells.append(f"{address}={content}")
                        if cells:
                            parts.add(" | ".join(cells))
                if not count:
                    raise ValueError("工作簿没有非空单元格")
            finally:
                workbook.close()
                if cached:
                    cached.close()
    except ValueError:
        raise
    except Exception as error:
        raise ValueError("Excel 无法解析，请使用未加密的 XLSX 文件") from error
    return (
        parts.text(),
        "readable",
        "按工作表、单元格位置读取；公式保留原式及已有缓存值，未重新计算。图片和图表未解析。",
    )


def include_office_expansion(data, expanded, entries):
    # DOCX/XLSX 自身也是压缩包，其内部展开量必须计入外层 ZIP 的总预算。
    with safe_archive(data) as document:
        members = document.infolist()
        expanded += sum(item.file_size for item in members)
        entries += len(members)
    if expanded > MAX_EXPANDED or entries > 2000:
        raise AttachmentLimitError(
            "ZIP 含 Office 文档展开后累计超过 64 MB 或 2000 项，请拆分后上传"
        )
    return expanded, entries


def parse_zip(data):
    parts, skipped, partial, read = TextParts(), [], [], 0
    with safe_archive(data) as archive:
        members = archive.infolist()
        expanded, entries = sum(item.file_size for item in members), len(members)
        for item in members:
            if item.is_dir():
                continue
            path = item.filename.replace("\\", "/")
            extension = PurePosixPath(path).suffix.lower()
            # 仅解析一层文件；Office 内部结构交给原解析器，不递归展开嵌套 ZIP。
            if extension not in EXTENSIONS - {".zip"}:
                skipped.append(f"{path}（格式暂不支持，嵌套 ZIP 不递归读取）")
                continue
            limit = 2_000_000 if extension in TEXT_EXTENSIONS else MAX_UPLOAD
            if item.file_size > limit:
                label = "文本超过 2 MB" if extension in TEXT_EXTENSIONS else "文件超过 32 MB"
                skipped.append(f"{path}（{label}）")
                continue
            try:
                member_data = archive.read(item)
                if extension in {".docx", ".xlsx"}:
                    expanded, entries = include_office_expansion(member_data, expanded, entries)
                _, content, status, notes = parse_attachment(member_data, path)
            except AttachmentLimitError:
                raise
            except (ValueError, zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
                skipped.append(f"{path}（解析失败：{error}）")
                continue
            parts.add(f"[文件 {path}]\n[解析说明] {notes}\n{content}")
            if status == "partial":
                partial.append(path)
            read += 1
    notes = f"读取 {read} 个文件；未解压到工程、未执行内容。"
    if partial:
        notes += " 部分可读的文件：" + ", ".join(partial[:30])
        if len(partial) > 30:
            notes += f"等 {len(partial)} 项"
    if skipped:
        notes += " 未读取的文件：" + ", ".join(skipped[:30])
        if len(skipped) > 30:
            notes += f"等 {len(skipped)} 项"
    if not read:
        raise ValueError("ZIP 中没有可读取的文档、源码或文本文件。" + notes)
    return parts.text(), "partial" if skipped or partial else "readable", notes


def parse_attachment(data, filename):
    try:
        return _parse_attachment(data, filename)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        raise ValueError("压缩文档损坏或使用不支持的压缩方式，请重新导出后上传") from error


def _parse_attachment(data, filename):
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError("文件不能为空且单个文件不能超过 32 MB")
    filename = filename_for(filename)
    extension = PurePosixPath(filename).suffix.lower()
    if extension in {".xlsx", ".csv"}:
        content, status, notes = parse_spreadsheet(data, extension)
    elif extension == ".zip":
        content, status, notes = parse_zip(data)
    elif extension in {".pdf", ".docx"}:
        parser = parse_pdf if extension == ".pdf" else parse_docx
        try:
            content, status, notes, _ = parser(data)
        except ValueError:
            raise
        except Exception as error:
            raise ValueError("文档损坏或无法解析，请重新导出后上传") from error
        if status == "needs_ocr":
            raise ValueError("文档没有可提取文字，请使用文本版文档；扫描件和图片识别暂未接入")
    else:
        text, _ = decode_source(data)
        if not text.strip():
            raise ValueError("文档没有可读取的内容")
        content = "\n".join(f"[L{index}] {line}" for index, line in enumerate(text.splitlines(), 1))
        status, notes = "readable", "按行号读取；未执行文件内容。"
    if not content.strip():
        raise ValueError("文档没有可读取的内容")
    if len(content) > MAX_CONTENT:
        raise AttachmentLimitError("文档提取正文超过 100 万字，请按功能范围拆分后上传")
    return filename, content, status, notes
