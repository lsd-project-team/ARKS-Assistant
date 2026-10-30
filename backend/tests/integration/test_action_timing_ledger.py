"""台账API、实际SQLite事务、文件往返、权限和并发；只用临时库。"""

import csv
import io
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.modules.action_timing.ledger_files import HEADERS
from app.modules.auth.models import Account
from tests.helpers.accounts import sign_in

BASE = "/api/action-timing/ledger"


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


def test_empty_ledger_does_not_seed_data_and_survives_restart(services):
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


def test_retired_source_routes_are_absent_and_preserve_ledger_and_historical_reports(services):
    directory = services[0].data / "cache/action-timing"
    directory.mkdir(parents=True)
    report = directory / "historical.json.gz"
    historical = b"historical-report-not-for-loading"
    report.write_bytes(historical)
    with TestClient(create_app(services[0])) as client:
        item = action(client, "保留动作", duration=0)
        before = client.get(BASE).json()
        # 已移除的接口不再返回暂停占位，也不能读缓存或改变现有台账。
        for prefix in ("/api/action-timing", "/api/p/independent/action-timing"):
            for suffix in ("", "/export", "/coverage", "/old-action-id"):
                response = client.get(prefix + "/source-analysis" + suffix)
                assert response.status_code == 404
                expected = "接口不存在" if prefix == "/api/action-timing" else "Not Found"
                assert response.json() == {"detail": expected}
        assert client.get(BASE).json() == before
        assert report.read_bytes() == historical
    with TestClient(create_app(services[0])) as client:
        stored = client.get(BASE).json()["items"]
        assert len(stored) == 1 and stored[0]["id"] == item["id"]
        assert stored[0]["duration_seconds"] == 0
        assert report.read_bytes() == historical


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


def test_duration_sort_is_global_before_pagination_nulls_last_and_export_matches(services):
    with TestClient(create_app(services[0])) as client:
        preview = upload(
            client,
            [["A" if i % 2 else "B", f"动作{i:02d}", 25 - i, ""] for i in range(25)]
            + [["A", "零值", 0, ""], ["A", "待填1", "", ""], ["B", "待填2", "", ""]],
        )
        assert commit(client, preview).status_code == 200
        for sort, values in [
            ("duration_asc", list(range(26))),
            ("duration_desc", list(range(25, -1, -1))),
        ]:
            pages = [
                client.get(BASE, params={"sort": sort, "offset": offset, "limit": 20}).json()
                for offset in (0, 20)
            ]
            assert [page["total"] for page in pages] == [28, 28]
            items = pages[0]["items"] + pages[1]["items"]
            assert [row["duration_seconds"] for row in items] == values + [None, None]
            exported = client.get(BASE + "/export", params={"sort": sort, "format": "csv"})
            assert exported.status_code == 200
            records = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
            assert [row[1] for row in records[1:]] == [row["name"] for row in items]
        filtered = client.get(BASE, params={"sort": "duration_desc", "search": "动作0"}).json()
        assert [row["duration_seconds"] for row in filtered["items"]] == list(range(25, 15, -1))
        missing = client.get(
            BASE, params={"sort": "duration_desc", "duration_status": "missing"}
        ).json()
        assert missing["total"] == 2 and all(
            row["duration_seconds"] is None for row in missing["items"]
        )
        assert client.get(BASE, params={"sort": "invalid"}).status_code == 422


def test_equal_durations_keep_stable_order_and_zero_is_not_missing(services):
    with TestClient(create_app(services[0])) as client:
        preview = upload(
            client, [["B", "b", 1, ""], ["A", "z", 1, ""], ["A", "a", 1, ""], ["", "zero", 0, ""]]
        )
        assert commit(client, preview).status_code == 200
        for sort in ("duration_asc", "duration_desc"):
            tied = client.get(BASE, params={"sort": sort, "search": ""}).json()["items"]
            assert [row["name"] for row in tied if row["duration_seconds"] == 1] == ["a", "z", "b"]
        assert client.get(BASE, params={"duration_status": "filled"}).json()["total"] == 4


@pytest.mark.parametrize("format", ["csv", "xlsx"])
def test_millisecond_template_import_preview_commit_and_export_only_convert_once(services, format):
    from openpyxl import load_workbook

    with TestClient(create_app(services[0])) as client:
        template = client.get(
            BASE + "/export", params={"format": format, "template": True, "template_unit": "ms"}
        )
        assert template.status_code == 200
        if format == "csv":
            assert "耗时（毫秒）" in template.content.decode("utf-8-sig")
            raw = (
                template.content + "固晶,取片,1250,换算\r\n固晶,零值,0,\r\n固晶,待填,,\r\n".encode()
            )
        else:
            book = load_workbook(io.BytesIO(template.content))
            assert book.active["C1"].value == "耗时（毫秒）"
            for row in [
                ["固晶", "取片", 1250, "换算"],
                ["固晶", "零值", 0, ""],
                ["固晶", "待填", None, ""],
            ]:
                book.active.append(row)
            output = io.BytesIO()
            book.save(output)
            book.close()
            raw = output.getvalue()
        response = client.post(
            BASE + "/import-preview", params={"filename": "现场." + format}, content=raw
        )
        assert response.status_code == 200
        preview = response.json()
        assert not preview["errors"]
        assert [row["duration_seconds"] for row in preview["rows"]] == [1.25, 0, None]
        assert client.get(BASE).json()["total"] == 0
        assert commit(client, preview).status_code == 200
        stored = {row["name"]: row["duration_seconds"] for row in client.get(BASE).json()["items"]}
        assert stored == {"取片": 1.25, "零值": 0, "待填": None}
        exported = client.get(BASE + "/export", params={"format": "csv"})
        rows = list(csv.reader(io.StringIO(exported.content.decode("utf-8-sig"))))
        assert rows[0][2] == "耗时（秒）"
        assert next(row for row in rows if row[1] == "取片")[2] == "1.25"
        bad = client.post(
            BASE + "/import-preview",
            params={"filename": "现场." + format, "unit": "s"},
            content=raw,
        )
        assert bad.status_code == 422 and "与表头不一致" in bad.json()["detail"]
        assert (
            client.post(
                BASE + "/import-preview",
                params={"filename": "现场.csv", "unit": "minutes"},
                content=b"bad",
            ).status_code
            == 422
        )


@pytest.mark.authentication
def test_accounts_and_csrf_protect_independent_timing_projects(services):
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
        a = action(client, "个人动作")
        project = client.post("/api/action-timing/projects", json={"name": "第二台设备"}).json()
        scope = {"timing_project": project["id"]}
        c = client.post(BASE + "/categories", params=scope, json={"name": "项目分类"}).json()
        added = client.post(
            BASE + "/actions", params=scope, json={"name": "项目动作", "category_id": c["id"]}
        )
        assert added.status_code == 201
        assert (
            client.post(
                BASE + "/actions", json={"name": "越界分类", "category_id": c["id"]}
            ).status_code
            == 404
        )
        login("ledger-b")
        assert client.get(BASE).json()["total"] == 0
        assert project["id"] not in {
            row["id"] for row in client.get("/api/action-timing/projects").json()["projects"]
        }
        assert client.get(BASE, params=scope).status_code == 404
        assert client.get(BASE + "/export", params=scope).status_code == 404
        assert (
            client.post(BASE + "/actions", params=scope, json={"name": "越权"}).status_code == 404
        )
        assert (
            client.patch(
                "/api/action-timing/projects/" + project["id"],
                json={"name": "越权改名", "version": 1},
            ).status_code
            == 404
        )
        assert client.delete(BASE + "/actions/" + a["id"], params={"version": 1}).status_code == 404
        client.headers.pop("X-Arks-CSRF")
        assert client.post(BASE + "/actions", json={"name": "无CSRF"}).status_code == 403


def test_timing_project_names_and_data_are_independent_of_chat_lifecycle(services):
    with TestClient(create_app(services[0])) as client:
        timing = client.get("/api/action-timing/projects").json()["projects"][0]
        assert timing["name"] == "智芯2200"
        item = action(client, "取片", duration=0.12)
        chat = client.post("/api/projects", json={"name": "软件分析"}).json()
        assert client.get("/api/projects/" + timing["id"]).status_code == 404
        assert client.get(BASE, params={"timing_project": chat["id"]}).status_code == 404
        renamed = client.patch(
            "/api/action-timing/projects/" + timing["id"],
            json={"name": "智芯2200现场", "version": 1},
        )
        assert renamed.status_code == 200 and renamed.json()["version"] == 2
        assert client.get("/api/projects/" + chat["id"]).json()["name"] == "软件分析"
        assert (
            client.patch(
                "/api/action-timing/projects/" + timing["id"], json={"name": "过期", "version": 1}
            ).status_code
            == 409
        )
        assert (
            client.post("/api/action-timing/projects", json={"name": " 智芯2200现场 "}).status_code
            == 409
        )
        assert client.post("/api/action-timing/projects", json={"name": "  "}).status_code == 422
        for changes in ({"name": "个人对话"}, {"state": "archived"}):
            assert client.patch("/api/projects/" + chat["id"], json=changes).status_code == 200
            data = client.get(BASE).json()
            assert data["writable"] and data["items"] == [item]
        assert client.delete("/api/projects/" + chat["id"]).status_code == 200
        assert (
            client.get("/api/action-timing/projects").json()["projects"][0]["name"]
            == "智芯2200现场"
        )
        assert client.get(BASE).json()["items"] == [item]
        action(client, "删除聊天项目后仍可添加", duration=0)
        other = client.post("/api/action-timing/projects", json={"name": "另一台设备"}).json()
        assert client.get(BASE, params={"timing_project": other["id"]}).json()["total"] == 0
        assert client.get(BASE, params={"timing_project": timing["id"]}).json()["total"] == 2
