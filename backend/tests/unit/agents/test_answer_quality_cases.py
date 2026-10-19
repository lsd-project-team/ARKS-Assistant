import importlib
from pathlib import Path


def test_evaluation_manifest_has_reproducible_twenty_questions_and_five_real_flows(monkeypatch):
    root = Path(__file__).resolve().parents[4]
    monkeypatch.syspath_prepend(str(root))
    data = importlib.import_module("scripts.verification.answer_quality.cases")
    first, repeated, different = data.cases(20261019), data.cases(20261019), data.cases(20261020)
    assert first == repeated and [row["id"] for row in first] != [row["id"] for row in different]
    assert len({row["id"] for row in first}) == 20
    assert sum(row["category"] == "experience" for row in first) == 15
    flows = [row for row in first if row["category"] == "flow"]
    assert len(flows) == 5
    for row in flows:
        assert row["source"]["path"].startswith("AKRS.ZX2200/")
        assert not Path(row["source"]["path"]).is_absolute()
        assert ".." not in Path(row["source"]["path"]).parts
        assert row["source"]["start"] < row["source"]["end"]
        assert row["oracle"]
    assert {row["id"] for row in first} == {row["id"] for row in different}
