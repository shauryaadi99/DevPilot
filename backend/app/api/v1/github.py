"""GitHub integration endpoints for repository authorization and browsing."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.db.models import Repository
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
    x_github_token: Optional[str] = Header(None, alias="X-GitHub-Token"),
):
    """List accessible repositories using the provided token header."""
    if not x_github_token:
        raise HTTPException(status_code=401, detail="X-GitHub-Token header is required to list repositories.")

    client = GitHubClient(token=x_github_token)
    try:
        repos = await client.list_repositories(limit=50)
        return {"repositories": repos}
    except GitHubError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except Exception as e:
        logger.error(f"Error listing GitHub repositories: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve repositories.")


@router.post("/select", summary="Select and Persist Repository")
def select_repository(
    payload: SelectRepoRequest,
    db: Session = Depends(get_db),
):
    """Select a repository for engineering tasks and persist it in database."""
    # Check if already registered
    existing = db.query(Repository).filter(Repository.full_name == payload.full_name).first()
    if existing:
        # Update metadata
        existing.default_branch = payload.default_branch
        existing.is_private = payload.is_private
        existing.html_url = payload.html_url
        existing.description = payload.description
        db.commit()
        db.refresh(existing)
        return {"status": "selected", "repository": existing}

    repo = Repository(
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
    return {"status": "created", "repository": repo}
