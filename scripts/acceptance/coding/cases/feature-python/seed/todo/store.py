"""JSON 文件存储。"""

import json
from pathlib import Path

from .models import Task


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self._tasks = []
        self._load()

    def _load(self):
        if self.path.is_file():
            raw = self.path.read_text(encoding="utf-8") or "[]"
            self._tasks = [Task.from_dict(row) for row in json.loads(raw)]

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps([task.to_dict() for task in self._tasks], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def all(self):
        return list(self._tasks)

    def add(self, task):
        self._tasks.append(task)
        self._save()

    def update(self, task):
        for index, existing in enumerate(self._tasks):
            if existing.id == task.id:
                self._tasks[index] = task
                self._save()
                return
        raise KeyError(task.id)

    def next_id(self):
        return max((task.id for task in self._tasks), default=0) + 1
