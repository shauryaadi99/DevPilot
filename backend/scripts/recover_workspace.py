"""Recover the forensic workspace for task 37078adf.

Reads loose Git objects from the partially-deleted temp workspace,
clones the upstream repo fresh, applies recovered blobs, commits,
and updates the DB workspace_path record.

Run from d:\\proj\\DevPilot\\backend:
    python scripts/recover_workspace.py

DO NOT touch the original forensic remnants in Temp.
"""

import os
import sys
import zlib
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

from app.services.git_service import get_workspace_root

TASK_ID = "37078adf-10e9-4ab3-bed0-8e11e89a089f"
EXECUTION_ID = "4ce7e708-7252-4c85-9303-ea55e330db57"
REPO_URL = "https://github.com/shauryaadi99/devpilot-taskflow-test"
DEFAULT_BRANCH = "main"
BRANCH_NAME = f"devpilot/task-{TASK_ID}"
COMMIT_MSG = f"feat(devpilot): implement task {TASK_ID}"
AUTHOR_NAME = "Shaurya Aditya Verma"
AUTHOR_EMAIL = "shauryaaditya99@gmail.com"

FORENSIC_ROOT = Path(r"C:\Users\BIT\AppData\Local\Temp\devpilot_workspaces") / TASK_ID
WORKSPACE_ROOT = get_workspace_root()
RECOVERY_DIR = WORKSPACE_ROOT / f"recovered-{TASK_ID[:8]}"

# Known blob SHA → repo-relative path
BLOBS = {
    "03e541f": "frontend/src/api/authApi.js",
    "0cb4811": "frontend/src/pages/ForgotPassword.jsx",
    "ac53143": "backend/src/controllers/passwordResetController.js",
    "d7b26a9": "backend/src/models/User.js",
    "e693010": "backend/src/routes/authRoutes.js",
}


def _read_blob(sha_prefix: str) -> bytes:
    """Find and decompress a loose Git object by SHA prefix."""
    objects_dir = FORENSIC_ROOT / ".git" / "objects"
    # Find matching object file
    for d in objects_dir.iterdir():
        if not d.is_dir() or len(d.name) != 2:
            continue
        for obj_file in d.iterdir():
            full_sha = d.name + obj_file.name
            if full_sha.startswith(sha_prefix):
                raw = zlib.decompress(obj_file.read_bytes())
                # Strip git object header: "blob <size>\x00<content>"
                null_idx = raw.index(b"\x00")
                return raw[null_idx + 1:]
    raise FileNotFoundError(f"Object {sha_prefix} not found in {objects_dir}")


def main():
    import subprocess
    from git import Repo, Actor

    if not FORENSIC_ROOT.exists():
        print(f"[WARN] Forensic workspace not found at {FORENSIC_ROOT}. Skipping blob recovery.")
        blobs_available = False
    else:
        blobs_available = True

    WORKSPACE_ROOT.mkdir(parents=True, exist_ok=True)

    if RECOVERY_DIR.exists():
        print(f"[INFO] Recovery dir already exists: {RECOVERY_DIR}. Skipping clone.")
        repo = Repo(str(RECOVERY_DIR))
    else:
        print(f"[INFO] Cloning {REPO_URL} into {RECOVERY_DIR} ...")
        repo = Repo.clone_from(REPO_URL, str(RECOVERY_DIR), branch=DEFAULT_BRANCH)
        print(f"[INFO] Clone done. HEAD: {repo.head.commit.hexsha[:7]}")

    # Ensure task branch
    try:
        repo.git.checkout(BRANCH_NAME)
        print(f"[INFO] Checked out existing branch {BRANCH_NAME}")
    except Exception:
        repo.git.checkout("-b", BRANCH_NAME)
        print(f"[INFO] Created branch {BRANCH_NAME}")

    if blobs_available:
        # Apply recovered blobs
        for sha_prefix, rel_path in BLOBS.items():
            dest = RECOVERY_DIR / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            try:
                content = _read_blob(sha_prefix)
                dest.write_bytes(content)
                print(f"[OK] Wrote {rel_path} ({len(content)} bytes)")
            except Exception as exc:
                print(f"[WARN] Could not recover {rel_path}: {exc}")

        if repo.is_dirty(untracked_files=True):
            repo.git.add("-A")
            author = Actor(AUTHOR_NAME, AUTHOR_EMAIL)
            commit = repo.index.commit(
                COMMIT_MSG,
                author=author,
                committer=author,
            )
            new_sha = commit.hexsha
            print(f"[OK] Committed: {new_sha[:7]} — {COMMIT_MSG}")
        else:
            new_sha = repo.head.commit.hexsha
            print(f"[INFO] No changes to commit. HEAD: {new_sha[:7]}")
    else:
        new_sha = repo.head.commit.hexsha
        print(f"[INFO] No forensic blobs available. Recovery dir ready at {RECOVERY_DIR}")

    # Update DB
    db_path = Path(__file__).parent.parent / "devpilot.db"
    if db_path.exists():
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute(
            "UPDATE task_executions SET workspace_path = ?, commit_sha = ? WHERE id = ?",
            (str(RECOVERY_DIR), new_sha, EXECUTION_ID),
        )
        conn.commit()
        rows = cur.rowcount
        conn.close()
        print(f"[DB] Updated {rows} row(s): workspace_path={RECOVERY_DIR}, commit_sha={new_sha[:7]}")
    else:
        print(f"[WARN] DB not found at {db_path}. Update manually.")

    print("\n=== Recovery complete ===")
    print(f"  Workspace : {RECOVERY_DIR}")
    print(f"  Branch    : {BRANCH_NAME}")
    print(f"  Commit    : {new_sha}")
    print(f"  Forensic  : {FORENSIC_ROOT} (untouched)")


if __name__ == "__main__":
    main()

