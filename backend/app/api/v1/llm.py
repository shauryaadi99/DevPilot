"""LLM connectivity and verification endpoint for Chapter 1."""

from fastapi import APIRouter
from app.integrations.groq_client import get_groq_provider

router = APIRouter(prefix="/api/v1/llm", tags=["LLM"])


@router.get("/status", summary="Check LLM Configuration Status")
async def get_llm_status():
    """Return the current LLM configuration state without executing external queries."""
    groq_provider = get_groq_provider()
    return {
        "provider": "groq",
        "configured": groq_provider.is_configured,
        "model": groq_provider.model,
    }


@router.post("/test", summary="Test Groq Cloud Connectivity")
async def test_llm_connection():
    """Perform a live verification test against the Groq Cloud endpoint."""
    groq_provider = get_groq_provider()
    result = groq_provider.test_connection()
    return result
