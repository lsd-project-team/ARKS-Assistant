"""交接包下载必须同时满足当前记录和所选快照已确认。"""

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.helpers.accounts import sign_in


@pytest.fixture
def client(services):
    with TestClient(create_app(services[0])) as value:
        yield value


def create_package(client):
    source = client.post(
        "/api/handover/records",
        json={
            "kind": "issue",
            "title": "原始处理经验",
            "actor": "整理人",
            "payload": {"question": "保留打包时的经验"},
        },
    )
    assert source.status_code == 201, source.text
    package = client.post(
        "/api/handover/packages",
        json={"title": "交接包", "actor": "整理人", "record_ids": [source.json()["id"]]},
    )
    assert package.status_code == 201, package.text
    return source.json(), package.json()


def act(client, row, action="confirm"):
    return client.post(
        f"/api/handover/records/{row['id']}/{action}",
        json={"version": row["version"], "actor": "确认人", "opinion": "已核对交接内容"},
    )


@pytest.mark.parametrize("format", ["docx", "zip"])
def test_download_requires_confirmation_and_old_links_cannot_bypass_invalidation(client, format):
    source, package = create_package(client)
    path = f"/api/handover/packages/{package['id']}/export?format={format}"
    draft_version = package["version"]
    blocked = client.get(path)
    assert blocked.status_code == 409 and "交接包未确认" in blocked.text
    assert "content-disposition" not in blocked.headers
    rejected = act(client, package, "reject")
    assert rejected.status_code == 409 and "仅使用未确认和已确认" in rejected.text
    assert client.get(f"/api/handover/records/{package['id']}").json()["version"] == draft_version

    confirmed = act(client, package)
    assert confirmed.status_code == 200, confirmed.text
    package = confirmed.json()
    assert package["state"] == "confirmed"
    assert act(client, {**package, "version": draft_version}).status_code == 409
    result = client.get(path)
    assert result.status_code == 200 and "attachment;" in result.headers["content-disposition"]
    assert zipfile.is_zipfile(io.BytesIO(result.content))
    assert client.get(path + f"&version={draft_version}").status_code == 409

    updated = client.patch(
        f"/api/handover/records/{source['id']}",
        json={
            "kind": source["kind"],
            "title": source["title"],
            "version": source["version"],
            "actor": "整理人",
            "payload": {**source["payload"], "question": "来源内容已更新"},
        },
    )
    assert updated.status_code == 200, updated.text
    current = client.get(f"/api/handover/records/{package['id']}").json()
    assert current["state"] == "needs_review"
    assert client.get(path).status_code == 409
    assert client.get(path + f"&version={package['version']}").status_code == 409
    confirmed = act(client, current)
    assert confirmed.status_code == 200, confirmed.text
    package = confirmed.json()
    assert client.get(path).status_code == 200
    archived = act(client, package, "archive")
    assert archived.status_code == 200
    assert client.get(path + f"&version={package['version']}").status_code == 409
    restored = act(client, archived.json(), "restore")
    assert restored.status_code == 200 and restored.json()["state"] == "needs_review"
    assert client.get(path).status_code == 409


def test_user_can_download_confirmed_package_but_cannot_confirm_it(client):
    _, package = create_package(client)
    path = f"/api/handover/packages/{package['id']}/export?format=zip"
    sign_in(client, "user")
    assert act(client, package).status_code == 403
    assert client.get(path).status_code == 409
    sign_in(client)
    confirmed = act(client, package)
    assert confirmed.status_code == 200, confirmed.text
    sign_in(client, "user")
    result = client.get(path)
    assert result.status_code == 200
    with zipfile.ZipFile(io.BytesIO(result.content)) as bundle:
        assert {"handover.docx", "manifest.json"}.issubset(bundle.namelist())
