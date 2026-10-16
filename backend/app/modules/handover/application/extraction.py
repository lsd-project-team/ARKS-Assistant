"""AI 作业用例：固定输入、限制并发、可取消和恢复。"""

import asyncio

from app.modules.handover.application.ports import CandidateGeneratorFactory, RepositoryFactory
from app.modules.handover.domain.schemas import validate_payload


class HandoverAI:
    def __init__(
        self, repository_factory: RepositoryFactory, generator_factory: CandidateGeneratorFactory
    ):
        self.repository_factory = repository_factory
        self.generator_factory = generator_factory
        self.tasks = {}
        self.capacity = asyncio.Semaphore(2)

    def recover(self):
        store = self.repository_factory()
        for identifier in store.pending_job_ids():
            self._set(
                store,
                identifier,
                status="interrupted",
                error="服务重启中断了作业；可重试，已保存的输入版本仍可查看",
            )

    def _set(self, store, identifier, **changes):
        return store.job_status(identifier, **changes)

    def start(self, store, action, record_ids, actor):
        if (
            action not in {"extract", "plan", "framework", "training"}
            or not record_ids
            or len(record_ids) > 20
        ):
            raise ValueError("请选择 1–20 条资料及有效的 AI 操作")
        records = [store.get(identifier) for identifier in dict.fromkeys(record_ids)]
        if any(
            row["kind"] in {"job", "candidate", "package"} or row["state"] == "archived"
            for row in records
        ):
            raise ValueError("请选择未归档的原始资料、访谈或业务记录")
        if action == "plan" and sum(row["kind"] == "task" for row in records) != 1:
            raise ValueError("生成接续计划时请只选择一个工作项，可附上基线与资料")
        job = store.create(
            "job",
            {
                "extract": "提取交接候选",
                "plan": "生成接续计划候选",
                "framework": "整理框架候选",
                "training": "整理培训候选",
            }[action],
            {
                "action": action,
                "record_ids": [row["id"] for row in records],
                "input_versions": {row["id"]: row["version"] for row in records},
            },
            actor,
            internal=True,
        )
        self.tasks[job["id"]] = asyncio.create_task(self._run(store, job["id"], records))
        return job

    async def _run(self, store, identifier, records):
        try:
            # 入队时固定模型配置，等待并发名额期间切换设置不改变本次作业。
            generate = self.generator_factory()
            async with self.capacity:
                self._set(store, identifier, status="running")
                job = store.get(identifier)
                result = await generate(records, job["payload"]["action"])
                inputs = {row["id"]: row["version"] for row in records}
                candidates = []
                expected = {"plan": "plan", "framework": "framework", "training": "training"}.get(
                    job["payload"]["action"]
                )
                # 先校验全部候选，再持久化，避免失败重试时留下半批结果。
                for item in result.candidates:
                    value = item.payload.model_dump()
                    if expected and value["target_kind"] != expected:
                        raise ValueError("模型返回了错误的候选类型")
                    if not value["evidence"] or any(
                        inputs.get(ref["record_id"]) != ref["version"] for ref in value["evidence"]
                    ):
                        raise ValueError("AI 返回了不存在或版本不符的来源，结果已拒绝")
                    value["origin"] = "ai"
                    value["proposed"]["origin"] = "ai"
                    value["proposed"]["evidence"] = value["evidence"]
                    from app.modules.handover.domain.rules import validate_links

                    proposed = validate_payload(value["target_kind"], value["proposed"])
                    all_rows = {row["id"]: row for row in store.list()}
                    validate_links(value["target_kind"], proposed, all_rows, store.get)
                    candidates.append((item.title, value))
                store.complete_job(identifier, candidates)
        except asyncio.CancelledError:
            self._set(
                store, identifier, status="cancelled", error="用户取消或服务关闭，原始资料已保留"
            )
        except Exception as error:
            detail = (
                "模型响应超时；可以重试，或先手动整理已保存的资料"
                if isinstance(error, TimeoutError)
                else str(error)
            )
            self._set(store, identifier, status="failed", error=detail)
        finally:
            self.tasks.pop(identifier, None)

    async def cancel(self, store, identifier):
        job = store.get(identifier)
        if job["kind"] != "job":
            raise ValueError("请选择 AI 作业")
        task = self.tasks.get(identifier)
        if task and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            current = store.get(identifier)
            if current["payload"]["status"] in {"queued", "running"}:
                self._set(store, identifier, status="cancelled", error="用户已取消运行")
            self.tasks.pop(identifier, None)
        return store.get(identifier)

    async def shutdown(self):
        for task in list(self.tasks.values()):
            task.cancel()
        await asyncio.gather(*list(self.tasks.values()), return_exceptions=True)
