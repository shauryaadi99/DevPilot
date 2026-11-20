"""GitHub integration endpoints for repository authorization and browsing.

Supports both direct token header and session-based encrypted PAT resolution.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.v1.auth import get_optional_current_user
from app.db.session import get_db
from app.db.models import Repository, User, UserSession
from app.integrations.github_client import GitHubClient, GitHubError
from app.core.logging import logger

router = APIRouter(prefix="/api/v1/github", tags=["GitHub"])


class ConnectRequest(BaseModel):
    token: str


class SelectRepoRequest(BaseModel):
    github_id: Optional[int] = None
    name: str
    full_name: str
    owner: str
    default_branch: str = "main"
    is_private: bool = False
    html_url: str
    description: Optional[str] = None


@router.post("/connect", summary="Validate GitHub Token and Connect User")
async def connect_github(payload: ConnectRequest):
    """Validate GitHub token and return authenticated user details."""
    token = payload.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="GitHub token must not be empty.")

    client = GitHubClient(token=token)
    try:
        user_info = await client.get_authenticated_user()
        return {
            "status": "connected",
            "user": user_info,
        }
    except GitHubError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error validating GitHub token: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to GitHub.")


@router.get("/repos", summary="List Authorized GitHub Repositories")
async def list_repositories(
    request: Request,
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
):
    """List accessible repositories using session encrypted PAT or explicit token header."""
    token = x_github_token
    if not token and auth_context:
        _, _, decrypted_pat = auth_context
        token = decrypted_pat

    if not token:
        raise HTTPException(
            status_code=401,
            detail="GitHub token required. Please sign in and configure a GitHub PAT.",
        )

    client = GitHubClient(token=token)
    try:
        repos = await client.list_repositories(limit=50)
        return {"repositories": repos}
    except GitHubError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing GitHub repositories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve repositories.")


def _repo_to_dict(repo: Repository) -> dict:
    return {
        "id": repo.id,
        "user_id": repo.user_id,
        "github_id": repo.github_id,
        "name": repo.name,
        "full_name": repo.full_name,
        "owner": repo.owner,
        "default_branch": repo.default_branch,
        "is_private": repo.is_private,
        "html_url": repo.html_url,
        "description": repo.description,
        "created_at": repo.created_at.isoformat() if repo.created_at else None,
        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
    }


@router.get("/saved-repos", summary="List Previously Selected Repositories")
def list_saved_repositories(
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """List repositories persisted in PostgreSQL for the active user."""
    query = db.query(Repository)
    if auth_context:
        user, _, _ = auth_context
        query = query.filter((Repository.user_id == user.id) | (Repository.user_id.is_(None)))
    repos = query.order_by(Repository.updated_at.desc()).all()
    return {"repositories": [_repo_to_dict(r) for r in repos]}


@router.post("/select", summary="Select and Persist Repository")
def select_repository(
    payload: SelectRepoRequest,
    auth_context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Select a repository for engineering tasks and persist it in database."""
    user_id: Optional[str] = None
    session: Optional[UserSession] = None
    if auth_context:
        user, session, _ = auth_context
        user_id = user.id

    # Check if already registered
    existing = db.query(Repository).filter(Repository.full_name == payload.full_name).first()
    if existing:
        existing.default_branch = payload.default_branch
        existing.is_private = payload.is_private
        existing.html_url = payload.html_url
        existing.description = payload.description
        if user_id and not existing.user_id:
            existing.user_id = user_id
        if session:
            if session.active_repo_id != existing.id:
                session.active_repo_id = existing.id
                session.active_task_id = None
            else:
                session.active_repo_id = existing.id
        db.commit()
        db.refresh(existing)
        return {"status": "selected", "repository": _repo_to_dict(existing)}

    repo = Repository(
        user_id=user_id,
        github_id=payload.github_id,
        name=payload.name,
        full_name=payload.full_name,
        owner=payload.owner,
        default_branch=payload.default_branch,
        is_private=payload.is_private,
        html_url=payload.html_url,
        description=payload.description,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    if session:
        session.active_repo_id = repo.id
        session.active_task_id = None
        db.commit()

    return {"status": "created", "repository": _repo_to_dict(repo)}
