"""管理员显式准备本仓库的可信隔离执行镜像，不拉取浮动基础镜像。"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.infrastructure.execution import ExecutionError, prepare_executor  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-image", required=True, help="已存在的基础镜像 sha256 ID 或 digest")
    parser.add_argument("--context", default="default")
    arguments = parser.parse_args()
    try:
        result = prepare_executor(arguments.base_image, context=arguments.context)
    except ExecutionError as exc:
        print(json.dumps({"available": False, "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
