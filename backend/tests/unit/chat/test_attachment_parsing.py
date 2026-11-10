import io
import zipfile

import pytest
from openpyxl import Workbook
from pypdf import PdfWriter

from app.modules.chat.attachment_parsing import (
    MAX_UPLOAD,
    TEXT_EXTENSIONS,
    parse_attachment,
)
from tests.helpers.chat_attachments import document_bytes


@pytest.mark.parametrize(
    "extension", sorted(TEXT_EXTENSIONS | {".docx", ".pdf", ".xlsx", ".csv", ".zip"})
)
def test_formats_extract_document_requirement_with_positions(extension):
    name, content, status, notes = parse_attachment(document_bytes(extension), f"需求{extension}")
    assert name == f"需求{extension}"
    assert "NewValue = 7" in content
    assert status == "readable" and notes
    if extension == ".docx":
        assert "[段落 1]" in content and "表格规则" in content
    elif extension == ".pdf":
        assert "[第 1 页]" in content
    elif extension == ".xlsx":
        assert "参数" in content and "A2=NewValue = 7" in content
        assert "B2=7" in content and "C2==B2+1" in content and "未重新计算" in content


@pytest.mark.parametrize(
    "filename,data",
    [
        ("old.doc", b"old"),
        ("run.exe", b"exe"),
        ("image.png", b"png"),
        ("empty.txt", b""),
        ("spaces.md", b"   \n "),
        ("binary.cs", b"\x00\x01"),
        ("broken.docx", b"not zip"),
        ("broken.pdf", b"not pdf"),
        ("large.txt", b"x" * (MAX_UPLOAD + 1)),
        ("long.txt", b"x" * 1_000_001),
        ("bad\n.txt", b"test"),
    ],
    ids=lambda value: value if isinstance(value, str) else "bytes",
)
def test_unsupported_invalid_or_oversized_files_are_rejected(filename, data):
    with pytest.raises(ValueError):
        parse_attachment(data, filename)


def test_csv_preserves_quoted_multiline_empty_cells_and_gb18030():
    data = '参数,值,备注\r\n"新\n规则",,"保持,原样"'.encode("gb18030")
    _, content, _, _ = parse_attachment(data, "参数.CSV")
    assert '[行 2] ["新\\n规则", "", "保持,原样"]' in content


def test_source_zip_reports_omitted_binary_without_truncating_supported_source():
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("source/one.cs", "class One {}\n" + "// x\n" * 3000)
        archive.writestr("library.dll", b"\x00\x01")
    _, content, status, notes = parse_attachment(output.getvalue(), "source.zip")
    assert content.count("// x") == 3000
    assert status == "partial" and "library.dll" in notes


def test_zip_traversal_and_duplicate_members_are_rejected():
    for names in [["../escape.cs"], ["one.cs", "one.cs"]]:
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            for name in names:
                archive.writestr(name, "class Test {}")
        with pytest.raises(ValueError):
            parse_attachment(output.getvalue(), "unsafe.zip")


def test_scan_and_encrypted_pdf_fail_without_claiming_readable():
    for encrypted in [False, True]:
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        if encrypted:
            writer.encrypt("password")
        output = io.BytesIO()
        writer.write(output)
        with pytest.raises(ValueError):
            parse_attachment(output.getvalue(), "scan.pdf")


def test_sparse_excel_outside_limits_is_rejected():
    book = Workbook()
    book.active["A20001"] = "limit"
    output = io.BytesIO()
    book.save(output)
    book.close()
    with pytest.raises(ValueError, match="20000"):
        parse_attachment(output.getvalue(), "large.xlsx")
