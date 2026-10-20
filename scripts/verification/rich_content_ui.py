"""隔离的真实聊天页面验收入口：真实认证/API/SSE/数据库，模型使用可控替身。"""

import argparse
import asyncio
import json
import sys
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

import uvicorn  # noqa: E402

from app.agents.runtime.engine import AgentRuntime  # noqa: E402
from app.bootstrap import create_app  # noqa: E402
from app.core.config import Paths  # noqa: E402
from app.modules.auth.context import request_identity  # noqa: E402
from app.modules.auth.models import Account, public_account  # noqa: E402
from app.modules.source_analysis.evidence import SourceEvidence, source_excerpt  # noqa: E402


def fixture_answer():
    fixture = ROOT / "frontend/tests/chat/fixtures/rich-content.json"
    document = json.loads(fixture.read_text(encoding="utf-8"))
    return (
        "# 执行引擎分析\n\n以下内容用于界面和交互验收。\n\n```rich-content\n"
        + json.dumps(document, ensure_ascii=False)
        + "\n```\n\n已保留源码证据，可按需查看实现。"
    )


async def exercise_reply(self, run, emit):
    question = self.repository.message(run["message_id"])["content"]
    ledger = SourceEvidence(self.workspace, emit)
    ledger.record(source_excerpt(self.workspace, "Program.cs", 2, 2))
    emit("stage", {"stage": "generating"})
    answer = fixture_answer()
    if "停止" in question:
        emit("token", {"text": answer[:160]})
        await asyncio.Event().wait()
    if "异常" in question:
        emit("token", {"text": answer[:160]})
        raise ValueError("界面验收中的可控失败")
    for offset in range(0, len(answer), 28):
        emit("token", {"text": answer[offset : offset + 28]})
        await asyncio.sleep(0.035)
    return answer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8876)
    parser.add_argument("--ui-port", type=int, default=5179)
    args = parser.parse_args()
    destination = Path(tempfile.mkdtemp(prefix="rich-ui-", dir=ROOT / "output"))
    vite_config = destination / "vite.config.mjs"
    vite_config.write_text(
        "import config from "
        + json.dumps((ROOT / "frontend/vite.config.ts").as_posix())
        + ";\n"
        + "export default {...config, server:{host:'127.0.0.1',strictPort:true,port:"
        + str(args.ui_port)
        + ",proxy:{'/api':"
        + json.dumps(f"http://127.0.0.1:{args.port}")
        + "}}};\n",
        encoding="utf-8",
    )
    source = destination / "source"
    source.mkdir()
    (source / "Program.cs").write_text(
        "class Program {\n static void Main() {}\n}\n", encoding="utf-8"
    )
    application = create_app(Paths(destination / "data", source))
    original_lifespan = application.router.lifespan_context
    AgentRuntime.execute = exercise_reply

    @asynccontextmanager
    async def isolated_lifespan(app):
        async with original_lifespan(app):
            auth = app.state.auth
            with auth.database.session.begin() as session:
                account = Account(
                    username="rich-test",
                    display_name="界面验收",
                    role="user",
                    password_hash=auth.hasher.hash("local-rich-ui-test"),
                )
                session.add(account)
                session.flush()
                identity = public_account(account)
            token = request_identity.set({"user": identity})
            try:
                app.state.projects.account_defaults.ensure(identity)
                services = app.state.projects.services(app.state.projects.list()[0]["id"])
                repository = services.repository
                run = repository.create_run(None, "组件与源码验收", [])
                ledger = SourceEvidence(
                    services.workspace,
                    lambda kind, payload: repository.event(run["id"], kind, payload),
                )
                ledger.record(source_excerpt(services.workspace, "Program.cs", 2, 2))
                repository.finish(run["id"], fixture_answer())
                old = repository.create_run(None, "Markdown 与异常兼容验收", [])
                repository.finish(
                    old["id"],
                    "## 历史技术回答\n\n普通段落，参数20~30g。\n\n"
                    "- 主项\n  - 子项\n\n- [x] 已完成\n\n"
                    "| 参数 | 数值 |\n| --- | ---: |\n| 等待时间 | 0 |\n\n"
                    "```python\nprint('安全代码示例')\n```\n\n"
                    '```rich-content\n{"version":9,"blocks":[]}\n```\n\n后续文字仍可阅读。',
                )
            finally:
                request_identity.reset(token)
            print(f"隔离数据目录：{destination}", flush=True)
            print(f"Vite 配置：{vite_config}", flush=True)
            yield

    application.router.lifespan_context = isolated_lifespan
    uvicorn.run(application, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
