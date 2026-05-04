from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Корневой declarative base для всех ORM-моделей ядра. Импортируется
    модулями, миграции Alembic используют его metadata."""
