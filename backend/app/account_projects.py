"""公司源码共用，账号的项目身份、对话和知识仍各自保存。"""

import uuid

from sqlalchemy import select

from app.models import Project


class AccountProjects:
    def __init__(self, projects):
        self.projects = projects

    def source(self):
        root = str(self.projects.base.workspace.root)
        repo = self.projects.base.settings.load().deepwiki_repo
        with self.projects.database.session() as session:
            original = session.get(Project, self.projects.default_id)
            if original and original.source_root == root and original.deepwiki_repo:
                repo = original.deepwiki_repo
        # 只使用管理员已配置的公司源码关联，不复制任何人的说明、指令、资料或记忆。
        return {"source_root": root, "source_folders": [], "deepwiki_repo": repo}

    def ensure(self, user):
        if user["role"] != "user":
            return
        binding = self.source()
        with self.projects.lock, self.projects.database.session.begin() as session:
            existing = session.scalar(
                select(Project.id).where(
                    Project.owner_id == user["id"],
                    Project.source_root == binding["source_root"],
                    Project.state == "active",
                )
            )
            if existing:
                return
            identifier = uuid.uuid5(uuid.NAMESPACE_URL, f"arks:account-project:{user['id']}").hex
            # 用户主动归档或移除后不在每次登录时重建；独立对话仍能读取公司源码。
            if session.get(Project, identifier):
                return
            session.add(
                Project(
                    id=identifier,
                    owner_id=user["id"],
                    name="ZX2200 软件分析",
                    source_root=binding["source_root"],
                    deepwiki_repo=binding["deepwiki_repo"],
                )
            )

    def preferred(self, rows):
        root = str(self.projects.base.workspace.root)
        shared = [row for row in rows if row["source_root"] == root]
        return min(shared, key=lambda row: (row["created_at"], row["id"]))["id"] if shared else None

    def permits(self, root, folders):
        binding = self.source()
        return root == binding["source_root"] and not folders
