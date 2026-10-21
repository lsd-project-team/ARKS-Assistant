"""有界读取JSON/ZIP；不解压到磁盘，不接收包内归属或路径指令。"""

import io
import json
import zipfile

from app.modules.action_timing.schemas import TimingPackage

MAX_BYTES = 16 * 1024 * 1024


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"JSON字段重复：{key[:80]}")
        result[key] = value
    return result


def decode_json(raw):
    try:
        return json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_keys)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("数据包必须为有效UTF-8 JSON") from error


def read_package(raw: bytes):
    if len(raw) > MAX_BYTES:
        raise ValueError("数据包超过16MiB，请缩小采集批次")
    if not raw.startswith(b"PK"):
        return TimingPackage.model_validate(decode_json(raw))
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if (
                len(members) != 2
                or {item.filename for item in members} != {"manifest.json", "events.jsonl"}
                or sum(item.file_size for item in members) > MAX_BYTES
                or any(item.flag_bits & 1 for item in members)
            ):
                raise ValueError("ZIP只允许manifest.json和events.jsonl，展开总量不超过16MiB")
            manifest = decode_json(archive.read("manifest.json"))
            events = [
                decode_json(line)
                for line in archive.read("events.jsonl").splitlines()
                if line.strip()
            ]
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError) as error:
        raise ValueError("采集ZIP损坏或格式不受支持") from error
    return TimingPackage.model_validate({"manifest": manifest, "events": events})
