"""待办业务逻辑。"""

from .models import Task


class TodoService:
    def __init__(self, store):
        self.store = store

    def add(self, title):
        title = title.strip()
        if not title:
            raise ValueError("标题不能为空")
        task = Task(id=self.store.next_id(), title=title)
        self.store.add(task)
        return task

    def complete(self, task_id):
        for task in self.store.all():
            if task.id == task_id:
                task.done = True
                self.store.update(task)
                return task
        raise KeyError(task_id)

    def list(self, kind="all"):
        tasks = self.store.all()
        if kind == "all":
            return tasks
        if kind == "active":
            return [task for task in tasks if not task.done]
        if kind == "done":
            return [task for task in tasks if task.done]
        raise ValueError(kind)
