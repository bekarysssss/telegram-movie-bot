"""initial schema

Первая миграция создаёт схему по текущим моделям (+ расширение pg_trgm для поиска).
Все следующие изменения схемы — через `alembic revision --autogenerate -m "..."`.
"""
import sqlalchemy as sa  # noqa: F401
from alembic import op

from app.db import models  # noqa: F401
from app.db.base import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
