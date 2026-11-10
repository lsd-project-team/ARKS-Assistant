import io
import zipfile

import pytest
from pypdf import PdfReader, PdfWriter

from app.modules.chat import attachment_parsing
from app.modules.chat.attachment_parsing import MAX_UPLOAD, parse_attachment
from tests.helpers.chat_attachments import document_bytes, zip_bytes


@pytest.mark.parametrize(
    "extension,position",
    [(".pdf", "[第 1 页]"), (".docx", "[段落 1]"), (".xlsx", "A2="), (".csv", "[行 2]")],
)
def test_zip_document_preserves_nested_path_content_and_positions(extension, position):
    path = "资料/需求" + extension.upper()
    _, content, status, notes = parse_attachment(
        zip_bytes({path: document_bytes(extension, 37)}), "资料.zip"
    )
    assert f"[文件 {path}]" in content
    assert "NewValue = 37" in content and position in content
    assert status == "readable" and "读取 1 个文件" in notes
    if extension == ".xlsx":
        assert "C2==B2+1" in content and "未重新计算" in content


def test_zip_mixes_documents_and_source_without_merging_same_basename():
    files = {
        f"folder{index}/需求{extension}": document_bytes(extension, index + 11)
        for index, extension in enumerate([".pdf", ".docx", ".xlsx", ".csv", ".cs"])
    }
    files["other/需求.cs"] = b"// other source"
    _, content, status, _ = parse_attachment(zip_bytes(files), "mixed.zip")
    assert status == "readable"
    for path, value in zip(list(files)[:5], range(11, 16), strict=True):
        section = content.split(f"[文件 {path}]\n", 1)[1].split("[文件 ", 1)[0]
        assert f"NewValue = {value}" in section
    assert "[文件 other/需求.cs]" in content and "[L1] // other source" in content


def test_zip_reports_invalid_and_unsupported_members_and_continues():
    files = {
        "broken.pdf": b"not pdf",
        "broken.docx": b"not zip",
        "broken.xlsx": b"not zip",
        "broken.csv": b"\x00\x01",
        "empty.md": b"  ",
        "nested.zip": document_bytes(".zip", 99),
        "unsupported.rar": b"rar",
        "valid.cs": b"class Valid {}",
    }
    _, content, status, notes = parse_attachment(zip_bytes(files), "mixed.zip")
    assert status == "partial" and "class Valid {}" in content
    for path in list(files)[:-1]:
        assert path in notes and f"[文件 {path}]" not in content
    assert "NewValue = 99" not in content
    assert "解析失败" in notes and "格式暂不支持" in notes


@pytest.mark.parametrize("extension", [".pdf", ".docx", ".xlsx", ".csv"])
def test_zip_with_no_readable_document_fails_with_member_reason(extension):
    with pytest.raises(ValueError, match="没有可读取") as error:
        parse_attachment(zip_bytes({"bad" + extension: b""}), "bad.zip")
    assert "bad" + extension in str(error.value)


@pytest.mark.parametrize("kind", ["scan", "encrypted", "mixed"])
def test_zip_propagates_pdf_scan_encryption_and_partial_page_status(kind):
    writer = PdfWriter()
    if kind == "mixed":
        writer.add_page(PdfReader(io.BytesIO(document_bytes(".pdf"))).pages[0])
    writer.add_blank_page(width=100, height=100)
    if kind == "encrypted":
        writer.encrypt("password")
    output = io.BytesIO()
    writer.write(output)
    _, content, status, notes = parse_attachment(
        zip_bytes({"docs/input.pdf": output.getvalue(), "valid.cs": b"class Valid {}"}),
        "docs.zip",
    )
    assert status == "partial" and "docs/input.pdf" in notes
    if kind == "mixed":
        assert "[第 2 页]" in content and "无可提取文字页：[2]" in content
        assert "部分可读的文件" in notes
    else:
        assert "[文件 docs/input.pdf]" not in content
        assert ("扫描件" if kind == "scan" else "加密 PDF") in notes


def office_with_extra_files(extension, extra_files):
    source = zipfile.ZipFile(io.BytesIO(document_bytes(extension)))
    with source:
        files = {item.filename: source.read(item) for item in source.infolist()}
    return zip_bytes(files | extra_files)


@pytest.mark.parametrize("extension", [".docx", ".xlsx"])
def test_zip_office_member_can_exceed_old_two_mb_text_limit(extension):
    # 使用存储模式使 Office 原文件大于 2 MB，正文仍然是正常小文档。
    data = io.BytesIO(office_with_extra_files(extension, {}))
    with zipfile.ZipFile(data, "a") as archive:
        archive.writestr("padding.bin", b"x" * 2_000_001)
    document = data.getvalue()
    assert len(document) > 2_000_000
    _, content, status, _ = parse_attachment(zip_bytes({"large" + extension: document}), "docs.zip")
    assert "NewValue = 7" in content and status == "readable"


@pytest.mark.parametrize("extension,limit", [(".txt", 2_000_000), (".pdf", MAX_UPLOAD)])
def test_zip_reports_member_size_limit_without_losing_other_files(extension, limit):
    _, content, status, notes = parse_attachment(
        zip_bytes({"large" + extension: b"x" * (limit + 1), "ok.cs": b"class Ok {}"}),
        "large.zip",
    )
    assert status == "partial" and "class Ok {}" in content
    assert "large" + extension in notes and "超过" in notes


@pytest.mark.parametrize(
    "files",
    [
        {"huge.txt": b"x" * 1_000_001},
        {
            "first.txt": b"x" * 600_000,
            "second.csv": ("x" * 90 + ",7\n").encode() * 6000,
        },
    ],
)
def test_zip_rejects_individual_and_combined_content_overflow(files):
    with pytest.raises(ValueError, match="100 万"):
        parse_attachment(zip_bytes(files), "huge.zip")


def test_zip_counts_embedded_office_expansion_toward_total_budget(monkeypatch):
    office = office_with_extra_files(".docx", {"padding.bin": b"x" * 10_000})
    data = zip_bytes({"one.docx": office, "two.docx": office})
    with zipfile.ZipFile(io.BytesIO(office)) as archive:
        expanded = sum(item.file_size for item in archive.infolist())
    # 缩小预算验证累积边界，输入仍使用真实压缩包和真实 Word 解析。
    monkeypatch.setattr(attachment_parsing, "MAX_EXPANDED", len(office) * 2 + expanded)
    with pytest.raises(ValueError, match="累计"):
        parse_attachment(data, "expanded.zip")


def test_zip_counts_embedded_office_entries_toward_total_budget():
    office = office_with_extra_files(".docx", {f"extra/{i}": b"" for i in range(1000)})
    with pytest.raises(ValueError, match="2000"):
        parse_attachment(zip_bytes({"one.docx": office, "two.docx": office}), "entries.zip")


def test_zip_still_rejects_unsafe_outer_and_office_member_paths():
    with pytest.raises(ValueError, match="不安全路径"):
        parse_attachment(zip_bytes({"../bad.pdf": document_bytes(".pdf")}), "unsafe.zip")
    office = office_with_extra_files(".docx", {"../escape": b"bad"})
    _, content, status, notes = parse_attachment(
        zip_bytes({"unsafe.docx": office, "ok.txt": b"ok"}), "docs.zip"
    )
    assert status == "partial" and "[L1] ok" in content
    assert "unsafe.docx" in notes and "不安全路径" in notes
