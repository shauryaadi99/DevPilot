"""Health check endpoint providing system status and component diagnostics."""

from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import get_settings
from app.db.session import check_database_connection
from app.integrations.groq_client import get_groq_provider

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Basic Liveness Probe")
@router.get("/api/v1/health", summary="Comprehensive System Health Check")
async def get_health():
    """Return health status of the application and its critical subsystems."""
    settings = get_settings()
    db_status = check_database_connection()
    groq_provider = get_groq_provider()

    is_overall_healthy = db_status["status"] == "connected"

    return {
        "status": "healthy" if is_overall_healthy else "degraded",
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "components": {
            "database": db_status,
            "llm": {
                "provider": "groq",
                "configured": groq_provider.is_configured,
                "model": groq_provider.model,
            },
        },
    }
