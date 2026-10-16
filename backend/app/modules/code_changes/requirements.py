"""把需求验收与允许修改范围绑定到副本，空范围沿用项目内编辑能力。"""

import fnmatch
import json

from app.modules.code_changes.schemas import ChangeWrite


def requirement_payload(body: ChangeWrite):
    return body.model_dump(include={"acceptance_criteria", "constraints", "allowed_paths"})


def requirements(row):
    return {
        "acceptance_criteria": [],
        "constraints": "",
        "allowed_paths": [],
        **json.loads(row.requirements_json or "{}"),
    }


def path_allowed(row, path):
    scopes = requirements(row)["allowed_paths"]
    return not scopes or any(
        fnmatch.fnmatchcase(path, pattern)
        or pattern.startswith("**/")
        and fnmatch.fnmatchcase(path, pattern[3:])
        for pattern in scopes
    )


def scope_conflicts(row, files):
    return [file["path"] for file in files if not path_allowed(row, file["path"])]
