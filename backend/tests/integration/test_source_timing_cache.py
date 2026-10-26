"""暂停入口不得加载、重算或删除已保存的源码报告。"""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.action_timing.source_report_cache import SourceReportCache

BASE = "/api/p/independent/action-timing/source-analysis"


def test_paused_source_routes_preserve_existing_cache_after_restart(services, monkeypatch):
    directory = services[0].data / "cache/action-timing"
    directory.mkdir(parents=True)
    path = directory / "historical.json.gz"
    path.write_bytes(b"historical-report-not-for-loading")

    def forbidden(*args, **kwargs):
        raise AssertionError("暂停后不得读取报告缓存")

    monkeypatch.setattr(SourceReportCache, "load", forbidden)
    for _ in range(2):
        with TestClient(create_app(services[0])) as client:
            assert client.get(BASE).status_code == 410
            assert client.get(BASE + "/export").status_code == 410
        assert path.read_bytes() == b"historical-report-not-for-loading"


@pytest.mark.authentication
def test_anonymous_request_is_rejected_before_accessing_a_paused_source_route(services):
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE)
        assert response.status_code == 401
