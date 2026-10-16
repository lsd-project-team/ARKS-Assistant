"""有界版本缓存；真实内容哈希为键，避免依赖 mtime 漏掉原位替换。"""

from collections import OrderedDict
from threading import RLock


class VersionCache:
    def __init__(self, max_entries=64, max_bytes=16_000_000):
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self.entries = OrderedDict()
        self.bytes = self.hits = self.misses = 0
        self.lock = RLock()

    def get_or_create(self, key, factory, weight):
        with self.lock:
            if key in self.entries:
                self.hits += 1
                self.entries.move_to_end(key)
                return self.entries[key][0]
            self.misses += 1
            value = factory()
            if weight > self.max_bytes:
                return value
            self.entries[key] = (value, weight)
            self.bytes += weight
            while len(self.entries) > self.max_entries or self.bytes > self.max_bytes:
                _, (_, removed) = self.entries.popitem(last=False)
                self.bytes -= removed
            return value

    def statistics(self):
        with self.lock:
            return {
                "hits": self.hits,
                "misses": self.misses,
                "entries": len(self.entries),
                "bytes": self.bytes,
            }
