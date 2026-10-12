"""Tree-sitter 离线后备解析器，隔离原生库故障，不能带崩主服务。"""

import json
import sys

from app.workspace import Workspace

if __name__ == "__main__":
    print(json.dumps(Workspace._native_symbols(json.loads(sys.stdin.read())), ensure_ascii=False))
