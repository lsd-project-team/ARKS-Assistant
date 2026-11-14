import json

import pytest

from todo import Store, TodoService


def service(tmp_path):
    return TodoService(Store(tmp_path / "tasks.json"))


def test_add_returns_task(tmp_path):
    task = service(tmp_path).add("写周报")
    assert task.id == 1 and task.title == "写周报" and task.done is False


def test_add_empty_title_raises(tmp_path):
    with pytest.raises(ValueError):
        service(tmp_path).add("   ")


def test_complete(tmp_path):
    todo = service(tmp_path)
    task = todo.add("a")
    assert todo.complete(task.id).done is True


def test_complete_missing_raises(tmp_path):
    with pytest.raises(KeyError):
        service(tmp_path).complete(99)


def test_list_filters(tmp_path):
    todo = service(tmp_path)
    first = todo.add("a")
    second = todo.add("b")
    todo.complete(first.id)
    assert [task.id for task in todo.list("active")] == [second.id]
    assert [task.id for task in todo.list("done")] == [first.id]
    assert len(todo.list("all")) == 2


def test_list_invalid_kind_raises(tmp_path):
    with pytest.raises(ValueError):
        service(tmp_path).list("bogus")


def test_persistence_reload(tmp_path):
    path = tmp_path / "tasks.json"
    todo = TodoService(Store(path))
    task = todo.add("a")
    todo.complete(task.id)
    reloaded = TodoService(Store(path))
    assert len(reloaded.list("all")) == 1
    assert reloaded.list("all")[0].done is True


def test_old_data_without_due_loads(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps([{"id": 1, "title": "old", "done": False}]), encoding="utf-8")
    todo = TodoService(Store(path))
    assert todo.list("all")[0].title == "old"


def test_ids_increase(tmp_path):
    todo = service(tmp_path)
    assert todo.add("a").id == 1
    assert todo.add("b").id == 2


def test_complete_is_idempotent(tmp_path):
    todo = service(tmp_path)
    task = todo.add("a")
    todo.complete(task.id)
    assert todo.complete(task.id).done is True
