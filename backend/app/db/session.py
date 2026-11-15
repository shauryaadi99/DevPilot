"""Database engine and session management for PostgreSQL."""

from typing import Any, Dict, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import logger
from app.db.base import Base

settings = get_settings()

# Engine configuration for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for providing a database session to API endpoints."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> Dict[str, Any]:
    """Test the database connection and return status information."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "status": "connected",
            "engine": "postgresql" if "postgres" in settings.DATABASE_URL else "sqlite",
            "error": None,
        }
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return {
            "status": "disconnected",
            "engine": "unknown",
            "error": str(e),
        }


def init_db() -> None:
    """Ensure all application tables exist in PostgreSQL."""
    Base.metadata.create_all(bind=engine)
