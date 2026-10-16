"""审核与交付包绑定同一份源码/补丁/验证身份，始终不向业务原件写入。"""

import io
import json
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.identifiers import now_iso
from app.modules.code_changes.files import changes_diff, export_patch, safe_path
from app.modules.code_changes.models import VerificationProfileRecord, VerificationRecord
from app.modules.code_changes.policy import profile_version
from app.modules.code_changes.requirements import requirements, scope_conflicts
from app.modules.code_changes.verification import baseline_current


def deliverable(service, session, row):
    service._editable(row)
    if row.status != "passed":
        raise ValueError("当前修改尚未验证通过，不能审核或交付")
    version = service._refresh(row)
    if service._source_conflicts(row):
        raise ValueError("原件已变化，请合并新基线后重新验证")
    if not requirements(row)["acceptance_criteria"]:
        raise ValueError("请先填写本次修改的验收标准")
    _, files, _ = changes_diff(
        safe_path(service._folder(row), "base"), service._work(row), json.loads(row.manifest_json)
    )
    if scope_conflicts(row, files):
        raise ValueError("修改超出约定范围，不能审核交付")
    verification = session.get(VerificationRecord, row.latest_verification_id)
    if (
        verification is None
        or verification.purpose != "change"
        or verification.status != "passed"
        or verification.change_version != version
    ):
        raise ValueError("本次修改验证已失效，请重新验证")
    profile_row = session.get(VerificationProfileRecord, (verification.profile_id, row.project_id))
    profile = service._profile(profile_row) if profile_row else None
    if profile is None or profile_version(profile) != verification.profile_version:
        raise ValueError("验证环境或命令已变化，请使用当前配置重新验证")
    if profile["baseline_required"] and baseline_current(service, session, row, profile) is None:
        raise ValueError("缺少当前源码及验证环境的通过基线，请先验证原版本")
    if service.policy.get().require_sandbox_delivery:
        evidence = json.loads(verification.executor_json).get("evidence", {})
        if profile["executor"]["kind"] != "container":
            raise ValueError("当前验证使用宿主机权限，未在沙箱验证，不能标记为可交付")
        if (
            not evidence.get("isolated")
            or evidence.get("protocol") != 2
            or not evidence.get("image_id")
        ):
            raise ValueError("缺少实际镜像与隔离执行证明，请重新验证")
    return verification, profile


def review_change(service, identifier, version, notes, actor):
    with service.lock, service.database.session.begin() as session:
        row = service._row(session, identifier)
        verification, profile = deliverable(service, session, row)
        if row.change_version != version:
            raise ValueError("修改版本已变化，请重新查看差异后审核")
        row.review_json = json.dumps(
            {
                "change_version": version,
                "verification_id": verification.id,
                "profile_version": profile_version(profile),
                "actor": actor,
                "notes": notes,
                "reviewed_at": now_iso(),
            },
            ensure_ascii=False,
        )
        row.updated_at = now_iso()
    return service.get(identifier)


def delivery_package(service, identifier):
    with service.lock, service.database.session.begin() as session:
        row = service._row(session, identifier)
        verification, profile = deliverable(service, session, row)
        review = json.loads(row.review_json or "{}")
        if (
            review.get("change_version") != row.change_version
            or review.get("verification_id") != verification.id
        ):
            raise ValueError("当前版本尚未审核，仍可导出草稿补丁供核对")
        patch = export_patch(
            safe_path(service._folder(row), "base"),
            service._work(row),
            json.loads(row.manifest_json),
        )
        manifest = {
            "schema_version": 1,
            "project_id": row.project_id,
            "change_id": row.id,
            "title": row.title,
            "goal": row.goal,
            **requirements(row),
            "change_version": row.change_version,
            "source_version": verification.source_version,
            "verification_id": verification.id,
            "verification": verification_metadata(verification),
            "baseline": verification_metadata(baseline_current(service, session, row, profile)),
            "profile": profile,
            "review": review,
            "generated_at": now_iso(),
            "limits": "命令通过不代表真实设备、工艺或现场验收完成",
        }
        result = io.BytesIO()
        with ZipFile(result, "w", compression=ZIP_DEFLATED) as archive:
            archive.writestr("changes.patch", patch)
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            archive.writestr("README.md", INSTRUCTIONS)
        # 在导出完成后再核对，防止读取补丁时外部进程改动副本。
        if service._refresh(row) != manifest["change_version"] or service._source_conflicts(row):
            raise ValueError("生成交付包期间源码发生变化，请重新验证并审核")
        row.delivered_at, row.updated_at = now_iso(), now_iso()
        return result.getvalue()


def verification_metadata(record):
    """离线交付附可核对的结果身份；日志或命令的额外输出不打包传播。"""
    if record is None:
        return None
    keys = (
        "id",
        "status",
        "exit_code",
        "purpose",
        "change_version",
        "source_version",
        "profile_version",
        "started_at",
        "ended_at",
    )
    return {
        **{key: getattr(record, key) for key in keys},
        "executor": json.loads(record.executor_json),
    }


INSTRUCTIONS = """# 代码交付包

先核对 manifest.json 中的项目、源码版本、需求验收、验证记录和审核人。
本包不会自动写回原项目或提交代码。先在正确版本的独立工作分支中检查：

    git apply --check changes.patch
    git apply changes.patch

重新执行项目构建与测试并由项目人员复核。应用后若尚未修改同一区域，可检查并回退：

    git apply --reverse --check changes.patch
    git apply --reverse changes.patch

如果后续已有其他改动，使用项目Git历史按具体提交回退并处理冲突，勿覆盖未提交工作。
没有Git的源码先做完整备份，并使用支持Git补丁的工具核对应用；本系统不自动覆盖原件。
设备动作、联锁及工艺结果须另外现场验收。
"""
