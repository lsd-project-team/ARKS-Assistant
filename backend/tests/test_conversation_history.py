import pytest

from app.models import Message


def populate(repository, count=205):
    thread = repository.create_thread("长对话")
    with repository.database.session.begin() as session:
        rows = [
            Message(
                id=f"message-{index:04d}",
                thread_id=thread["id"],
                role="user" if index % 2 == 0 else "assistant",
                content=f"历史正文 {index}",
                created_at=f"2026-10-10T00:{index // 60:02d}:{index % 60:02d}+00:00",
            )
            for index in range(count)
        ]
        session.add_all(rows)
    return thread["id"]


def test_message_pages_and_cross_thread_cursors(services):
    repository = services[3]
    thread_id = populate(repository)
    latest = repository.thread(thread_id, 80)
    assert len(latest["messages"]) == 80
    assert latest["messages"][0]["id"] == "message-0125"
    assert latest["has_older"] and not latest["has_newer"]
    older = repository.thread(thread_id, 80, before=latest["before_cursor"])
    assert older["messages"][-1]["id"] == "message-0124"
    assert older["has_older"] and older["has_newer"]
    first = repository.thread(thread_id, 80, before=older["before_cursor"])
    assert len(first["messages"]) == 45 and not first["has_older"]
    around = repository.thread(thread_id, 20, around="message-0050")
    assert [row["id"] for row in around["messages"]] == [
        f"message-{index:04d}" for index in range(40, 60)
    ]
    other = repository.create_thread("其他会话")
    with pytest.raises(FileNotFoundError):
        repository.thread(other["id"], 20, around="message-0050")


def test_selection_history_pages_and_full_content_read(services):
    repository = services[3]
    thread = repository.create_thread("选区检索")
    content = "a" * 13000 + "SelectionOnly" + "b" * 15000
    for index in range(23):
        run = repository.create_run(
            thread["id"], str(index), [{"path": "Code/SelectionOnly.cs", "content": content}]
        )
        repository.finish(run["id"], "答案")
    page = repository.history.search(thread["id"], "SelectionOnly", limit=10)
    assert page["total"] == 23 and page["next_offset"] == 10
    assert page["matches"][0]["selections"][0]["partial"]
    second = repository.history.search(thread["id"], "SelectionOnly", offset=10, limit=10)
    assert not {row["id"] for row in page["matches"]} & {row["id"] for row in second["matches"]}
    identifier = page["matches"][0]["id"]
    offset, parts = 0, []
    while offset is not None:
        portion = repository.history.read(thread["id"], identifier, offset)
        parts.append(portion["selections"][0]["content"])
        offset = portion["next_offset"]
    assert "".join(parts) == content
    assert '\\"' not in repository.threads(query="SelectionOnly")[0]["snippet"]


def test_first_send_creates_title_atomically(services):
    repository = services[3]
    run = repository.create_run(None, "解释这一段", [{"path": "Module/Main.cs"}])
    thread = repository.thread(run["thread_id"])
    assert thread["title"] == "Main.cs · 解释这一段"
    assert len(thread["messages"]) == 1
    with pytest.raises(ValueError):
        repository.create_run(run["thread_id"], "重复提交", [])
    assert len(repository.threads()) == 1
