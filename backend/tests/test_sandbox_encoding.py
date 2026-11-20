"""Regression tests for Windows subprocess encoding safety in SandboxService.

Ensures UTF-8 characters with continuation byte 0x8f (e.g. Jest bullet U+25CF)
and corrupted byte sequences are decoded safely without raising UnicodeDecodeError.
"""

import sys
from pathlib import Path
import pytest

from app.services.sandbox_service import SandboxService


def test_subprocess_decodes_bullet_byte_0x8f(tmp_path: Path):
    """Verify that byte 0x8f in Jest bullet character U+25CF (0xE2 0x97 0x8F) decodes cleanly."""
    sandbox = SandboxService()
    # Write the exact 3-byte UTF-8 sequence for bullet point '●' (b'\xe2\x97\x8f')
    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(b'\\xe2\\x97\\x8f Password Reset Endpoints > should return 400\\n'); sys.stdout.flush()",
    ]
    res = sandbox.run_command(cmd, tmp_path, timeout=10.0)

    assert res.exit_code == 0
    assert res.error is None
    # Must correctly decode to the unicode character '●'
    assert "●" in res.stdout
    assert "Password Reset Endpoints" in res.stdout
    # Must never fail with charmap or cp1252 error in stderr
    assert "charmap" not in res.stderr
    assert "UnicodeDecodeError" not in res.stderr


def test_subprocess_handles_corrupt_binary_bytes_with_replace(tmp_path: Path):
    """Verify that undefined binary bytes (including orphaned 0x8f) do not raise UnicodeDecodeError."""
    sandbox = SandboxService()
    # Write raw undefined bytes in CP1252/UTF-8
    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.buffer.write(b'\\x8f\\xff\\xfe corrupted binary stream\\n'); sys.stdout.flush()",
    ]
    res = sandbox.run_command(cmd, tmp_path, timeout=10.0)

    assert res.exit_code == 0
    assert res.error is None
    # errors="replace" substitutes \ufffd for invalid bytes
    assert "\ufffd" in res.stdout
    assert "corrupted binary stream" in res.stdout
    assert "UnicodeDecodeError" not in res.stderr


def test_sanitize_env_preserves_utf8_encoding_variables():
    """Verify that _sanitize_env sets UTF-8 environment variables for child processes."""
    sandbox = SandboxService()
    clean_env = sandbox._sanitize_env()

    assert clean_env.get("PYTHONIOENCODING") == "utf-8"
    assert clean_env.get("PYTHONUTF8") == "1"

