import io
import json
import subprocess
from types import SimpleNamespace

import pytest
from pypdf import PdfReader, PdfWriter

from app.infrastructure import pdf_ocr
from app.infrastructure import pdf_ocr_worker as worker
from app.infrastructure.pdf_ocr import OcrLimitError, PdfOcrBudget, decode_result, failed_pages
from app.modules.chat.attachment_parsing import parse_attachment
from app.modules.handover.infrastructure.parsers.pdf import parse_pdf
from tests.helpers.chat_attachments import document_bytes, zip_bytes


def blank_pdf(count=1):
    writer, output = PdfWriter(), io.BytesIO()
    for _ in range(count):
        writer.add_blank_page(width=100, height=100)
    writer.write(output)
    return output.getvalue()


def mixed_pdf():
    writer, output = PdfWriter(), io.BytesIO()
    writer.add_page(PdfReader(io.BytesIO(document_bytes(".pdf"))).pages[0])
    writer.add_page(PdfReader(io.BytesIO(blank_pdf())).pages[0])
    writer.write(output)
    return output.getvalue()


def test_text_pdf_never_calls_ocr_and_mixed_pdf_only_calls_for_empty_page():
    calls = []

    def ocr(data, pages):
        calls.append(pages)
        return {number: {"text": "扫描页目标 47", "partial": False} for number in pages}

    text, status, _, _ = parse_pdf(document_bytes(".pdf"), ocr=ocr)
    assert status == "readable" and "NewValue = 7" in text and calls == []
    text, status, notes, _ = parse_pdf(mixed_pdf(), ocr=ocr)
    assert calls == [[2]] and status == "readable"
    assert "[第 1 页]\nNewValue = 7" in text
    assert "[第 2 页] [OCR 识别]\n扫描页目标 47" in text
    assert "OCR 已识别页：[2]" in notes


@pytest.mark.parametrize("partial", [False, True])
def test_ocr_page_status_and_source_are_preserved_in_zip(partial):
    def ocr(data, pages):
        return {number: {"text": "扫描页目标 47", "partial": partial} for number in pages}

    _, content, status, notes = parse_attachment(
        zip_bytes({"docs/scan.pdf": blank_pdf()}), "scans.zip", ocr_budget=ocr
    )
    assert status == ("partial" if partial else "readable")
    assert "[文件 docs/scan.pdf]" in content and "[OCR 识别]" in content
    assert "扫描页目标 47" in content
    if partial:
        assert "docs/scan.pdf" in notes and "低置信或识别不完整页：[1]" in content


def test_failed_ocr_preserves_native_text_but_all_failed_scan_is_rejected():
    def ocr(data, pages):
        return failed_pages(pages, "OCR 组件不可用")

    content, status, notes, _ = parse_pdf(mixed_pdf(), ocr=ocr)
    assert status == "partial" and "NewValue = 7" in content
    assert "[第 2 页]" in content and "OCR 组件不可用" in content and "OCR 组件不可用" in notes
    with pytest.raises(ValueError, match="OCR 组件不可用"):
        parse_attachment(blank_pdf(), "scan.pdf", ocr_budget=ocr)


def test_zip_shares_ocr_page_budget_and_does_not_swallow_cumulative_limit(monkeypatch):
    def run(*args, **kwargs):
        output = json.dumps({"pages": [{"page": 1, "text": "ok", "partial": False}]}).encode()
        return SimpleNamespace(returncode=0, stdout=output)

    monkeypatch.setattr(pdf_ocr.subprocess, "run", run)
    data = zip_bytes({"a.pdf": blank_pdf(), "b.pdf": blank_pdf()})
    with pytest.raises(OcrLimitError, match="累计超过 50 页"):
        parse_attachment(data, "two.zip", ocr_budget=PdfOcrBudget(pages_left=1))


def test_ocr_worker_uses_stdin_fixed_command_and_bounded_timeout(monkeypatch):
    calls = []

    def run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout=b'{"pages":[{"page":2,"text":"recognized","partial":false}]}',
        )

    monkeypatch.setattr(pdf_ocr.subprocess, "run", run)
    result = PdfOcrBudget()(b"private-pdf-bytes", [2])
    command, kwargs = calls[0]
    assert command[-3:] == ["app.infrastructure.pdf_ocr_worker", "--pages", "2"]
    assert "private-pdf-bytes" not in " ".join(command)
    assert kwargs["input"] == b"private-pdf-bytes" and 0 < kwargs["timeout"] <= 120
    assert result[2]["text"] == "recognized"


def test_ocr_timeout_is_fatal_and_releases_slot_for_next_request(monkeypatch):
    class Slots:
        acquired = 0
        released = 0

        def acquire(self, **kwargs):
            self.acquired += 1
            return True

        def release(self):
            self.released += 1

    slots = Slots()

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("ocr", 120)

    monkeypatch.setattr(pdf_ocr, "_slots", slots)
    monkeypatch.setattr(pdf_ocr.subprocess, "run", timeout)
    with pytest.raises(OcrLimitError, match="120 秒"):
        PdfOcrBudget()(b"pdf", [1])
    assert slots.acquired == slots.released == 1


def test_expired_budget_never_starts_worker(monkeypatch):
    monkeypatch.setattr(pdf_ocr.time, "monotonic", lambda: 121)

    def forbidden(*args, **kwargs):
        pytest.fail("超时预算不能启动 OCR")

    monkeypatch.setattr(pdf_ocr.subprocess, "run", forbidden)
    with pytest.raises(OcrLimitError, match="120 秒"):
        PdfOcrBudget(deadline=120)(b"pdf", [1])


@pytest.mark.parametrize("output", [b"bad json", b"[]", b'{"pages":[]}', b'{"pages":[{}]}'])
def test_invalid_worker_output_never_claims_success(output):
    result = decode_result(output, [1])
    assert result[1]["text"] == "" and result[1]["partial"]
    assert "无效" in result[1]["error"]


def test_worker_limit_is_not_downgraded_to_unreadable_page():
    with pytest.raises(OcrLimitError, match="超限"):
        decode_result(json.dumps({"limit_error": "超限"}).encode(), [1])


@pytest.mark.parametrize("failure", ["missing", "exit"])
def test_unavailable_worker_has_actionable_failure_without_exposing_stderr(monkeypatch, failure):
    def run(*args, **kwargs):
        if failure == "missing":
            raise OSError("private-host-path")
        return SimpleNamespace(returncode=1, stdout=b"", stderr=b"private-document-content")

    monkeypatch.setattr(pdf_ocr.subprocess, "run", run)
    result = PdfOcrBudget()(b"pdf", [1])
    assert "Setup.ps1" in result[1]["error"] and result[1]["text"] == ""
    assert "private" not in str(result)


def test_ocr_deadline_is_shared_between_documents(monkeypatch):
    elapsed, timeouts = [0], []
    monkeypatch.setattr(pdf_ocr.time, "monotonic", lambda: elapsed[0])

    def run(*args, **kwargs):
        timeouts.append(kwargs["timeout"])
        elapsed[0] += 20
        return SimpleNamespace(
            returncode=0, stdout=b'{"pages":[{"page":1,"text":"ok","partial":false}]}'
        )

    monkeypatch.setattr(pdf_ocr.subprocess, "run", run)
    budget = PdfOcrBudget()
    budget(b"first", [1])
    budget(b"second", [1])
    assert timeouts == [120, 100] and budget.deadline == 120


def test_queue_timeout_never_releases_a_slot_it_did_not_acquire(monkeypatch):
    class Slots:
        def acquire(self, **kwargs):
            return False

        def release(self):
            pytest.fail("不能释放其他请求正在使用的 OCR 槽位")

    monkeypatch.setattr(pdf_ocr, "_slots", Slots())
    with pytest.raises(OcrLimitError, match="120 秒"):
        PdfOcrBudget()(b"pdf", [1])


def test_worker_bounds_render_size_filters_low_scores_and_releases_bitmap():
    class Bitmap:
        closed = False

        def to_numpy(self):
            return "pixels"

        def close(self):
            self.closed = True

    class Page:
        bitmap = Bitmap()
        scale = 0

        def get_size(self):
            return 10000, 5000

        def render(self, scale):
            self.scale = scale
            return self.bitmap

    page = Page()

    def engine(pixels):
        assert pixels == "pixels"
        return SimpleNamespace(txts=("bad", "uncertain", "good"), scores=(0.3, 0.7, 0.99))

    result = worker.recognize_page(page, engine)
    assert page.scale == 0.25 and page.bitmap.closed
    assert result["text"] == "uncertain\ngood" and result["partial"] is True


def test_worker_releases_bitmap_on_inference_failure():
    bitmap = SimpleNamespace(to_numpy=lambda: "pixels", close=lambda: closed.append(True))
    page = SimpleNamespace(get_size=lambda: (100, 100), render=lambda **kwargs: bitmap)
    closed = []

    def engine(pixels):
        raise RuntimeError("inference failed")

    with pytest.raises(RuntimeError, match="inference failed"):
        worker.recognize_page(page, engine)
    assert closed == [True]
