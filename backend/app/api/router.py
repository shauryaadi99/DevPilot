"""Centralized API Router configuration."""

from fastapi import APIRouter
from app.api.v1 import health, llm, github, tasks, auth, session, delivery

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(llm.router)
api_router.include_router(auth.router)
api_router.include_router(session.router)
api_router.include_router(github.router)
api_router.include_router(tasks.router)
api_router.include_router(delivery.router)
