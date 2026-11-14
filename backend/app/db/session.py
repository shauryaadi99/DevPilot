"""Database engine and session management."""

from typing import Any, Dict, Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.logging import logger

settings = get_settings()

connect_args: Dict[str, Any] = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
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
        db_type = "sqlite" if settings.DATABASE_URL.startswith("sqlite") else "postgresql"
        return {
            "status": "connected",
            "engine": db_type,
            "error": None,
        }
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return {
            "status": "disconnected",
            "engine": "unknown",
            "error": str(e),
        }

