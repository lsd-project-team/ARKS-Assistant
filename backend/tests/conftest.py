import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import Paths, SettingsStore
from app.infrastructure.database.registry import Base
from app.infrastructure.database.session import Database
from app.modules.auth.models import Account
from app.modules.chat.repository import Repository
from app.modules.memory.service import MemoryService
from app.modules.source_analysis.workspace import Workspace


@pytest.fixture
def source_iteration_limit(monkeypatch):
    """显式压低分析额度，让保护路径用例不依赖生产环境的默认展开能力。"""
    from app.modules.action_timing import source_estimator
    from app.modules.action_timing.source_budget import IterationBudget

    def apply(limit):
        monkeypatch.setattr(
            source_estimator, "IterationBudget", lambda: IterationBudget(limit=limit)
        )

    return apply


@pytest.fixture(autouse=True)
def authenticate_business_clients(request, monkeypatch, tmp_path):
    """原有业务回归通过真实管理员登录；认证用例自行控制所有登录状态。"""
    if request.node.get_closest_marker("authentication"):
        return
    original = TestClient.__enter__

    def enter(client):
        result = original(client)
        auth = getattr(client.app.state, "auth", None)
        if not auth:
            return result
        if not auth.initial_accounts.parent.is_relative_to(tmp_path):
            raise RuntimeError("测试账号只能建立在当前用例的临时数据目录")
        password = "test-admin-only-2026"
        with auth.database.session.begin() as session:
            account = session.scalar(select(Account).where(Account.username == "test-admin"))
            if not account:
                session.add(
                    Account(
                        username="test-admin",
                        display_name="测试管理员",
                        role="admin",
                        password_hash=auth.hasher.hash(password),
                    )
                )
        response = client.post(
            "/api/auth/login", json={"username": "test-admin", "password": password}
        )
        assert response.status_code == 200, response.text
        client.headers["X-Arks-CSRF"] = response.json()["csrf_token"]
        return result

    monkeypatch.setattr(TestClient, "__enter__", enter)


@pytest.fixture
def services(tmp_path):
    root = tmp_path / "trunk"
    root.mkdir()
    (root / "Program.cs").write_text(
        "class Program {\n static void Main() {}\n}\n", encoding="utf-8"
    )
    paths = Paths(tmp_path / "data", root)
    database = Database(paths.data / "app.sqlite3")
    Base.metadata.create_all(database.engine)
    workspace = Workspace(root)
    repository = Repository(database, workspace.id)
    memory = MemoryService(paths, database, workspace)
    yield paths, database, workspace, repository, memory, SettingsStore(paths)
    database.close()
