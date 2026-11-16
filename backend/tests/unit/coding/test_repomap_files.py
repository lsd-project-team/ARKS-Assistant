from app.modules.coding import repomap


def test_build_can_limit_to_selected_files(tmp_path):
    (tmp_path / "A.cs").write_text("public class A { }\n", encoding="utf-8")
    (tmp_path / "B.cs").write_text("public class B { }\n", encoding="utf-8")
    result = repomap.build(tmp_path, 800, files=["A.cs"])
    assert result["files"] == 1
    assert "A" in result["map"]
    assert "B" not in result["map"]


def test_build_accepts_nested_relative_paths(tmp_path):
    nested = tmp_path / "src" / "App"
    nested.mkdir(parents=True)
    (nested / "Thing.cs").write_text("public class Thing { }\n", encoding="utf-8")
    result = repomap.build(tmp_path, 800, files=["src/App/Thing.cs"])
    assert result["files"] == 1
    assert "src/App/Thing.cs" in result["map"]
