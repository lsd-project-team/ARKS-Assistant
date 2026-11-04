"""完整代码工作真实Windows验收：原目录只读，合并和回退只写output内的工程。"""

import asyncio
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.config import Paths  # noqa: E402
from app.infrastructure.database.registry import Base  # noqa: E402
from app.infrastructure.database.session import Database  # noqa: E402
from app.modules.chat.repository import Repository  # noqa: E402
from app.modules.code_work.environment import EnvironmentWrite  # noqa: E402
from app.modules.code_work.files import code_manifest, snapshot  # noqa: E402
from app.modules.code_work.service import CodeWork  # noqa: E402
from app.modules.source_analysis.workspace import Workspace  # noqa: E402

FILE = "AKRS.ZX2200/DispenseSystem/Controllers/DispenseController.cs"
CASE = """var controller = AKRS.ZX2200.DispenseSystem.Models.System1Domain.GetInstance()
    .DispenseController;
controller.CloseDispensingElectric();
var method = typeof(AKRS.ZX2200.DispenseSystem.Modules.DispenseModule)
    .GetMethod("OpenDispensingElectric");
int calls = CountCalls(method, () => {
    controller.OpenDispensingElectric(); controller.OpenDispensingElectric();
});
Check(calls == 1, "连续两次打开只下发一次开阀，实际次数=" + calls);
Check(controller.IsDispensingElectricOpen(), "开阀状态保持开启");
controller.CloseDispensingElectric();
Check(!controller.IsDispensingElectricOpen(), "关闭操作保持有效");"""


async def verify(work, thread):
    await work.verify(thread)
    task = work.tasks[thread]
    await task
    job = work.status(thread)["verification"]
    print(
        json.dumps(
            {
                "revision": job["revision"],
                "status": job["status"],
                "error": job["error"],
                "steps": [
                    {"name": item["name"], "status": item["status"]} for item in job["steps"]
                ],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    return job


async def finish_merge(work, thread, output, test_origin, source, before, passed):
    plan = work.merge_preview(thread)
    await work.merge_verify(thread, plan["id"])
    await work.tasks["merge:" + thread]
    merged = work.merge_status(thread, plan["id"])
    (output / "merge-verified.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert merged["can_apply"], merged
    before_target = (test_origin / FILE).read_bytes()
    work.merge_apply(thread, plan["id"], {"name": "隔离自动验收"})
    assert b"IsDispensingElectricOpen" in (test_origin / FILE).read_bytes()
    assert not work.status(thread)["files"]
    work.merge_rollback(thread, plan["id"], {"name": "隔离自动验收"})
    assert (test_origin / FILE).read_bytes() == before_target
    assert code_manifest(source) == before, "原工程发生变化"
    (output / "complete.json").write_text(
        json.dumps(
            {
                "passed": True,
                "thread_id": thread,
                "plan_id": plan["id"],
                "original_unchanged": True,
                "requirement_checks": passed.get("requirements_results"),
                "desktop_checks": passed.get("desktop_results"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("PASS: full code-work flow, original source unchanged", flush=True)


async def main():
    source = Path("C:/Users/w/Desktop/AKRS.ZX2200/trunk")
    output = ROOT / "output/code-work-complete-20261104"
    output.mkdir(exist_ok=True)
    resume = "--resume" in sys.argv
    if (output / "data/app.sqlite3").exists() and not resume:
        raise RuntimeError("验收数据已存在；请先查看已有结果，不能重复启动或覆盖")
    before = code_manifest(source)
    test_origin = output / "test-origin"
    if not resume:
        test_origin.mkdir()
        snapshot(source, test_origin)
    paths = Paths(output / "data", test_origin)
    database = Database(paths.data / "app.sqlite3")
    Base.metadata.create_all(database.engine)
    repository = Repository(database, Workspace(test_origin).id)
    work = CodeWork(paths, repository)
    work.environment.save(
        EnvironmentWrite(
            source_root=str(test_origin),
            msbuild="D:/VisualStudio/2022/Community/MSBuild/Current/Bin/MSBuild.exe",
            timeout_seconds=900,
            version=work.environment.version(),
        )
    )
    if resume and "--merge-only" in sys.argv:
        identity = json.loads((output / "identity.json").read_text(encoding="utf-8"))
        assert before == identity["original_code"], "原工程与验收初始版本不同"
        thread = identity["thread_id"]
        status = work.status(thread)
        assert status["verification_current"] and status["verification"]["status"] == "passed", (
            "已有验证必须仍对应当前代码和宿主"
        )
        await finish_merge(
            work, thread, output, test_origin, source, before, status["verification"]
        )
        database.close()
        return
    if resume:
        identity = json.loads((output / "identity.json").read_text(encoding="utf-8"))
        assert before == identity["original_code"], "原工程与验收初始版本不同"
        thread = identity["thread_id"]
        for item in work.status(thread)["files"]:
            work.revert(thread, item["path"], item["version"])
    else:
        thread = repository.create_thread("完整副本流程真实验收")["id"]
        work.create(thread)
        work.set_requirement(
            thread,
            {
                "name": "开阀幂等与关闭回归",
                "expectation": "重复打开只调用底层一次，关闭和状态读取保持有效",
                "code": CASE,
            },
        )
    identity = {
        "thread_id": thread,
        "folder": str(work.folder(thread)),
        "test_origin": str(test_origin),
        "original_code": before,
    }
    (output / "identity.json").write_text(json.dumps(identity, indent=2), encoding="utf-8")
    failed = await verify(work, thread)
    (output / "requirement-before.json").write_text(
        json.dumps(failed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    if (
        failed["status"] != "failed"
        or failed["steps"][-1]["name"] != "本次需求断言验证"
        or "实际次数=2" not in failed["steps"][-1]["log"]
    ):
        raise AssertionError("预期原始非幂等方法被真实需求断言检出，请检查日志")
    content = (work.folder(thread) / "source" / FILE).read_text(encoding="utf-8-sig")
    target = re.search(
        r"public void OpenDispensingElectric\(\)\s*\{\s*"
        r"this\.DispenseModule\.OpenDispensingElectric\(\);\s*\}",
        content,
    )
    assert target, "未找到准确控制器方法"
    work.write(
        thread,
        FILE,
        "public void OpenDispensingElectric()\n        {\n"
        "            if (!this.DispenseModule.IsDispensingElectricOpen())\n"
        "                this.DispenseModule.OpenDispensingElectric();\n        }",
        work.read(thread, FILE)["version"],
        old_text=target[0],
        run_id="verification-fix",
    )
    work.set_desktop_flow(thread, True, work.status(thread)["revision"])
    passed = await verify(work, thread)
    (output / "requirement-and-desktop.json").write_text(
        json.dumps(passed, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert passed["status"] == "passed", passed["error"]
    await finish_merge(work, thread, output, test_origin, source, before, passed)
    database.close()


if __name__ == "__main__":
    asyncio.run(main())
