"""应用用例依赖的记录仓储接口，由数据库适配器实现。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import Any, Protocol


class RecordRepository(Protocol):
    lock: AbstractContextManager

    def list(self) -> list[dict]: ...

    def get(self, identifier: str, version: int | None = None) -> dict: ...

    def create(self, kind, title, payload, actor, **options) -> dict: ...

    def update(self, identifier, body, **options) -> dict: ...

    def action(self, identifier, action, body) -> dict: ...

    def history(self, identifier) -> list[dict]: ...

    def events(self) -> list[dict]: ...

    def blob(self, identifier) -> dict[str, Any]: ...

    def promote(self, identifier, body, title, proposed) -> dict: ...

    def debug_rows(self, include_archived: bool = False) -> list[dict]: ...

    def pending_job_ids(self) -> list[str]: ...

    def job_status(self, identifier: str, **changes) -> dict: ...

    def complete_job(self, identifier: str, candidates: list[tuple[str, dict]]) -> dict: ...


RepositoryFactory = Callable[[], RecordRepository]


class MaterialParser(Protocol):
    def parse(self, data: bytes, filename: str) -> dict: ...

    def snapshot(self, data: bytes, path: str) -> dict: ...


class PackageExporter(Protocol):
    def render(self, package: dict, records: list[dict], blobs: dict, zipped: bool) -> bytes: ...


class CandidateGenerator(Protocol):
    async def __call__(self, records: list[dict], action: str) -> Any: ...


CandidateGeneratorFactory = Callable[[], CandidateGenerator]
