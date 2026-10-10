from alembic import context

from app.config import Paths
from app.database import Database
from app.models import Base

database = None
engine = context.config.attributes.get("connection")
if engine is None:
    database = Database(Paths().data / "app.sqlite3")
    engine = database.engine
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()
if database:
    database.close()
