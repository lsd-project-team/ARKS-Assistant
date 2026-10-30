"""业务回归显式选择项目，禁止依赖已移除的无项目旧接口。"""


def project_api(client, path):
    return f"/api/p/{client.app.state.projects.default_id}{path}"
