"""新问题捕获项目默认来源；已有问题的快照不随默认值变化。"""

import json

from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.core.config import dump_json
from app.modules.auth.ownership import current_owner
from app.modules.chat.schemas import SourceOptions
from app.modules.projects.models import SourcePreference


class SourcePreferences:
    def __init__(self, database, scope_id):
        self.database, self.project_scope_id = database, scope_id

    @property
    def scope_id(self):
        # 所有独立对话共用服务对象，但默认来源不能共用另一个账号的选择。
        owner = current_owner()
        return (
            f"independent:{owner}"
            if owner and self.project_scope_id == "independent"
            else self.project_scope_id
        )

    def read(self, session):
        row = session.get(SourcePreference, self.scope_id)
        return {
            "source_options": SourceOptions.model_validate(
                json.loads(row.options_json) if row else {}
            ).model_dump(),
            "version": row.version if row else 0,
        }

    def get(self):
        with self.database.session() as session:
            return self.read(session)

    def save(self, body):
        options = body.source_options.model_dump()
        conflict = "知识来源已在其他窗口修改，请读取最新配置后重试"
        try:
            with self.database.session.begin() as session:
                if body.version == 0:
                    session.add(
                        SourcePreference(scope_id=self.scope_id, options_json=dump_json(options))
                    )
                else:
                    # 条件更新保护并发保存，避免旧窗口覆盖最新选项。
                    result = session.execute(
                        update(SourcePreference)
                        .where(
                            SourcePreference.scope_id == self.scope_id,
                            SourcePreference.version == body.version,
                        )
                        .values(options_json=dump_json(options), version=body.version + 1)
                    )
                    if result.rowcount != 1:
                        raise ValueError(conflict)
        except IntegrityError as error:
            raise ValueError(conflict) from error
        return {"source_options": options, "version": body.version + 1}
