import json

from app.modules.knowledge.source_guides import ProjectKnowledge


def catalogue(workspace, path):
    source = workspace.read("Program.cs")
    document = {
        "id": "startup:main",
        "title": "启动流程 / Main",
        "text": "从 Main 进入程序入口。",
        "references": [
            {
                "path": "Program.cs",
                "sha256": source["version"],
                "start": 1,
                "end": source["line_count"],
                "method": "Main",
                "code": source["content"].rstrip("\r\n"),
            }
        ],
    }
    path.write_text(json.dumps({"schema_version": 1, "documents": [document]}), encoding="utf-8")
    return document


def test_knowledge_requires_matching_file_and_fragment(services, tmp_path):
    _, _, workspace, *_ = services
    path = tmp_path / "catalogue.json"
    catalogue(workspace, path)
    knowledge = ProjectKnowledge(workspace, path)
    result = knowledge.search("Main 启动流程")
    assert len(result["matches"]) == 1 and result["matches"][0]["references"][0]["lines"]
    (workspace.root / "Program.cs").write_text("class Other {}", encoding="utf-8")
    assert knowledge.search("Main")["matches"] == []
    assert knowledge.search("Main")["excluded_stale"] == 1
    document = catalogue(workspace, path)
    document["references"][0]["code"] = "伪造片段"
    path.write_text(json.dumps({"schema_version": 1, "documents": [document]}), encoding="utf-8")
    assert knowledge.search("Main")["matches"] == []


def test_knowledge_honors_budget_and_path_boundary(services, tmp_path):
    _, _, workspace, *_ = services
    path = tmp_path / "catalogue.json"
    document = catalogue(workspace, path)
    knowledge = ProjectKnowledge(workspace, path)
    assert knowledge.search("Main", max_tokens=1)["matches"] == []
    document["references"][0]["path"] = "../outside.cs"
    path.write_text(json.dumps({"schema_version": 1, "documents": [document]}), encoding="utf-8")
    assert knowledge.search("Main")["matches"] == []
