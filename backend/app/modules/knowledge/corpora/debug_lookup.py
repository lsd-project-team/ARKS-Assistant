"""每轮延迟建立问题库快照，普通问题仅装配工具定义，不加载或搜索记录。"""

from threading import RLock

from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus, debug_issue_tools


class DebugIssueLookup:
    def __init__(self, database, emit, context_query):
        self.database, self.emit, self.context_query = database, emit, context_query
        self._corpus = None
        self._lock = RLock()

    def _load(self):
        # 模型可能并行调用多个工具；同轮共用第一次查询时固定的记录版本。
        with self._lock:
            if self._corpus is None:
                self._corpus = DebugIssueCorpus(self.database, self.emit, self.context_query)
            return self._corpus

    def search_report(self, *args, **kwargs):
        return self._load().search_report(*args, **kwargs)

    def read(self, *args, **kwargs):
        return self._load().read(*args, **kwargs)

    def review_records(self, references):
        if self._corpus is None:
            return []
        return self._corpus.review_records(references)

    def resolve_references(self, references):
        # 追问可能复用前文引用；仅实际引用记录时按编号核对，不进行全库相似度搜索。
        requested = {}
        for reference in references:
            identifier, version = reference.removeprefix("debug-issue:").rsplit("/", 1)
            requested[identifier] = int(version)
        corpus = self._load()
        records = corpus.review_records(requested)
        for identifier, version in requested.items():
            if corpus.items.get(identifier, {}).get("version") == version:
                corpus.read(identifier)
        return records

    def tools(self):
        return debug_issue_tools(self)
