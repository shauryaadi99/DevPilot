"""Declarative base for SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Import all models here so Alembic detects them on Base.metadata
from app.db import models  # noqa: F401, E402
