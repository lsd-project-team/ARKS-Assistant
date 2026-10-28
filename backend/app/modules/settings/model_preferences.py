"""个人模型选择与全局配置分开，执行时按发起账号解析并冻结配置。"""

from sqlalchemy.dialects.sqlite import insert

from app.modules.settings.models import ModelPreference


class ModelPreferences:
    def __init__(self, database, settings):
        self.database, self.settings = database, settings

    def configuration(self, account_id=None):
        config = self.settings.load()
        if not account_id:
            return config
        with self.database.session() as session:
            preference = session.get(ModelPreference, account_id)
            profile = next(
                (
                    item
                    for item in config.model_profiles
                    if preference and item.id == preference.profile_id
                ),
                None,
            )
        # 管理员删除配置后，旧选择自然回退到当前系统默认模型。
        return (
            config.model_copy(update={"active_profile_id": profile.id, "model": profile.config})
            if profile
            else config
        )

    def public(self, account_id):
        config = self.configuration(account_id)
        return {
            "active_profile_id": config.active_profile_id,
            "model_profiles": [
                {"id": item.id, "name": item.name, "model": item.config.model}
                for item in config.model_profiles
            ],
        }

    def save(self, account_id, profile_id):
        if profile_id not in {item.id for item in self.settings.load().model_profiles}:
            raise ValueError("模型配置不存在，请刷新后重新选择")
        # 同一账号多个窗口首次选择也只生成一条偏好，不写全局配置文件。
        with self.database.session.begin() as session:
            session.execute(
                insert(ModelPreference)
                .values(account_id=account_id, profile_id=profile_id)
                .on_conflict_do_update(
                    index_elements=[ModelPreference.account_id], set_={"profile_id": profile_id}
                )
            )
        return self.public(account_id)
