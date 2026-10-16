"""自动检查仅证明机械事实，语义质量始终交给独立评审。"""

import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from app.modules.code_changes.files import inventory, safe_path
from app.modules.source_analysis.evidence import SourceEvidence


def check(name, status, evidence):
    return {"name": name, "status": status, "evidence": evidence}


def source_checks(workspace, answer, events, before):
    evidence = SourceEvidence(workspace, lambda *_: None, required=True)
    evidence.reads = [row["payload"] for row in events if row["kind"] == "source_evidence"]
    validation = evidence.check(answer)
    try:
        current = inventory(workspace.root)
    except (OSError, ValueError) as error:
        return [check("source_integrity", "failed", {"error": str(error)})]
    versions_valid = all(before.get(row["path"]) == row["version"] for row in evidence.reads)
    return [
        check(
            "source_integrity",
            "pass" if current == before else "failed",
            {
                "added": sorted(current.keys() - before.keys()),
                "removed": sorted(before.keys() - current.keys()),
                "changed": sorted(
                    path for path in current.keys() & before.keys() if current[path] != before[path]
                ),
            },
        ),
        check(
            "current_citations",
            "pass" if validation["passed"] and versions_valid else "failed",
            validation,
        ),
    ]


def replay_patch(base, work, patch):
    executable = shutil.which("git")
    if not executable:
        return check("patch_replay", "unknown", "没有Git，未检查应用及反向回退")
    baseline, expected = inventory(base), inventory(work)
    with tempfile.TemporaryDirectory(prefix="quality-patch-") as temporary:
        target = Path(temporary)
        for relative in baseline:
            file = safe_path(target, relative)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(safe_path(base, relative).read_bytes())
        for arguments in (["--check"], [], ["--reverse", "--check"], ["--reverse"]):
            result = subprocess.run(
                [executable, "-c", "core.autocrlf=false", "apply", *arguments, "-"],
                cwd=target,
                input=patch.encode("utf-8"),
                capture_output=True,
                check=False,
                timeout=15,
            )
            if result.returncode:
                return check(
                    "patch_replay",
                    "failed",
                    {"arguments": arguments, "stderr": result.stderr.decode(errors="replace")},
                )
            if not arguments and inventory(target) != expected:
                return check("patch_replay", "failed", "应用后的文件哈希与隔离副本不同")
        return check(
            "patch_replay",
            "pass" if inventory(target) == baseline else "failed",
            {
                "applied_matches_work": True,
                "reversed_matches_base": inventory(target) == baseline,
            },
        )


def change_evidence(service):
    results = []
    for change in service.list():
        diff = service.diff(change["id"])
        patch = service.export(change["id"])
        with service.database.session() as session:
            row = service._row(session, change["id"])
            folder = service._folder(row)
            replay = (
                replay_patch(safe_path(folder, "base"), service._work(row), patch)
                if diff["files"]
                else check("patch_replay", "failed", "副本没有实际修改")
            )
            baseline_version = json.loads(row.manifest_json)
        results.append(
            {
                "change": change,
                "diff": diff,
                "patch": patch,
                "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
                "patch_replay": replay,
                "baseline_sources": baseline_version,
                "verifications": service.verification_history(change["id"])["verifications"],
            }
        )
    return results
