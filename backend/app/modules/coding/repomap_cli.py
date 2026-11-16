"""repo_map 子进程入口：tree-sitter 解析异常时隔离崩溃，不影响主服务。

用法：
  repomap_cli <root> <max_tokens> [files.json]   生成地图
  repomap_cli --probe <root> <files.json>        只解析文件，用于定位崩溃文件
"""

import json
import sys
from pathlib import Path

from app.modules.coding import repomap


def _load_files(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def probe(root, files):
    parser = repomap._parser()
    for relative in files:
        path = (root / relative).resolve()
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        repomap._symbols(parser, text)
    print(json.dumps({"ok": True, "files": len(files)}))


def main():
    args = sys.argv[1:]
    if args and args[0] == "--probe":
        probe(Path(args[1]), _load_files(args[2]) or [])
        return
    root = Path(args[0])
    max_tokens = int(args[1]) if len(args) > 1 else 1000
    files = _load_files(args[2]) if len(args) > 2 else None
    try:
        result = repomap.build(root, max_tokens, files=files)
    except Exception as error:  # noqa: BLE001
        result = {
            "map": "（仓库地图生成失败）",
            "files": 0,
            "symbols": 0,
            "shown": 0,
            "error": str(error)[:300],
        }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
