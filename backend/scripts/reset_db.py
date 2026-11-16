import os
import shutil
import sys
from pathlib import Path

sys.path.insert(0, os.path.abspath("backend"))

from sqlalchemy import text
from app.db.session import engine

def reset_all():
    print("=" * 60)
    print("Resetting DevPilot PostgreSQL database and workspaces...")
    print("=" * 60)

    tables_to_truncate = [
        "qa_reports",
        "code_review_reports",
        "execution_logs",
        "file_changes",
        "plan_approvals",
        "task_executions",
        "implementation_plans",
        "requirement_analyses",
        "inspection_results",
        "execution_locks",
        "tasks",
        "repositories",
        "user_sessions",
        "user_credentials",
        "users",
        "checkpoints",
        "checkpoint_blobs",
        "checkpoint_writes",
    ]

    with engine.begin() as conn:
        for table in tables_to_truncate:
            try:
                conn.execute(text(f"TRUNCATE TABLE {table} CASCADE;"))
                print(f"[OK] Truncated table: {table}")
            except Exception as e:
                print(f"[SKIP/WARN] Could not truncate {table}: {e}")

    # Clean workspace directories
    workspaces_dir = Path("backend/workspaces")
    if workspaces_dir.exists():
        for item in workspaces_dir.iterdir():
            if item.is_dir() and item.name != ".gitkeep":
                try:
                    # Windows read-only git file handling
                    def on_rm_error(func, path, exc_info):
                        import stat
                        os.chmod(path, stat.S_IWRITE)
                        func(path)
                    shutil.rmtree(item, onerror=on_rm_error)
                    print(f"[OK] Removed workspace directory: {item.name}")
                except Exception as e:
                    print(f"[WARN] Failed to remove workspace {item.name}: {e}")

    print("=" * 60)
    print("All database tables truncated and workspaces cleared successfully.")
    print("=" * 60)

    # Verification
    print("Verification of row counts:")
    with engine.connect() as conn:
        for table in tables_to_truncate:
            cnt = conn.execute(text(f"SELECT COUNT(1) FROM {table}")).scalar()
            print(f"  {table}: {cnt} rows")

if __name__ == "__main__":
    reset_all()
