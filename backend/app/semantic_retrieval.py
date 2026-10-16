"""本机多语言向量检索；向量按模型与原文版本缓存，不上传资料。"""

import hashlib
import importlib.metadata
import json
import re
import sqlite3
from functools import lru_cache
from pathlib import Path
from threading import RLock

import numpy as np

from app.config import PROJECT_ROOT
from app.version_cache import VersionCache

MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_CACHE = PROJECT_ROOT / ".tools/embedding-models"
_model_lock = RLock()


@lru_cache(maxsize=1)
def local_encoder():
    from fastembed import TextEmbedding

    # 正常问答禁止触发模型下载；Setup / warmup 明确准备模型后再使用。
    return TextEmbedding(
        model_name=MODEL,
        cache_dir=str(MODEL_CACHE),
        threads=2,
        providers=["CPUExecutionProvider"],
        local_files_only=True,
    )


def chunks(text):
    """模型上限 128 token；短片段重叠，避免长记忆末尾被整体截断。"""
    result = []
    for sentence in re.split(r"(?<=[。！？!?;；\n])|(?<=\.)(?=\s)", text):
        sentence = re.sub(r"\s+", " ", sentence).strip()
        if not sentence:
            continue
        if len(sentence) <= 100:
            result.append(sentence)
        else:
            result.extend(sentence[start : start + 100] for start in range(0, len(sentence), 50))
    return result or [""]


class SemanticRetrieval:
    def __init__(self, database: Path):
        self.database = database
        self.lock = RLock()
        self.cache = VersionCache(max_entries=256, max_bytes=2_000_000)
        self.matrices = VersionCache(max_entries=16, max_bytes=64_000_000)
        self.error = None

    def _vectors(self, texts, *, persist=False):
        with _model_lock:
            encoder = local_encoder()
            revision = MODEL + ":" + importlib.metadata.version("fastembed")
            # 同名模型升级后，旧的文本向量不能作为新模型的结果复用。
            directory = getattr(getattr(encoder, "model", None), "_model_dir", None)
            if directory:
                revision += ":" + model_version(str(directory))
            if not persist:
                return {
                    text: self.cache.get_or_create(
                        (revision, text),
                        lambda value=text: normalized(next(encoder.embed([value]))),
                        1536,
                    )
                    for text in dict.fromkeys(texts)
                }
            return self._cached_documents(encoder, revision, texts)

    def _cached_documents(self, encoder, revision, texts):
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database, timeout=15) as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS vectors (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            result, missing = {}, []
            for text in dict.fromkeys(texts):
                key = hashlib.sha256((revision + "\n" + text).encode()).hexdigest()
                row = connection.execute("SELECT value FROM vectors WHERE key=?", (key,)).fetchone()
                if row:
                    result[text] = np.asarray(json.loads(row[0]), dtype=np.float32)
                else:
                    missing.append((text, key))
            vectors = encoder.embed([item[0] for item in missing], batch_size=32) if missing else []
            for (text, key), vector in zip(missing, vectors, strict=True):
                value = normalized(vector)
                result[text] = value
                connection.execute(
                    "INSERT OR REPLACE INTO vectors VALUES (?, ?)",
                    (key, json.dumps(value.tolist())),
                )
            # 缓存可重建，旧版本数量有上限；原记忆文件和历史不受清理影响。
            connection.execute(
                "DELETE FROM vectors WHERE rowid NOT IN "
                "(SELECT rowid FROM vectors ORDER BY rowid DESC LIMIT 20000)"
            )
            return result

    def scores(self, query, documents):
        if not query or not documents:
            return {}
        try:
            with self.lock:
                query_chunks = chunks(query)[:4]
                vectors = self._vectors(query_chunks)

                # 内容指纹也支持原位修改映射，不依赖对象身份或文件时间。
                def prepare():
                    sections = {key: chunks(text) for key, text in documents.items()}
                    values = self._vectors(
                        [text for rows in sections.values() for text in rows], persist=True
                    )
                    keys = [key for key, rows in sections.items() for _ in rows]
                    matrix = np.stack([values[text] for rows in sections.values() for text in rows])
                    return documents, keys, matrix

                weight = sum(len(chunks(text)) for text in documents.values()) * 1536
                signature = tuple(
                    (key, hashlib.sha256(text.encode()).digest()) for key, text in documents.items()
                )
                _, keys, matrix = self.matrices.get_or_create(signature, prepare, weight)
                similarities = np.max(
                    matrix @ np.stack([vectors[q] for q in query_chunks]).T, axis=1
                )
                scores = {}
                for key, similarity in zip(keys, similarities, strict=True):
                    scores[key] = max(scores.get(key, -1), float(similarity))
                self.error = None
                return scores
        except (OSError, ValueError, RuntimeError, sqlite3.Error) as error:
            self.error = f"本地语义检索暂不可用：{type(error).__name__}"
            return {}


def normalized(vector):
    return vector / max(float(np.linalg.norm(vector)), 1e-12)


@lru_cache(maxsize=2)
def model_version(directory):
    path = next(Path(directory).glob("*.onnx"), None)
    if path is None:
        return directory
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
