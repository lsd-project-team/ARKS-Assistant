"""代码副本测试的最小原工程夹具。"""

from app.modules.code_work.environment import EnvironmentWrite
from app.modules.code_work.files import PROJECT
from app.modules.code_work.service import CodeWork

FILE = f"{PROJECT}/Main/Example.cs"


def make_work(services, tmp_path):
    paths, _, _, repository, *_ = services
    source = tmp_path / "simulation-source"
    app = source / PROJECT
    (app / "Main").mkdir(parents=True)
    (app / "Infrastructure/Simulation/Tests").mkdir(parents=True)
    (app / "bin/Debug/Settings").mkdir(parents=True)
    (app / "bin/Debug/runtime.dll").write_bytes(b"test-dependency")
    (app / "bin/Debug/Settings/private.json").write_text("private", encoding="utf-8")
    for path, content in {
        "Main/Example.cs": "class Example {\r\n // 中文\r\n int Value = 1;\r\n}\r\n",
        "Program.cs": "class Program {}",
        f"{PROJECT}.csproj": "<Project />",
        "App.config": "<configuration />",
        "Infrastructure/Simulation/OriginalSimulation.cs": "class OriginalSimulation {}",
    }.items():
        (app / path).write_bytes(content.encode("utf-8"))
    service = CodeWork(paths, repository)
    service.environment.save(
        EnvironmentWrite(source_root=str(source), version=service.environment.version())
    )
    thread = repository.create_thread("代码修改")
    service.create(thread["id"])
    return service, thread["id"], app
