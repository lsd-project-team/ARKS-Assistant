"""台账API、实际SQLite事务、文件往返、权限和并发；只用临时库。"""

import csv
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.action_timing.ledger_files import HEADERS
from app.modules.action_timing.source_service import SourceTiming
from app.modules.auth.models import Account
from tests.helpers.accounts import sign_in

BASE = "/api/p/independent/action-timing/ledger"


def upload(client, rows, *, base=BASE, mode="skip"):
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(HEADERS)
    writer.writerows(rows)
    response = client.post(
        base + "/import-preview",
        params={"filename": "测试.csv", "mode": mode},
        content=output.getvalue().encode("utf-8-sig"),
    )
    assert response.status_code == 200, response.text
    return response.json()


def commit(client, preview, *, base=BASE, mode="skip"):
    rows = [
        {key: row[key] for key in ("row_number", "category", "name", "duration_seconds", "notes")}
        for row in preview["rows"]
    ]
    return client.post(
        base + "/imports", json={"rows": rows, "mode": mode, "revision": preview["revision"]}
    )


def category(client, name, base=BASE):
    response = client.post(base + "/categories", json={"name": name})
    assert response.status_code == 201, response.text
    return response.json()


def action(client, name, category_id=None, duration=None, base=BASE):
    response = client.post(
        base + "/actions",
        json={"name": name, "category_id": category_id, "duration_seconds": duration},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_empty_ledger_does_not_analyze_source_or_seed_data_and_survives_restart(
    services, monkeypatch
):
    def forbidden(*args, **kwargs):
        raise AssertionError("新台账不得启动源码模拟")

    monkeypatch.setattr(SourceTiming, "__init__", forbidden)
    with TestClient(create_app(services[0])) as client:
        data = client.get(BASE).json()
        assert data["items"] == data["categories"] == []
        assert data["total"] == data["action_count"] == 0 and data["writable"]
        assert client.get(BASE + "/export?template=true").status_code == 200
        assert client.get(BASE).json() == data
        item = action(client, "待导入耗时")
        assert item["duration_seconds"] is None and item["category"] == "未分类"
    with TestClient(create_app(services[0])) as client:
        assert client.get(BASE).json()["items"][0]["id"] == item["id"]


def test_category_action_crud_zero_blank_filters_and_stale_updates(services):
    with TestClient(create_app(services[0])) as client:
        first = category(client, "取料")
        other = category(client, "贴装")
        item = action(client, "准备", first["id"], 0)
        action(client, "准备")
        assert client.post(BASE + "/actions", json={"name": "准备"}).status_code == 409
        assert client.post(BASE + "/categories", json={"name": " 取料 "}).status_code == 409
        assert client.post(BASE + "/categories", json={"name": "未分类"}).status_code == 422
        renamed = client.patch(
            BASE + "/categories/" + first["id"], json={"name": "取片", "version": 1}
        )
        assert renamed.status_code == 200 and renamed.json()["version"] == 2
        assert (
            client.patch(
                BASE + "/categories/" + first["id"], json={"name": "过期", "version": 1}
            ).status_code
            == 409
        )
        data = client.get(BASE, params={"duration_status": "filled"}).json()
        assert data["total"] == 1 and data["items"][0]["duration_seconds"] == 0
        assert data["items"][0]["category"] == "取片"
        updated = client.patch(
            BASE + "/actions/" + item["id"],
            json={
                "name": "新准备",
                "category_id": other["id"],
                "duration_seconds": None,
                "notes": "测试备注",
                "version": 1,
            },
        )
        assert updated.status_code == 200 and updated.json()["duration_seconds"] is None
        assert updated.json()["category"] == "贴装" and updated.json()["version"] == 2
        assert (
            client.delete(BASE + "/actions/" + item["id"], params={"version": 1}).status_code == 409
        )
        filtered = client.get(
            BASE, params={"category_id": other["id"], "search": "新", "duration_status": "missing"}
        ).json()
        assert filtered["total"] == 1 and filtered["items"][0]["notes"] == "测试备注"
        assert (
            client.delete(BASE + "/actions/" + item["id"], params={"version": 2}).status_code == 200
        )
        assert client.get(BASE).json()["total"] == 1


def test_category_delete_moves_actions_and_conflicts_roll_back_entire_transaction(services):
    with TestClient(create_app(services[0])) as client:
        first, second = category(client, "甲"), category(client, "乙")
        a = action(client, "同名", first["id"], 1.25)
        action(client, "同名", second["id"], 2.5)
        response = client.request(
            "DELETE",
            BASE + "/categories/" + first["id"],
            json={"version": 1, "target_id": second["id"]},
        )
        assert response.status_code == 409
        data = client.get(BASE).json()
        assert len(data["categories"]) == 2 and data["total"] == 2
        assert next(row for row in data["items"] if row["id"] == a["id"])["version"] == 1
        moved = client.request("DELETE", BASE + "/categories/" + first["id"], json={"version": 1})
        assert moved.status_code == 200 and moved.json()["moved"] == 1
        row = client.get(BASE, params={"category_id": "uncategorized"}).json()["items"][0]
        assert row["id"] == a["id"] and row["duration_seconds"] == 1.25 and row["version"] == 2


def test_import_preview_validation_is_read_only_and_confirmation_is_atomic(services):
    with TestClient(create_app(services[0])) as client:
        bad = upload(client, [["新分类", "动作", "-2", ""], ["新分类", "动作2", 1, ""]])
        assert bad["errors"][0]["row_number"] == 2
        assert client.get(BASE).json()["categories"] == []
        duplicate = upload(client, [["A", "TEST", 1, ""], ["Ａ", "test", 2, ""]])
        assert duplicate["errors"] and commit(client, duplicate).status_code == 409
        good = upload(client, [["取料", "准备", 0, "保留零"], ["", "待填写", "", ""]])
        assert not good["errors"] and good["counts"] == {"add": 2, "update": 0, "skip": 0}
        assert client.get(BASE).json()["total"] == 0
        assert commit(client, good).status_code == 200
        data = client.get(BASE).json()
        assert data["total"] == 2 and len(data["categories"]) == 1
        assert sorted(row["name"] for row in data["items"]) == ["准备", "待填写"]
        fresh = upload(client, [["取料", "准备", 9, "替换"]])
        assert fresh["counts"]["skip"] == 1 and commit(client, fresh).status_code == 200
        update = upload(client, [["取料", "准备", "", "新备注"]], mode="update")
        assert update["rows"][0]["effective_duration_seconds"] == 0
        assert commit(client, update, mode="update").status_code == 200
        item = client.get(BASE, params={"search": "准备"}).json()["items"][0]
        assert item["duration_seconds"] == 0 and item["notes"] == "新备注"


def test_stale_and_concurrent_imports_do_not_overwrite_newer_data(services):
    with TestClient(create_app(services[0])) as client:
        preview = upload(client, [["取料", "准备", 1.5, ""]])
        category(client, "新分类")
        assert commit(client, preview).status_code == 409
        assert client.get(BASE).json()["total"] == 0
        fresh = upload(client, [["取料", "准备", 1.5, ""]])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: commit(client, fresh), range(2)))
        assert sorted(response.status_code for response in results) == [200, 409]
        assert client.get(BASE).json()["total"] == 1


@pytest.mark.parametrize("format", ["csv", "xlsx"])
def test_filtered_export_contains_all_pages_and_can_be_imported_again(services, format):
    with TestClient(create_app(services[0])) as client:
        preview = upload(
            client,
            [["取料", f"动作{i:02d}", i, ""] for i in range(25)] + [["贴装", "其他", "", ""]],
        )
        assert commit(client, preview).status_code == 200
        page = client.get(BASE, params={"search": "动作", "offset": 20, "limit": 20}).json()
        assert page["total"] == 25 and len(page["items"]) == 5
        response = client.get(BASE + "/export", params={"format": format, "search": "动作"})
        assert (
            response.status_code == 200 and "attachment;" in response.headers["content-disposition"]
        )
        imported = client.post(
            BASE + "/import-preview",
            params={"filename": "导出." + format},
            content=response.content,
        )
        assert imported.status_code == 200 and len(imported.json()["rows"]) == 25
        assert imported.json()["counts"] == {"add": 0, "update": 0, "skip": 25}


@pytest.mark.authentication
def test_accounts_projects_archive_and_csrf_cannot_be_bypassed(services):
    app = create_app(services[0])
    with TestClient(app) as client:
        assert client.get(BASE).status_code == 401
        sign_in(client)
        for name in ("ledger-a", "ledger-b"):
            with app.state.auth.database.session.begin() as session:
                session.add(
                    Account(
                        id=name,
                        username=name,
                        display_name=name,
                        role="user",
                        password_hash=app.state.auth.hasher.hash("test-password-1234"),
                    )
                )

        def login(name):
            response = client.post(
                "/api/auth/login", json={"username": name, "password": "test-password-1234"}
            )
            assert response.status_code == 200
            client.headers["X-Arks-CSRF"] = response.json()["csrf_token"]

        login("ledger-a")
        project = client.post("/api/projects", json={"name": "台账项目"}).json()
        scoped = f"/api/p/{project['id']}/action-timing/ledger"
        a = action(client, "个人动作")
        c = category(client, "项目分类", scoped)
        action(client, "项目动作", c["id"], base=scoped)
        assert (
            client.post(
                BASE + "/actions", json={"name": "越界分类", "category_id": c["id"]}
            ).status_code
            == 404
        )
        assert (
            client.patch("/api/projects/" + project["id"], json={"state": "archived"}).status_code
            == 200
        )
        assert not client.get(scoped).json()["writable"]
        assert client.post(scoped + "/actions", json={"name": "禁止修改"}).status_code == 409
        assert client.get(scoped + "/export").status_code == 200
        login("ledger-b")
        assert client.get(BASE).json()["total"] == 0
        assert client.get(scoped).status_code == 404
        assert client.get(scoped + "/export").status_code == 404
        assert client.delete(BASE + "/actions/" + a["id"], params={"version": 1}).status_code == 404
        client.headers.pop("X-Arks-CSRF")
        assert client.post(BASE + "/actions", json={"name": "无CSRF"}).status_code == 403
