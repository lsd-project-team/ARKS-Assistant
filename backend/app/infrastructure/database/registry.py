"""统一注册业务表；保持一个元数据集合和既有迁移历史。"""

from app.infrastructure.database import legacy_code_work
from app.infrastructure.database.base import Base
from app.modules.action_timing import models as action_timing
from app.modules.admin import models as admin
from app.modules.auth import models as auth
from app.modules.chat import models as chat
from app.modules.handover.infrastructure.persistence import models as handover
from app.modules.memory import models as memory
from app.modules.projects import models as projects
from app.modules.settings import models as settings
from app.modules.source_analysis import models as source_analysis
from app.modules.source_analysis.reading import models as project_reading

REGISTERED_MODELS = (
    action_timing,
    projects,
    chat,
    source_analysis,
    memory,
    auth,
    admin,
    handover,
    project_reading,
    legacy_code_work,
    settings,
)
__all__ = ["Base"]
