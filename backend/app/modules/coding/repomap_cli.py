"""repo_map 子进程入口：tree-sitter 解析异常时隔离崩溃，不影响主服务。"""

import json
import sys
from pathlib import Path

from app.modules.coding import repomap


def main():
    root = Path(sys.argv[1])
    max_tokens = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    try:
        result = repomap.build(root, max_tokens)
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
