"""C# 仓库地图：提取符号与跨文件引用，按 token 预算裁剪。

参考 Aider 的 repo map 思路：给出全仓最关键的类/方法签名，让模型先看结构再决定读哪些文件。
"""

import re
from pathlib import Path

SKIP_DIRS = {".git", ".vs", "bin", "obj", "node_modules", "publish", "TestResults"}
KINDS = {
    "class_declaration": "class",
    "interface_declaration": "interface",
    "struct_declaration": "struct",
    "enum_declaration": "enum",
    "record_declaration": "record",
    "method_declaration": "method",
    "constructor_declaration": "ctor",
    "property_declaration": "property",
}
IGNORED_SUFFIX = (".g.cs", ".designer.cs", ".generated.cs")
MAX_FILE_BYTES = 200_000


def _parser():
    import tree_sitter_c_sharp
    from tree_sitter import Language, Parser

    return Parser(Language(tree_sitter_c_sharp.language()))


def _signature(text, node):
    lines = text[node.start_byte : node.end_byte].splitlines()
    if not lines:
        return ""
    first = re.sub(r"\s+", " ", lines[0]).strip()
    for marker in ("{", "=>"):
        if marker in first:
            first = first.split(marker, 1)[0].strip()
    return first[:140]


def _symbols(parser, text):
    tree = parser.parse(text.encode("utf-8"))
    pending = [tree.root_node]
    found = []
    while pending:
        node = pending.pop()
        kind = KINDS.get(node.type)
        if kind:
            name = node.child_by_field_name("name")
            if name:
                found.append(
                    {
                        "name": name.text.decode("utf-8", "replace"),
                        "kind": kind,
                        "line": node.start_point.row + 1,
                        "signature": _signature(text, node),
                    }
                )
        pending.extend(reversed(node.children))
    return found


def syntax_errors(text):
    """快速语法检查：返回 ERROR/MISSING 节点（行号 + 说明），不替代编译。"""
    parser = _parser()
    tree = parser.parse(text.encode("utf-8", "replace"))
    if not tree.root_node.has_error:
        return []
    errors = []
    pending = [tree.root_node]
    while pending and len(errors) < 10:
        node = pending.pop()
        if node.is_missing:
            errors.append(
                {
                    "line": node.start_point.row + 1,
                    "kind": "missing",
                    "message": f"缺少 {node.type}",
                }
            )
        elif node.is_error:
            snippet = text[node.start_byte : node.end_byte][:80].replace("\n", " ")
            errors.append(
                {
                    "line": node.start_point.row + 1,
                    "kind": "error",
                    "message": f"语法错误: {snippet}",
                }
            )
        pending.extend(reversed(node.children))
    return errors


def csharp_files(root, limit=400):
    root = Path(root)
    files = []
    for path in sorted(root.rglob("*.cs")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.name.endswith(IGNORED_SUFFIX):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        files.append(path)
        if len(files) >= limit:
            break
    return files


def build(root, max_tokens=1500):
    root = Path(root)
    files = csharp_files(root)
    if not files:
        return {"map": "（没有找到 C# 文件）", "files": 0, "symbols": 0, "shown": 0}
    parser = _parser()
    texts = {}
    definitions = {}
    for path in files:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        relative = path.relative_to(root).as_posix()
        texts[relative] = text
        definitions[relative] = _symbols(parser, text)

    references = {}
    for relative, symbols in definitions.items():
        others = [(name, body) for name, body in texts.items() if name != relative]
        for symbol in symbols:
            pattern = re.compile(rf"\b{re.escape(symbol['name'])}\b")
            hits = sum(1 for _, body in others if pattern.search(body))
            references[(relative, symbol["name"], symbol["line"])] = hits

    ranked = []
    for relative, symbols in definitions.items():
        for symbol in symbols:
            key = (relative, symbol["name"], symbol["line"])
            weight = 2 if symbol["kind"] in {"class", "interface", "record"} else 1
            public = 2 if "public" in symbol["signature"] else 0
            score = references.get(key, 0) * 3 + weight + public
            ranked.append((score, relative, symbol))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2]["line"]))

    char_budget = max(400, int(max_tokens) * 4)
    chosen = []
    used = 0
    for _, relative, symbol in ranked:
        line = f"  {symbol['signature']}"
        cost = len(line) + len(relative) + 4
        if chosen and used + cost > char_budget:
            continue
        chosen.append((relative, symbol))
        used += cost
        if used >= char_budget:
            break

    grouped = {}
    for relative, symbol in chosen:
        grouped.setdefault(relative, []).append(symbol)
    lines = [
        f"# C# 仓库地图：{len(files)} 个文件，{sum(len(v) for v in definitions.values())} 个符号，"
        f"展示 {len(chosen)} 个（按引用热度排序）"
    ]
    for relative in sorted(grouped):
        lines.append(f"{relative}:")
        for symbol in sorted(grouped[relative], key=lambda item: item["line"]):
            lines.append(f"  {symbol['signature']}")
    return {
        "map": "\n".join(lines),
        "files": len(files),
        "symbols": sum(len(value) for value in definitions.values()),
        "shown": len(chosen),
        "truncated": len(chosen) < sum(len(value) for value in definitions.values()),
    }
