"""生产路由复用持久报告，但仍先检查会话权限。"""

from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.action_timing.source_report_cache import SourceReportCache
from app.modules.action_timing.source_service import SourceTiming

BASE = "/api/p/independent/action-timing/source-analysis"


def test_source_routes_reuse_the_persisted_report_after_app_restart(services, monkeypatch):
    (services[2].root / "Demo.cs").write_text(
        "class Demo : ActionNode {public int DoWork(){Thread.Sleep(12);return 0;}}",
        encoding="utf-8",
    )
    with TestClient(create_app(services[0])) as client:
        response = client.get(BASE)
        assert response.status_code == 200
        summary = response.json()
        identifier = summary["rows"][0]["id"]
        detail = client.get(BASE + "/" + identifier).json()
        exported = client.get(BASE + "/export").text
        coverage = client.get(BASE + "/coverage").json()
    assert list((services[0].data / "cache/action-timing").glob("*.json.gz"))

    def unexpected_build(*args):
        raise AssertionError("重启后的相同源码应直接复用报告")

    monkeypatch.setattr(SourceTiming, "_build", unexpected_build)
    with TestClient(create_app(services[0])) as client:
        assert client.get(BASE).json() == summary
        assert client.get(BASE + "/" + identifier).json() == detail
        assert client.get(BASE + "/export").text == exported
        assert client.get(BASE + "/coverage").json() == coverage


def test_anonymous_request_cannot_load_an_existing_report_cache(services, monkeypatch):
    with TestClient(create_app(services[0])) as client:
        assert client.get(BASE).status_code == 200
        calls = []
        original = SourceReportCache.load

        def measured(self, signature):
            calls.append(signature)
            return original(self, signature)

        monkeypatch.setattr(SourceReportCache, "load", measured)
        client.cookies.clear()
        assert client.get(BASE).status_code == 401
        assert not calls
