import pytest

from app.config import Paths, SettingsStore
from app.database import Database
from app.memory import MemoryService
from app.models import Base
from app.repository import Repository
from app.workspace import Workspace


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
