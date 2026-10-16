"""验证运行适配；基线在一次性副本执行，原版快照始终保持不可变。"""

import json

from app.modules.code_changes.files import digest, inventory, remove_copy, safe_path, tree_version
from app.modules.code_changes.policy import profile_version


def baseline_directory(service, row, verification_id):
    folder = service._folder(row)
    # 同一修改只能登记一个运行任务；短目录名避免 Windows 传统工具的长路径上限。
    temporary = safe_path(folder, "baseline")
    temporary.mkdir()
    try:
        required = sum(
            safe_path(folder / "base", name).stat().st_size
            for name in json.loads(row.manifest_json)
        )
        service.policy.check_space(service._scope(row.project_id), required)
        for relative, version in json.loads(row.manifest_json).items():
            source = safe_path(safe_path(folder, "base"), relative)
            content = source.read_bytes()
            if digest(content) != version:
                raise ValueError("原版本快照已改变，不能进行基线验证")
            target = safe_path(temporary, relative)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return temporary
    except BaseException:
        remove_copy(folder, temporary)
        raise


def execute(service, task, profile, work, log_path, purpose, run_host):
    temporary = None
    policy = service.policy.get()
    try:
        if purpose == "baseline":
            with service.database.session() as session:
                row = service._row(session, task.change_id, task.project_id)
                temporary = baseline_directory(service, row, task.verification_id)
            work = temporary
        before = inventory(work)
        executor = profile["executor"]
        if executor["kind"] == "container":
            from app.infrastructure.execution import run_container

            executor = {**executor, "owner_id": digest(str(service.paths.data).encode())}
            result = run_container(
                task,
                profile["argv"],
                work,
                log_path,
                profile["timeout_seconds"],
                executor,
                service.policy.limits(service._scope(task.project_id)),
            )
        else:
            result = run_host(
                task,
                profile["argv"],
                work,
                log_path,
                profile["timeout_seconds"],
                max_log_bytes=policy.max_log_mb * 1024 * 1024,
            )
        if purpose == "baseline" and inventory(work) != before:
            return "failed", result[1], "基线命令修改了受保护的源码，结果不能作为原版本基线"
        return result
    finally:
        if temporary is not None and temporary.exists():
            remove_copy(temporary.parent, temporary)


def baseline_current(service, session, row, profile):
    from sqlalchemy import select

    from app.modules.code_changes.models import VerificationRecord

    return session.scalar(
        select(VerificationRecord).where(
            VerificationRecord.project_id == row.project_id,
            VerificationRecord.change_id == row.id,
            VerificationRecord.purpose == "baseline",
            VerificationRecord.status == "passed",
            VerificationRecord.source_version == tree_version(json.loads(row.manifest_json)),
            VerificationRecord.profile_version == profile_version(profile),
        )
    )
