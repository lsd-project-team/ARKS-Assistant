"""ASGI 入口；应用装配与生命周期集中在 bootstrap。"""

from app.bootstrap import create_app
from app.core.logging import configure_logging

configure_logging()
app = create_app()
