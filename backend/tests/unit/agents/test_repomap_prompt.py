from app.agents.runtime.graph_builder import csharp_repo_map_prompt


class Coding:
    def __init__(self, repo):
        self.repo = repo

    def repo_map(self, max_tokens):
        return self.repo


async def test_repo_map_injected_for_large_csharp_project():
    coding = Coding(
        {
            "files": 12,
            "shown": 30,
            "symbols": 60,
            "map": "# C# 仓库地图\nsrc/Foo.cs:\n  public class Foo",
        }
    )
    prompt = await csharp_repo_map_prompt(coding)
    assert "C# 仓库地图" in prompt
    assert "public class Foo" in prompt


async def test_repo_map_skipped_for_small_or_empty_project():
    assert await csharp_repo_map_prompt(Coding({"files": 2, "shown": 3, "map": "x"})) == ""
    assert await csharp_repo_map_prompt(Coding({"files": 20, "shown": 0, "map": ""})) == ""


async def test_repo_map_failure_is_ignored():
    class Broken:
        def repo_map(self, max_tokens):
            raise OSError("boom")

    assert await csharp_repo_map_prompt(Broken()) == ""
