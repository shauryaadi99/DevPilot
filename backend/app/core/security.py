"""Security and cryptographic helpers for DevPilot.

Handles encryption/decryption of GitHub Personal Access Tokens (PAT),
secure session token generation, and token masking.
"""

import base64
import hashlib
import os
import secrets
from typing import Optional

from cryptography.fernet import Fernet
from app.core.config import get_settings


def _get_fernet() -> Fernet:
    """Derive a 32-byte Fernet key from SECRET_KEY."""
    settings = get_settings()
    secret = settings.SECRET_KEY
    if not secret:
        # Fallback predictable seed for local development
        secret = "devpilot-default-insecure-secret-key-change-in-production"
    # Derive consistent 32-byte key via SHA-256
    derived_bytes = hashlib.sha256(secret.encode("utf-8")).digest()
    key_b64 = base64.urlsafe_b64encode(derived_bytes)
    return Fernet(key_b64)


def encrypt_pat(plain_pat: str) -> bytes:
    """Encrypt a GitHub PAT into ciphertext bytes. Never stores plaintext or hash."""
    if not plain_pat or not plain_pat.strip():
        raise ValueError("Cannot encrypt an empty token.")
    fernet = _get_fernet()
    return fernet.encrypt(plain_pat.strip().encode("utf-8"))


def decrypt_pat(encrypted_bytes: bytes) -> str:
    """Decrypt ciphertext bytes back to the original GitHub PAT."""
    fernet = _get_fernet()
    decrypted = fernet.decrypt(encrypted_bytes)
    return decrypted.decode("utf-8")


def mask_pat(pat: str) -> str:
    """Return a masked representation of a PAT for safe UI display (e.g. ghp_••••abcd)."""
    pat = pat.strip()
    if len(pat) <= 8:
        return "••••"
    prefix = pat[:4] if "_" in pat[:5] else ""
    suffix = pat[-4:]
    return f"{prefix}••••{suffix}"


def generate_session_token() -> str:
    """Generate a high-entropy URL-safe session token for HTTP-only cookies."""
    return secrets.token_urlsafe(32)

