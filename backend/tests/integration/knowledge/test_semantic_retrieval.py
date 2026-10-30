"""实际本地多语言模型验证不同措辞及长记忆末尾，不调用供应商。"""

import sqlite3

from app.modules.knowledge.semantic import SemanticRetrieval


def test_real_multilingual_embedding_finds_paraphrase_and_caches_versions(tmp_path):
    engine = SemanticRetrieval(tmp_path / "retrieval.sqlite3")
    documents = {
        "恢复": "机器停止后重新启动生产，需要先恢复运行条件。",
        "外观": "界面颜色设置与字体大小。",
        "尾部": "字体大小与界面颜色。" * 100 + "机器停止后重新启动生产，需要先恢复运行条件。",
    }
    scores = engine.scores("停机以后怎样重新生产", documents)
    assert not engine.error and scores["恢复"] > 0.65
    assert scores["外观"] < 0.3 and scores["尾部"] > 0.65
    with sqlite3.connect(engine.database) as connection:
        before = connection.execute("SELECT count(*) FROM vectors").fetchone()[0]
    assert engine.scores("停机以后怎样重新生产", documents) == scores
    with sqlite3.connect(engine.database) as connection:
        assert connection.execute("SELECT count(*) FROM vectors").fetchone()[0] == before
    documents["恢复"] = "按钮字体采用十六像素，界面背景颜色为白色。"
    changed = engine.scores("停机以后怎样重新生产", documents)
    assert changed["恢复"] < scores["恢复"]
