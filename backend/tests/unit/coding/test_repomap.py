from app.modules.coding import repomap


def test_repo_map_lists_classes_and_methods(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Orders.cs").write_text(
        "namespace Demo;\n"
        "public class OrderService\n"
        "{\n"
        "    public int Total() { return 0; }\n"
        "}\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "Api.cs").write_text(
        "namespace Demo;\n"
        "public class Api\n"
        "{\n"
        "    private readonly OrderService _service = new();\n"
        "    public int Get() => _service.Total();\n"
        "}\n",
        encoding="utf-8",
    )
    result = repomap.build(tmp_path, max_tokens=400)
    assert result["files"] == 2
    assert "OrderService" in result["map"]
    assert "Total" in result["map"]
    assert result["symbols"] >= 3


def test_repo_map_respects_budget(tmp_path):
    for index in range(30):
        (tmp_path / f"File{index}.cs").write_text(
            f"namespace Demo;\npublic class Service{index}\n{{\n"
            f"    public void Method{index}() {{ }}\n}}\n",
            encoding="utf-8",
        )
    result = repomap.build(tmp_path, max_tokens=80)
    assert result["shown"] < result["symbols"]
    assert len(result["map"]) < 2000


def test_repo_map_handles_empty_repo(tmp_path):
    result = repomap.build(tmp_path)
    assert result["files"] == 0
    assert "C# 文件" in result["map"]
