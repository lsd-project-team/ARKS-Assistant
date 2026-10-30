"""离线 Linux 语义检索验收；只使用本地公开权重和一次性合成问题库。"""

import json
import os
import sqlite3
import subprocess
import sys

from .linux_runtime.safety import (
    PROJECT,
    SmokeFailure,
    environment,
    prepare_root,
    require,
    write_report,
)

DOCUMENTS = {
    "production": "机器停止后重新启动生产，需要先恢复运行条件。",
    "appearance": "调整侧边栏字体大小和颜色，选择不同外观。",
    "network": "服务器网络连接中断，检查网线和交换机。",
}
QUERY = "停机以后怎样重新生产"


def vector_cache(path):
    with sqlite3.connect(path) as connection:
        return dict(connection.execute("SELECT key, value FROM vectors"))


def restart_probe(root):
    # 独立进程重新加载实际模型；不能用同一对象的内存缓存代替重启证据。
    program = """
import json
import sys
from pathlib import Path
from app.modules.knowledge.semantic import SemanticRetrieval, chunks, local_encoder
from scripts.verification.linux_semantic import DOCUMENTS, QUERY

encoder = local_encoder()
original_embed = encoder.embed
observed = []

def traced_embed(values, **kwargs):
    values = list(values)
    observed.extend(values)
    return original_embed(values, **kwargs)

encoder.embed = traced_embed
index = SemanticRetrieval(Path(sys.argv[1]))
scores = index.scores(QUERY, DOCUMENTS)
assert index.error is None
# 追踪真实编码器的输入，不替代推理；重启只编码查询，不能重编码已缓存文档。
assert observed == chunks(QUERY)[:4]
print(json.dumps(scores))
"""
    result = subprocess.run(
        [sys.executable, "-c", program, str(root / "vectors.sqlite3")],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    require(result.returncode == 0, "semantic_restart_failed")
    return json.loads(result.stdout)


def semantic(root, checks, hashes):
    import numpy as np

    from app.modules.knowledge.semantic import SemanticRetrieval, local_encoder, model_version

    encoder = local_encoder()
    vector = next(encoder.embed([QUERY]))
    require(vector.shape == (384,) and np.isfinite(vector).all(), "embedding_vector_invalid")
    hashes["model_onnx"] = model_version(str(encoder.model._model_dir))
    checks["local_cpu_embedding_384_finite"] = True
    index = SemanticRetrieval(root / "vectors.sqlite3")
    scores = index.scores(QUERY, DOCUMENTS)
    require(index.error is None and set(scores) == set(DOCUMENTS), "semantic_degraded")
    require(max(scores, key=scores.get) == "production", "semantic_paraphrase_rank_failed")
    checks["actual_semantic_paraphrase_ranking"] = True
    before = vector_cache(index.database)
    require(bool(before), "document_vectors_not_persisted")
    require(
        all(
            len(parsed := json.loads(value)) == 384
            and np.isfinite(parsed).all()
            and abs(float(np.linalg.norm(parsed)) - 1) < 0.001
            for value in before.values()
        ),
        "persistent_normalized_vector_invalid",
    )
    checks["product_document_vectors_normalized"] = True
    after_scores = restart_probe(root)
    require(vector_cache(index.database) == before, "restart_reencoded_document_cache")
    require(
        all(abs(after_scores[key] - value) < 0.00001 for key, value in scores.items()),
        "restart_semantic_scores_changed",
    )
    checks["separate_process_persistent_vector_reuse"] = True


def debug_library(root, checks):
    from app.infrastructure.database.registry import Base
    from app.infrastructure.database.session import Database
    from app.modules.handover.application.commands import Action, DebugWrite
    from app.modules.handover.application.debug_issues import DebugIssues
    from app.modules.handover.infrastructure.persistence.repository import HandoverStore
    from app.modules.knowledge.corpora.debug_issues import DebugIssueCorpus

    database = Database(root / "library.sqlite3")
    try:
        Base.metadata.create_all(database.engine)
        store = HandoverStore(database=database)
        issues = DebugIssues(store)
        body = DebugWrite(
            title="中转台取片异常",
            payload={
                "problem": "取片不稳定",
                "device": "ZX2200 HS",
                "software_version": "1.20",
                "module": "取片",
                "conditions": "加热生产",
                "cause": "合成夹具：背胶粘连",
                "solution": "合成夹具：增加吹气",
                "resolution_status": "resolved",
            },
        )
        row = issues.save(body, {})
        events = []
        corpus = DebugIssueCorpus(database, lambda *event: events.append(event))
        for query in ("中间平台吸不起来", "中转台芯片黏住怎么办", "IPT 抓取失败"):
            report = corpus.search_report(query)
            require(not report["degraded"], "debug_retrieval_degraded")
            require(report["matches"][0]["id"] == row["id"], "debug_paraphrase_not_recalled")
        require(
            any(kind == "knowledge_reference" for kind, _ in events),
            "debug_reference_event_missing",
        )
        checks["real_debug_library_paraphrase_recall"] = True
        for query in (
            "ZX2300 中转台取片异常",
            "V1.2 中转台取片异常",
            "常温中转台取片异常",
            "中转台取片异常 E902",
        ):
            report = corpus.search_report(query)
            require(not report["degraded"], "debug_filter_semantic_degraded")
            require(not report["matches"], "incompatible_debug_record_reused")
        checks["device_version_temperature_alarm_exclusion"] = True
        bound = DebugIssueCorpus(database, context_query="ZX2300 V3.0.0 常温取片异常")
        require(
            not bound.search("取片异常", device="ZX2200 HS", software_version="1.20"),
            "user_conditions_overridden",
        )
        require(
            bound.read(row["id"])["compatibility"]["status"] == "mismatch", "read_mismatch_lost"
        )
        checks["original_user_conditions_preserved"] = True
        pending = issues.save(
            DebugWrite(title="真空报警 E901", payload={"problem": "合成夹具：E901 负压不足"}), {}
        )
        fresh = DebugIssueCorpus(database)
        match = fresh.search_report("E901 怎么办")
        require(not match["degraded"], "open_issue_semantic_degraded")
        require(
            match["matches"][0]["id"] == pending["id"]
            and match["matches"][0]["payload"]["resolution_status"] == "open",
            "open_issue_promoted_to_resolved",
        )
        checks["unresolved_record_keeps_open_status"] = True
        issues.save(
            DebugWrite(
                title=row["title"],
                version=row["version"],
                payload={**body.payload.model_dump(), "solution": "合成夹具：更新处理记录"},
            ),
            {},
            identifier=row["id"],
        )
        latest = DebugIssueCorpus(database)
        old, current = corpus.read(row["id"]), latest.read(row["id"])
        require(
            old["citation"] == f"debug-issue:{row['id']}/1"
            and current["citation"] == f"debug-issue:{row['id']}/2"
            and "增加吹气" in old["content"]
            and "更新处理记录" in current["content"],
            "fixed_revision_snapshot_changed",
        )
        checks["fixed_revision_citation_and_snapshot"] = True
        store.action(row["id"], "archive", Action(version=2, actor="合成夹具", opinion="归档验收"))
        archived = DebugIssueCorpus(database)
        require(row["id"] not in archived.items, "archived_issue_in_new_snapshot")
        require(corpus.read(row["id"])["version"] == 1, "archive_mutated_existing_snapshot")
        checks["archive_excluded_without_mutating_old_snapshot"] = True
    finally:
        database.close()


def main():
    require(sys.platform == "linux", "linux_required")
    require(os.geteuid() != 0, "nonroot_required")
    root, token = prepare_root(os.environ.get("ARKS_LINUX_SEMANTIC_ROOT"))
    checks, hashes, error = {}, {}, ""
    original = dict(os.environ)
    try:
        # 依赖只看到临时HOME和目录；不继承供应商、代理、MCP及正式配置。
        os.environ.clear()
        os.environ.update(environment(root, root / "data", root / "source", "", "localhost"))
        sys.path.insert(0, str(PROJECT / "backend"))
        semantic(root, checks, hashes)
        debug_library(root, checks)
    except SmokeFailure as failure:
        error = str(failure)
    except Exception:
        error = "unexpected_semantic_failure"
    finally:
        os.environ.clear()
        os.environ.update(original)
    report = write_report(root, token, checks, hashes, error)
    print(json.dumps(report), flush=True)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
