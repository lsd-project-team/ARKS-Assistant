"""Agent检索先覆盖多个实现文件；片段只作定位，不代替实际源码读取。"""

import re
from itertools import islice
from pathlib import PurePosixPath

ENTRY = re.compile(r"(?:actionnode|workflow|task|flow)(?:\.[^.]+)?\.cs$", re.I)
GENERATED = re.compile(r"(?:\.designer|\.generated|\.g)\.cs$", re.I)


def file_priority(path, query):
    normalized = path.casefold()
    file = PurePosixPath(normalized)
    parts = set(file.parts)
    # 依据真实路径分类，不把某个项目、业务词或方法名硬编码成“正确答案”。
    generated = bool(GENERATED.search(normalized))
    auxiliary = bool(parts & {"test", "tests", "experiment", "experiments"})
    literal_path = query.casefold() in normalized
    entry = bool(ENTRY.search(file.name)) and not generated and not auxiliary
    code = file.suffix in {".cs", ".py", ".ts", ".tsx", ".js", ".cpp", ".h", ".java"}
    return (not literal_path, generated or auxiliary, not entry, not code, normalized)


def select_matches(rows, query, limit, *, diverse=False):
    if not diverse:
        matches = list(islice(rows, max(0, limit) + 1))
        return {"matches": matches[:limit], "truncated": len(matches) > limit}

    files, count = {}, 0
    per_file = min(4, max(1, limit))
    for row in rows:
        count += 1
        bucket = files.setdefault(row["path"], [])
        if len(bucket) < per_file:
            bucket.append(row)
    paths = sorted(files, key=lambda path: file_priority(path, query))
    matches = []
    # 先给每个文件一个定位点，再补第二、第三个片段，保留可重复的顺序。
    for index in range(per_file):
        for path in paths:
            if len(matches) >= limit:
                return {"matches": matches, "truncated": count > len(matches)}
            if index < len(files[path]):
                matches.append(files[path][index])
    return {"matches": matches, "truncated": count > len(matches)}
