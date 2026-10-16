"""有界正文缓存和混合检索；每轮固定快照，后续只读取改变版本的正文。"""

import json
import re
from collections import OrderedDict, defaultdict
from pathlib import Path
from threading import RLock

from sqlalchemy import select

from app.memory_matching import terms
from app.semantic_retrieval import SemanticRetrieval

ALIASES = (
    ("取片", "拾取", "抓取", "取不下来", "吸不起来", "pick"),
    ("粘片", "粘住", "粘连", "黏住", "背胶", "脱模"),
    ("中转台", "中间平台", "转接台", "ipt"),
    ("真空", "负压", "vacuum"),
    ("回零", "归零", "原点", "homing"),
    ("载具", "料盘", "托盘", "tray"),
    ("报警", "报错", "故障", "异常", "error", "alarm"),
    ("断连", "掉线", "连接中断", "通信中断", "通讯中断"),
)


def alarm_codes(query):
    return set(re.findall(r"(?<![a-z0-9])(?!zx)[a-z]{1,3}\d{3,}(?![a-z0-9])", query.casefold()))


def expanded_terms(text):
    normalized = text.casefold()
    extra = " ".join(" ".join(group) for group in ALIASES if any(x in normalized for x in group))
    return terms(text + " " + extra)


def searchable_text(row):
    payload = row.get("payload", {})
    content = row.get("content") or "\n".join(
        str(value) if not isinstance(value, list) else " ".join(map(str, value))
        for key, value in payload.items()
        if key not in {"evidence", "reported_by", "source_message_id", "source_thread_id"}
    )
    return row["title"], content


class HybridIndex:
    def __init__(self, records, retrieval):
        self.records, self.retrieval = records, retrieval
        self.documents, self.titles, self.postings = {}, {}, defaultdict(set)
        for key, row in records.items():
            title, text = searchable_text(row)
            self.documents[key] = title + "\n" + text
            self.titles[key] = terms(title)
            for term in expanded_terms(title + "\n" + text):
                self.postings[term].add(key)

    def search(self, query, limit=10, predicate=None):
        query = query[:6000]
        original, expanded = terms(query), expanded_terms(query)
        lexical = defaultdict(float)
        for term in expanded:
            for key in self.postings.get(term, ()):
                lexical[key] += 1 if term in original else 0.25
        semantic = self.retrieval.scores(query, self.documents)
        # 明确报警码时不让仅有“报警”等泛词的其他故障占据结果。
        codes = alarm_codes(query)
        ranked = []
        for key in set(lexical) | set(semantic):
            if codes and not any(code in self.documents[key].casefold() for code in codes):
                continue
            meaning = semantic.get(key, 0)
            if not lexical[key] and meaning < 0.6:
                continue
            title = len(original & self.titles[key])
            score = lexical[key] + 3 * title + max(0, meaning) * 3
            ranked.append((score, key, meaning))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        accepted = [item for item in ranked if not predicate or predicate(self.records[item[1]])]
        return accepted[: max(1, min(limit, 50))]


class Catalog:
    def __init__(self, database):
        self.database, self.lock = database, RLock()
        self.snapshots = OrderedDict()
        path = Path(database.engine.url.database).parent / "retrieval.sqlite3"
        self.retrieval = SemanticRetrieval(path)
        self.loaded_documents = 0

    def snapshot(self, namespace, model, conditions):
        with self.lock:
            previous = self.snapshots.get(namespace)
            for _ in range(3):
                with self.database.session() as session:
                    versions = dict(
                        session.execute(select(model.id, model.version).where(*conditions)).all()
                    )
                    if previous and previous[0] == versions:
                        self.snapshots.move_to_end(namespace)
                        return previous[1]
                    old = previous[1].records if previous else {}
                    changed = [
                        key
                        for key, version in versions.items()
                        if old.get(key, {}).get("version") != version
                    ]
                    records = {key: row for key, row in old.items() if key in versions}
                    rows = (
                        session.scalars(select(model).where(model.id.in_(changed))).all()
                        if changed
                        else []
                    )
                    if len(rows) != len(changed) or any(
                        row.version != versions[row.id] for row in rows
                    ):
                        continue
                    for row in rows:
                        document = {
                            column.name: getattr(row, column.name)
                            for column in model.__table__.columns
                        }
                        if "payload_json" in document:
                            document["payload"] = json.loads(document.pop("payload_json"))
                        records[row.id] = document
                    self.loaded_documents += len(rows)
                index = HybridIndex(records, self.retrieval)
                self.snapshots[namespace] = (versions, index)
                self.snapshots.move_to_end(namespace)
                # 正文缓存有界；被清理的索引可从业务记录及版本重新建立。
                while len(self.snapshots) > 16 or (
                    len(self.snapshots) > 1
                    and sum(
                        len(text)
                        for _, item in self.snapshots.values()
                        for text in item.documents.values()
                    )
                    > 16_000_000
                ):
                    self.snapshots.popitem(last=False)
                return index
            raise ValueError("资料正在更新，请稍后重试检索")


_catalog_lock = RLock()


def catalog(database):
    with _catalog_lock:
        if not hasattr(database, "knowledge_catalog"):
            database.knowledge_catalog = Catalog(database)
        return database.knowledge_catalog
