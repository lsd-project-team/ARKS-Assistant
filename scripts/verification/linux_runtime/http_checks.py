"""通过实际HTTP写入微型项目、代码副本与资料；不启动Agent或验证命令。"""

import json
import re
from urllib.parse import urlsplit

from .safety import require, tree_hash

TEXT = "fixture original record\r\n记录人：Linux smoke\r\n"
ATTACHMENT = "fixture attachment\r\n中文附件原文\r\n".encode()


def request(client, method, url, status=200, **kwargs):
    response = client.request(method, url, **kwargs)
    require(response.status_code == status, "http_unexpected_status")
    return response


def bootstrap_password(data):
    path = data / "auth.initial-accounts.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    password = next(row["password"] for row in rows if row["username"] == "admin")
    # 应用引导文件仅在临时data短暂存在；之后密码只在本轮内存中保留。
    path.unlink()
    return password


def login(client, password, origin):
    client.headers["Origin"] = origin
    response = request(
        client,
        "POST",
        "/api/auth/login",
        json={
            "username": "admin",
            "password": password,
        },
    )
    body = response.json()
    require(body["user"]["role"] == "admin", "login_identity_not_admin")
    cookie = response.headers.get("set-cookie", "").lower()
    require(
        "secure" in cookie and "httponly" in cookie and "samesite=strict" in cookie,
        "deployed_https_cookie_flags_missing",
    )
    # HTTP在容器内模拟HTTPS反向代理上游；浏览器对外HTTPS Cookie不应被降级。
    token = response.cookies.get("arks_session")
    require(bool(token), "login_cookie_missing")
    client.headers["Cookie"] = f"arks_session={token}"
    client.headers["X-Arks-CSRF"] = body["csrf_token"]


def frontend(client):
    response = request(client, "GET", "/")
    require("text/html" in response.headers.get("content-type", ""), "frontend_not_html")
    assets = re.findall(r'(?:src|href)="(/assets/[^"?#]+)(?:[^"\s]*)?"', response.text)
    require(
        any(path.endswith(".js") for path in assets)
        and any(path.endswith(".css") for path in assets),
        "frontend_assets_missing",
    )
    for asset in assets:
        require(
            not urlsplit(asset).netloc and ".." not in asset.split("/"), "frontend_asset_not_local"
        )
        require(bool(request(client, "GET", asset).content), "frontend_asset_empty")


def csrf_checks(client, origin):
    token = client.headers.pop("X-Arks-CSRF")
    request(client, "POST", "/api/projects", status=403, json={"name": "must-not-create"})
    client.headers["X-Arks-CSRF"] = token
    request(
        client,
        "GET",
        "/api/projects",
        status=403,
        headers={"Origin": "https://untrusted.example.invalid"},
    )
    request(
        client,
        "GET",
        "/api/projects",
        status=403,
        headers={"Origin": origin, "Sec-Fetch-Site": "cross-site"},
    )
    request(
        client, "GET", "/api/projects", status=403, headers={"Host": "untrusted.example.invalid"}
    )


def populate(client, source):
    project = request(
        client,
        "POST",
        "/api/projects",
        status=201,
        json={
            "name": "Linux runtime fixture",
            "source_root": str(source),
            "auto_associate": False,
        },
    ).json()
    base = f"/api/p/{project['id']}"
    symbols = request(client, "GET", base + "/symbols", params={"path": "Entry.cs"}).json()
    require(
        {"Worker", "Run", "Start"} <= {row["name"] for row in symbols["symbols"]},
        "source_symbols_missing",
    )
    thread = request(
        client, "POST", base + "/threads", status=201, json={"title": "Linux persistent fixture"}
    ).json()
    change = request(
        client,
        "POST",
        base + "/code-changes",
        json={
            "title": "Linux isolated fixture edit",
            "goal": "Only update the fixture string",
            "acceptance_criteria": ["Original source hash stays unchanged"],
            "allowed_paths": ["Entry.cs"],
        },
    ).json()
    change_url = base + f"/code-changes/{change['id']}"
    old = request(client, "GET", change_url + "/file", params={"path": "Entry.cs"}).json()
    request(
        client,
        "PATCH",
        change_url + "/file",
        json={
            "path": "Entry.cs",
            "before": 'Run("text")',
            "after": 'Run("updated")',
            "version": old["version"],
            "requirements_version": old["requirements_version"],
        },
    )
    content = request(client, "GET", change_url + "/file", params={"path": "Entry.cs"}).json()
    require('Run("updated")' in content["content"], "isolated_edit_missing")
    text = request(
        client,
        "POST",
        "/api/handover/sources/text",
        status=201,
        json={
            "title": "Linux source record",
            "content": TEXT,
            "actor": "Linux fixture",
        },
    ).json()
    attached = request(
        client,
        "POST",
        "/api/handover/sources/import",
        status=201,
        params={"filename": "fixture.txt", "actor": "Linux fixture"},
        content=ATTACHMENT,
    ).json()
    return {
        "project_id": project["id"],
        "thread_id": thread["id"],
        "change_url": change_url,
        "text_id": text["id"],
        "attachment_id": attached["id"],
        "source_hash": tree_hash(source),
    }


def persistent(client, saved):
    base = f"/api/p/{saved['project_id']}"
    thread = request(client, "GET", base + f"/threads/{saved['thread_id']}").json()
    require(thread["title"] == "Linux persistent fixture", "thread_not_persistent")
    copy = request(client, "GET", saved["change_url"] + "/file", params={"path": "Entry.cs"}).json()
    require('Run("updated")' in copy["content"], "isolated_copy_not_persistent")
    text = request(client, "GET", f"/api/handover/records/{saved['text_id']}").json()
    require(text["payload"]["content"] == TEXT, "material_text_not_persistent")
    blob = request(client, "GET", f"/api/handover/sources/{saved['attachment_id']}/original")
    require(blob.content == ATTACHMENT, "attachment_not_persistent")
