"""把已结束采集目录打包为ARKS可导入ZIP；不修改原始记录。"""

import argparse
import json
import zipfile
from pathlib import Path


def pack(source, target):
    manifest = json.loads((source / "manifest.json").read_text(encoding="utf-8-sig"))
    if manifest.get("state") not in {"completed", "stopped", "incomplete"} or not manifest.get(
        "finished_at"
    ):
        raise ValueError("采集尚未结束，请先停止采集并等待导出完成")
    if target.exists():
        raise ValueError("目标文件已存在，不覆盖原导出")
    if not (source / "events.jsonl").is_file():
        raise ValueError("采集事件文件不存在")
    with zipfile.ZipFile(target, "x", zipfile.ZIP_DEFLATED) as archive:
        for name in ("manifest.json", "events.jsonl"):
            archive.write(source / name, name)
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    args = parser.parse_args()
    print(pack(args.source, args.target))


if __name__ == "__main__":
    main()
