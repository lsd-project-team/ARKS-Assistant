"""每个分块独立提交，取消和供应商失败不丢失此前分析。"""

import asyncio
import json

from app.core.config import dump_json
from app.core.identifiers import now_iso
from app.modules.source_analysis.reading import sources
from app.modules.source_analysis.reading.models import (
    ProjectReadingDocument,
    ProjectReadingFile,
)
from app.modules.source_analysis.reading.schemas import ReadingAnalysis
from app.modules.source_analysis.workspace import content_version


def file_row(service, session, job_id, project_id, file_id):
    row = session.scalar(
        service._query(ProjectReadingFile, project_id).where(
            ProjectReadingFile.id == file_id, ProjectReadingFile.job_id == job_id
        )
    )
    if row is None:
        raise FileNotFoundError("阅读文件不存在")
    return row


def update_status(service, job_id, project_id, status, error=""):
    with service.lock, service.database.session.begin() as session:
        job = service._job(session, job_id, project_id)
        job.status, job.error, job.updated_at = status, error, now_iso()
        for file in service._files(session, job_id, project_id):
            if file.status == "reading":
                file.status = "pending"


async def run_reading(service, job_id, project_id, analyzer, max_chunks):
    counter = {"used": 0}
    try:
        with service.lock, service.database.session() as session:
            files = service._files(session, job_id, project_id)
        for file in files:
            if file.status == "excluded" or file.analyzed:
                continue
            try:
                await read_file(
                    service,
                    job_id,
                    project_id,
                    file,
                    analyzer,
                    max_chunks,
                    counter,
                )
            except (OSError, ValueError, UnicodeError, TimeoutError) as error:
                mark_failure(
                    service, job_id, project_id, file.id, str(error) or type(error).__name__
                )
            except Exception as error:
                # 模型协议、网络和结构化输出错误只影响此文件；下一次 start 可重试。
                mark_failure(
                    service,
                    job_id,
                    project_id,
                    file.id,
                    f"分析失败：{type(error).__name__}: {str(error)[:500]}",
                )
            if counter["used"] >= max_chunks:
                with service.lock, service.database.session() as session:
                    pending = any(
                        not row.analyzed and row.status != "excluded"
                        for row in service._files(session, job_id, project_id)
                    )
                if pending:
                    update_status(service, job_id, project_id, "paused", "本轮分块预算已用完")
                    return
        with service.lock, service.database.session() as session:
            files = service._files(session, job_id, project_id)
            partial = any(row.status == "failed" or row.stale for row in files)
            failed = bool(files) and all(row.status == "failed" for row in files)
        update_status(
            service,
            job_id,
            project_id,
            "failed" if failed else "partial" if partial else "completed",
        )
    except asyncio.CancelledError:
        state = service.stop_status.get((project_id, job_id), "interrupted")
        update_status(service, job_id, project_id, state)
        raise
    except Exception as error:
        update_status(service, job_id, project_id, "failed", str(error)[:1000])


def mark_failure(service, job_id, project_id, file_id, error):
    with service.lock, service.database.session.begin() as session:
        file = file_row(service, session, job_id, project_id, file_id)
        file.status, file.error, file.analyzed, file.reviewed = "failed", error[:1000], False, False


async def read_file(service, job_id, project_id, file, analyzer, budget, counter):
    current = await asyncio.to_thread(sources.describe, service.workspace, file.path)
    if current["source_version"] != file.source_version:
        invalidate_file(service, job_id, project_id, file.id)
        return
    iterator = sources.chunks(service.workspace, file.path, file.encoding)
    try:
        chunk = next(iterator, None)
        while chunk is not None:
            following = next(iterator, None)
            if chunk["index"] >= file.next_chunk:
                if counter["used"] >= budget:
                    return
                metadata = {
                    "project_id": project_id,
                    "job_id": job_id,
                    "path": file.path,
                    "module": file.module,
                    "source_version": file.source_version,
                    "start_line": chunk["start_line"],
                    "end_line": chunk["end_line"],
                    "chunk_index": chunk["index"],
                    "text_sha256": content_version(chunk["text"].encode()),
                }
                with service.lock, service.database.session.begin() as session:
                    row = file_row(service, session, job_id, project_id, file.id)
                    row.status, row.error = "reading", ""
                    row.read_chunks = max(row.read_chunks, chunk["index"] + 1)
                    row.read = following is None
                # 仅真实读到的正文交给注入的分析器，不以扫描和索引冒充理解。
                counter["used"] += 1
                async with asyncio.timeout(180):
                    result = await analyzer(chunk["text"], metadata)
                analysis = parse_analysis(result, metadata)
                current = await asyncio.to_thread(sources.describe, service.workspace, file.path)
                if current["source_version"] != file.source_version:
                    invalidate_file(service, job_id, project_id, file.id)
                    return
                save_analysis(service, job_id, project_id, file.id, metadata, analysis)
            chunk = following
        with service.lock, service.database.session.begin() as session:
            row = file_row(service, session, job_id, project_id, file.id)
            row.status, row.error, row.stale = "analyzed", "", False
            row.read, row.analyzed = True, True
            current_documents = service._documents(session, job_id, project_id)
            for document in current_documents:
                if document.file_id == file.id and document.chunk_index >= row.next_chunk:
                    document.latest = False
            row.reviewed = all(
                document.status == "approved"
                for document in current_documents
                if document.file_id == file.id and document.latest
            )
    finally:
        iterator.close()


def invalidate_file(service, job_id, project_id, file_id):
    with service.lock, service.database.session.begin() as session:
        file = file_row(service, session, job_id, project_id, file_id)
        file.status, file.error, file.stale = "stale", "源码版本已变化，请刷新任务", True
        file.analyzed, file.reviewed = False, False
        for document in service._documents(session, job_id, project_id):
            if document.file_id == file_id:
                document.status = "stale"


def parse_analysis(result, metadata):
    if isinstance(result, str):
        result = json.loads(result)
    analysis = (
        result if isinstance(result, ReadingAnalysis) else ReadingAnalysis.model_validate(result)
    )
    for reference in analysis.references:
        if (
            reference.path != metadata["path"]
            or reference.source_version != metadata["source_version"]
            or reference.start_line < metadata["start_line"]
            or reference.end_line > metadata["end_line"]
        ):
            raise ValueError("分析器引用了本分块未读取的源码")
    return analysis


def save_analysis(service, job_id, project_id, file_id, metadata, analysis):
    with service.lock, service.database.session.begin() as session:
        file = file_row(service, session, job_id, project_id, file_id)
        query = service._query(ProjectReadingDocument, project_id).where(
            ProjectReadingDocument.job_id == job_id,
            ProjectReadingDocument.file_id == file_id,
            ProjectReadingDocument.chunk_index == metadata["chunk_index"],
        )
        previous = list(session.scalars(query))
        for document in previous:
            document.latest = False
        version = max((row.version for row in previous), default=0) + 1
        references = [row.model_dump() for row in analysis.references]
        actual = {
            key: metadata[key]
            for key in (
                "path",
                "source_version",
                "start_line",
                "end_line",
                "chunk_index",
                "text_sha256",
            )
        }
        references.append(actual)
        session.add(
            ProjectReadingDocument(
                project_id=project_id,
                job_id=job_id,
                file_id=file_id,
                path=file.path,
                module=file.module,
                chunk_index=metadata["chunk_index"],
                version=version,
                source_version=metadata["source_version"],
                start_line=metadata["start_line"],
                end_line=metadata["end_line"],
                summary=analysis.summary,
                entrypoints_json=dump_json(analysis.entrypoints),
                dependencies_json=dump_json(analysis.dependencies),
                unknowns_json=dump_json(analysis.unknowns),
                references_json=dump_json(references),
            )
        )
        file.next_chunk = metadata["chunk_index"] + 1
        service._job(session, job_id, project_id).updated_at = now_iso()
