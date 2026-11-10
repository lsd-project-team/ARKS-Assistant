import io
import re

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfReader, PdfWriter

from app.main import create_app
from tests.helpers.api_paths import project_api
from tests.helpers.chat_attachments import document_bytes, zip_bytes


def test_real_ocr_models_work_without_network_or_runtime_download(monkeypatch):
    from rapidocr.utils.download_file import DownloadFile
    from requests.sessions import Session

    from app.infrastructure.pdf_ocr_worker import recognize_pages

    def forbidden(*args, **kwargs):
        pytest.fail("识别文档时不能联网或下载模型")

    monkeypatch.setattr(DownloadFile, "run", forbidden)
    monkeypatch.setattr(Session, "request", forbidden)
    records = recognize_pages(document_bytes(".scan.pdf", 47), [1])
    assert records[0]["page"] == 1 and "扫描文档测试" in records[0]["text"]
    assert not records[0]["partial"]


@pytest.mark.parametrize("kind", ["pdf", "zip", "mixed"])
def test_real_local_ocr_upload_preview_download_and_locations(services, kind):
    data, filename = document_bytes(".scan.pdf", 47), "扫描件.pdf"
    assert not PdfReader(io.BytesIO(data)).pages[0].extract_text().strip()
    page = 1
    if kind == "zip":
        data, filename = zip_bytes({"docs/扫描件.pdf": data}), "扫描资料.zip"
    elif kind == "mixed":
        writer, output = PdfWriter(), io.BytesIO()
        writer.add_page(PdfReader(io.BytesIO(document_bytes(".pdf"))).pages[0])
        writer.add_page(PdfReader(io.BytesIO(data)).pages[0])
        writer.write(output)
        data, page = output.getvalue(), 2
    with TestClient(create_app(services[0])) as client:
        response = client.post(
            project_api(client, "/attachments"),
            params={"filename": filename},
            content=data,
            headers={"Content-Type": "application/octet-stream"},
        )
        assert response.status_code == 201, response.text
        attachment = response.json()
        assert attachment["filename"] == filename and attachment["parse_status"] == "readable"
        prefix = project_api(client, f"/attachments/{attachment['id']}")
        preview = client.get(prefix)
        assert preview.status_code == 200
        content = preview.json()["content"]
        assert f"[第 {page} 页] [OCR 识别]" in content
        assert "扫描文档测试" in content and re.search(r"NewValue\s*=\s*47\b", content)
        assert "120" in content and "合格" in content
        if kind == "zip":
            assert "[文件 docs/扫描件.pdf]" in content
        if kind == "mixed":
            assert "[第 1 页]\nNewValue = 7" in content
        assert client.get(prefix + "/download").content == data
