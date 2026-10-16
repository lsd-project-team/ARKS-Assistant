"""等待并发名额时仍使用作业入队时的模型配置。"""

import asyncio
from types import SimpleNamespace

from app.modules.handover.application.extraction import HandoverAI


class JobRepository:
    def __init__(self):
        self.records = {
            "source": {"id": "source", "kind": "source", "state": "draft", "version": 1}
        }

    def get(self, identifier):
        return self.records[identifier]

    def create(self, kind, title, payload, actor, **options):
        row = {"id": "job", "kind": kind, "payload": {"status": "queued", **payload}}
        self.records[row["id"]] = row
        return row

    def job_status(self, identifier, **changes):
        self.records[identifier]["payload"].update(changes)
        return self.records[identifier]

    def complete_job(self, identifier, candidates):
        assert candidates == []
        return self.job_status(identifier, status="succeeded")


async def test_queued_extraction_keeps_its_original_configuration():
    repository = JobRepository()
    configuration = {"model": "before"}
    prepared, received = asyncio.Event(), []

    def factory():
        model = configuration["model"]
        prepared.set()

        async def generate(records, action):
            received.append((model, records[0]["version"], action))
            return SimpleNamespace(candidates=[])

        return generate

    ai = HandoverAI(lambda: repository, factory)
    ai.capacity = asyncio.Semaphore(0)
    job = ai.start(repository, "extract", ["source"], "记录人")
    try:
        await asyncio.wait_for(prepared.wait(), 2)
        assert job["payload"]["status"] == "queued"
        configuration["model"] = "after"
        ai.capacity.release()
        await asyncio.wait_for(ai.tasks[job["id"]], 2)
        assert received == [("before", 1, "extract")]
        assert job["payload"]["status"] == "succeeded"
    finally:
        await ai.shutdown()
