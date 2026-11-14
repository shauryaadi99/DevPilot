"""Tests for database connectivity and session lifecycle."""

from app.db.session import check_database_connection, SessionLocal
from sqlalchemy import text


def test_database_connection():
    """Verify that the database connection test returns connected."""
    result = check_database_connection()
    assert result["status"] == "connected"
    assert result["error"] is None
    assert result["engine"] in ("sqlite", "postgresql")


def test_database_session_execution():
    """Verify that a session can be opened and execute a basic query."""
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        assert result == 1
    finally:
        db.close()
