"""知识引用使用实际返回的标题，未知链接不能假装具有检索依据。"""

import re

LINK = re.compile(r"\[([^\]\n]*)\]\(((?:debug-issue|handover-source):[^\s)]+)\)")
CODE = re.compile(r"(?ms)^[ \t]*(`{3,}|~{3,})[^\n]*\n.*?^[ \t]*\1[ \t]*$|`+[^`\n]*`+")
BARE = re.compile(r"(?:debug-issue:[\w-]+/\d+|handover-source:[\w-]+/\d+#L\d+(?:-L?\d+)?)")


def canonical_knowledge_citations(answer, references):
    code_spans = [match.span() for match in CODE.finditer(answer)]
    links = list(LINK.finditer(answer))

    def replacement(target, label=None):
        prefix, _, lines = target.partition("#L")
        for row in references:
            citation_prefix, _, citation_lines = row["citation"].partition("#L")
            if prefix != citation_prefix:
                continue
            if lines:
                requested = re.fullmatch(r"(\d+)(?:-L?(\d+))?", lines)
                returned = re.fullmatch(r"(\d+)(?:-L?(\d+))?", citation_lines)
                if not requested or not returned:
                    continue
                start, end = int(requested[1]), int(requested[2] or requested[1])
                if not int(returned[1]) <= start <= end <= int(returned[2] or returned[1]):
                    continue
            title = row["title"].replace("[", "（").replace("]", "）").replace("\n", " ")
            label = title if target.startswith("debug-issue:") else f"{title} · v{row['version']}"
            return f"[{label}]({target})"
        return f"{label or '资料'}（资料引用未核对）" if label is not None else target

    edits = []
    for match in links:
        if not any(start <= match.start() < end for start, end in code_spans):
            edits.append((*match.span(), replacement(match[2], match[1])))
    protected = [*code_spans, *(match.span() for match in links)]
    for match in BARE.finditer(answer):
        if not any(start <= match.start() < end for start, end in protected):
            edits.append((*match.span(), replacement(match[0])))
    for start, end, value in sorted(edits, reverse=True):
        answer = answer[:start] + value + answer[end:]
    return answer
