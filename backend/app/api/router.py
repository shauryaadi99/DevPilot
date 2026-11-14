"""Centralized API Router configuration."""

from fastapi import APIRouter
from app.api.v1 import health, llm, github, tasks

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(llm.router)
api_router.include_router(github.router)
api_router.include_router(tasks.router)

