from app.wiki_provenance import wiki_provenance


def test_unknown_remote_cannot_be_inferred_from_wiki_text(services, monkeypatch):
    workspace = services[2]
    monkeypatch.setattr(
        "app.wiki_provenance.local_revision", lambda _w: {"commit": "a" * 40, "dirty": False}
    )
    assert (
        wiki_provenance(workspace, "owner/repo", {"content": [{"text": "commit " + "a" * 40}]})[
            "status"
        ]
        == "unknown"
    )
    assert (
        wiki_provenance(
            workspace, "owner/repo", {"structuredContent": {"indexed_commit": "a" * 40}}
        )["status"]
        == "match"
    )
    assert (
        wiki_provenance(
            workspace, "owner/repo", {"structuredContent": {"indexed_commit": "b" * 40}}
        )["status"]
        == "different"
    )
    monkeypatch.setattr(
        "app.wiki_provenance.local_revision", lambda _w: {"commit": "a" * 40, "dirty": True}
    )
    assert (
        wiki_provenance(workspace, "owner/repo", {"structuredContent": {"commit": "a" * 40}})[
            "status"
        ]
        == "different"
    )
