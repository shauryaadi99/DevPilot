"""Authentication and GitHub Personal Access Token (PAT) management router.

Handles:
- GitHub OAuth Web Flow login & callback
- Dev login fallback for frictionless local testing
- Encrypted PAT submission, validation, masking, and status check
- User logout
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.core.security import encrypt_pat, decrypt_pat, mask_pat, generate_session_token
from app.db.session import get_db
from app.db.models import User, UserSession, UserCredential, Repository
from app.integrations.github_client import GITHUB_API_BASE, GitHubError

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Credentials"])


# ── Dependency: Get Authenticated User & Session ─────────────────────────────


def get_current_user_and_session(
    request: Request,
    devpilot_session_id: Optional[str] = Cookie(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
) -> tuple[User, UserSession, Optional[str]]:
    """Resolve active user, session, and decrypted PAT from cookie or header."""
    token = devpilot_session_id or x_session_id
    if not token:
        # For development / initial load, check if there's any active user session
        # or require authentication
        raise HTTPException(status_code=401, detail="Authentication required. Please sign in with GitHub.")

    session = (
        db.query(UserSession)
        .filter(UserSession.id == token)
        .first()
    )
    if not session:
        raise HTTPException(status_code=401, detail="Invalid session token.")

    if session.expires_at < datetime.now(timezone.utc):
        db.delete(session)
        db.commit()
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")

    user = session.user
    decrypted_pat: Optional[str] = None
    if user.credential and user.credential.is_valid:
        try:
            decrypted_pat = decrypt_pat(user.credential.encrypted_pat)
        except Exception as e:
            logger.warning(f"Failed to decrypt PAT for user {user.username}: {e}")

    return user, session, decrypted_pat


def get_optional_current_user(
    request: Request,
    devpilot_session_id: Optional[str] = Cookie(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
) -> Optional[tuple[User, UserSession, Optional[str]]]:
    """Optionally resolve user/session without raising 401."""
    token = devpilot_session_id or x_session_id
    if not token:
        # Check if single default user exists in local development
        user = db.query(User).first()
        if user:
            # Check or create dev session
            session = db.query(UserSession).filter(UserSession.user_id == user.id).first()
            if not session:
                session = UserSession(
                    id=generate_session_token(),
                    user_id=user.id,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
            decrypted_pat = None
            if user.credential and user.credential.is_valid:
                try:
                    decrypted_pat = decrypt_pat(user.credential.encrypted_pat)
                except Exception:
                    pass
            return user, session, decrypted_pat
        return None

    try:
        return get_current_user_and_session(request, devpilot_session_id, x_session_id, db)
    except HTTPException:
        return None


# ── Schemas ──────────────────────────────────────────────────────────────────


class PatSubmitRequest(BaseModel):
    token: str


class DevLoginRequest(BaseModel):
    username: str
    name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


# ── OAuth Endpoints ──────────────────────────────────────────────────────────


@router.get("/github/login", summary="Initiate GitHub OAuth Flow")
def github_login():
    """Redirect to GitHub's authorization page or return OAuth authorize URL."""
    settings = get_settings()
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=400,
            detail="GITHUB_CLIENT_ID is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env.",
        )

    scopes = "read:user,user:email"
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={settings.GITHUB_CLIENT_ID}"
        f"&scope={scopes}"
        f"&redirect_uri={settings.GITHUB_REDIRECT_URI}"
    )
    return {"oauth_url": url}


@router.get("/github/callback", summary="GitHub OAuth Callback")
async def github_callback(code: str, response: Response, db: Session = Depends(get_db)):
    """Exchange OAuth code for access token, upsert user, and create session."""
    settings = get_settings()
    if not settings.GITHUB_CLIENT_ID or not settings.GITHUB_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="OAuth credentials not configured on backend.")

    # 1. Exchange code for access token
    token_url = "https://github.com/login/oauth/access_token"
    payload = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "client_secret": settings.GITHUB_CLIENT_SECRET,
        "code": code,
        "redirect_uri": settings.GITHUB_REDIRECT_URI,
    }
    headers = {"Accept": "application/json"}

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, json=payload, headers=headers)
        if token_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to exchange OAuth code with GitHub.")

        token_data = token_res.json()
        oauth_token = token_data.get("access_token")
        if not oauth_token:
            err = token_data.get("error_description") or "OAuth token missing in response."
            raise HTTPException(status_code=400, detail=err)

        # 2. Fetch authenticated user profile
        user_res = await client.get(
            f"{GITHUB_API_BASE}/user",
            headers={"Authorization": f"Bearer {oauth_token}", "User-Agent": "DevPilot-Agent-Platform"},
        )
        if user_res.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch GitHub user profile.")
        gh_user = user_res.json()

    # 3. Upsert User in PostgreSQL
    user = db.query(User).filter(User.github_id == gh_user["id"]).first()
    if not user:
        user = User(
            github_id=gh_user["id"],
            username=gh_user["login"],
            name=gh_user.get("name") or gh_user["login"],
            email=gh_user.get("email"),
            avatar_url=gh_user.get("avatar_url"),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.username = gh_user["login"]
        user.name = gh_user.get("name") or user.name
        user.email = gh_user.get("email") or user.email
        user.avatar_url = gh_user.get("avatar_url") or user.avatar_url
        db.commit()

    # 4. Create Session
    session_id = generate_session_token()
    session = UserSession(
        id=session_id,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(session)
    db.commit()

    # 5. Set HTTP-only cookie and redirect to root
    redirect = RedirectResponse(url="http://localhost:3000/", status_code=302)
    redirect.set_cookie(
        key="devpilot_session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )
    return redirect


@router.post("/dev-login", summary="Development Login (No OAuth App Required)")
def dev_login(payload: DevLoginRequest, response: Response, db: Session = Depends(get_db)):
    """Local development login bypassing OAuth app setup when testing locally."""
    # Deterministic mock github_id from username
    mock_github_id = abs(hash(payload.username)) % (10**9)

    user = db.query(User).filter(User.username == payload.username).first()
    if not user:
        user = User(
            github_id=mock_github_id,
            username=payload.username.strip(),
            name=payload.name or payload.username,
            email=payload.email or f"{payload.username}@users.noreply.github.com",
            avatar_url=payload.avatar_url or f"https://github.com/{payload.username}.png",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    session_id = generate_session_token()
    session = UserSession(
        id=session_id,
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(session)
    db.commit()

    response.set_cookie(
        key="devpilot_session_id",
        value=session_id,
        httponly=True,
        samesite="lax",
        max_age=7 * 24 * 3600,
    )

    return {
        "status": "authenticated",
        "session_id": session_id,
        "user": {
            "id": user.id,
            "username": user.username,
            "name": user.name,
            "email": user.email,
            "avatar_url": user.avatar_url,
        },
    }


# ── PAT Management Endpoints ────────────────────────────────────────────────


@router.post("/pat", summary="Validate & Store Encrypted GitHub PAT")
async def store_pat(
    payload: PatSubmitRequest,
    response: Response,
    context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Validate user-provided GitHub PAT, encrypt it, and store in PostgreSQL. Never exposes plaintext."""
    pat = payload.token.strip()
    if not pat:
        raise HTTPException(status_code=400, detail="Personal Access Token cannot be empty.")

    # 1. Validate PAT against GitHub API
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {pat}",
        "User-Agent": "DevPilot-Agent-Platform",
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            res = await client.get(f"{GITHUB_API_BASE}/user", headers=headers)
        except Exception as e:
            raise HTTPException(status_code=503, detail=f"Failed to connect to GitHub API: {e}")

    if res.status_code == 401:
        raise HTTPException(status_code=401, detail="Invalid or expired GitHub Personal Access Token.")
    if res.status_code != 200:
        raise HTTPException(status_code=res.status_code, detail="GitHub API rejected token validation.")

    gh_user_data = res.json()
    scopes_header = res.headers.get("x-oauth-scopes", "")
    scopes = [s.strip() for s in scopes_header.split(",") if s.strip()]

    # If user context exists, use it; otherwise auto-provision user from validated GitHub account
    if context:
        user, session, _ = context
    else:
        gh_login = gh_user_data.get("login") or "github_user"
        user = db.query(User).filter(User.username == gh_login).first()
        if not user:
            user = User(
                username=gh_login,
                name=gh_user_data.get("name"),
                email=gh_user_data.get("email"),
                avatar_url=gh_user_data.get("avatar_url"),
                github_id=gh_user_data.get("id"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        session_id = generate_session_token()
        session = UserSession(
            id=session_id,
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )
        db.add(session)
        db.commit()

        response.set_cookie(
            key="devpilot_session_id",
            value=session_id,
            httponly=True,
            samesite="lax",
            max_age=7 * 24 * 3600,
        )

    # 2. Encrypt PAT
    encrypted_bytes = encrypt_pat(pat)
    masked = mask_pat(pat)

    # 3. Upsert UserCredential
    credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).first()
    if not credential:
        credential = UserCredential(
            user_id=user.id,
            encrypted_pat=encrypted_bytes,
            pat_masked=masked,
            scopes=scopes,
            is_valid=True,
            last_validated_at=datetime.now(timezone.utc),
        )
        db.add(credential)
    else:
        credential.encrypted_pat = encrypted_bytes
        credential.pat_masked = masked
        credential.scopes = scopes
        credential.is_valid = True
        credential.last_validated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(credential)

    logger.info(f"Successfully stored and encrypted PAT for user {user.username} ({masked})")

    return {
        "status": "valid",
        "pat_masked": masked,
        "scopes": scopes,
        "user": {
            "login": gh_user_data.get("login"),
            "name": gh_user_data.get("name"),
            "avatar_url": gh_user_data.get("avatar_url"),
        },
        "message": f"GitHub Personal Access Token validated and encrypted for @{user.username}.",
    }


@router.get("/pat/status", summary="Check Existing PAT Validity & Metadata")
async def get_pat_status(
    context: Optional[tuple] = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Check whether authenticated user has a valid encrypted PAT and offer reuse."""
    if not context:
        return {
            "has_pat": False,
            "is_valid": False,
            "pat_masked": None,
            "scopes": [],
            "message": "No active session.",
        }

    user, session, decrypted_pat = context

    if not user.credential:
        return {
            "has_pat": False,
            "is_valid": False,
            "pat_masked": None,
            "scopes": [],
            "message": "No Personal Access Token configured.",
        }

    # Perform lightweight validation check
    is_still_valid = user.credential.is_valid
    if decrypted_pat:
        headers = {
            "Authorization": f"Bearer {decrypted_pat}",
            "User-Agent": "DevPilot-Agent-Platform",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(f"{GITHUB_API_BASE}/user", headers=headers)
                if res.status_code == 200:
                    is_still_valid = True
                    user.credential.is_valid = True
                    user.credential.last_validated_at = datetime.now(timezone.utc)
                    db.commit()
                elif res.status_code == 401:
                    is_still_valid = False
                    user.credential.is_valid = False
                    db.commit()
        except Exception:
            pass  # Keep existing flag on network glitch

    return {
        "has_pat": True,
        "is_valid": is_still_valid,
        "pat_masked": user.credential.pat_masked,
        "scopes": user.credential.scopes,
        "last_validated_at": user.credential.last_validated_at.isoformat(),
        "message": "Valid PAT available for reuse." if is_still_valid else "PAT has expired or was revoked. Please replace it.",
    }


@router.post("/logout", summary="Logout and Clear Session")
def logout(
    response: Response,
    context: tuple = Depends(get_current_user_and_session),
    db: Session = Depends(get_db),
):
    """End the current user session and clear browser cookie."""
    _, session, _ = context
    db.delete(session)
    db.commit()

    response.delete_cookie("devpilot_session_id")
    return {"status": "logged_out", "message": "Successfully logged out."}
