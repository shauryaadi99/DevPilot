"""Script to clear all task, execution, planning, QA, review, and delivery data.
Preserves user accounts, PAT credentials, and database schema so the platform
can be tested from Chapter 1 with a completely clean slate.
"""

import os
import stat
import sys
import shutil
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.db.session import SessionLocal, engine
from app.core.config import get_settings


def _remove_readonly(func, path, excinfo):
    """Clear the readonly bit and reattempt removal on Windows."""
    try:
        os.chmod(path, stat.S_IWRITE)
        func(path)
    except Exception:
        pass


def clear_data():
    db = SessionLocal()
    try:
        print("Clearing task-related records from database...")
        # Clear in reverse foreign-key order or with CASCADE
        tables_to_clear = [
            "pull_requests",
            "delivery_approvals",
            "code_review_reports",
            "qa_reports",
            "file_changes",
            "execution_logs",
            "execution_locks",
            "task_executions",
            "plan_approvals",
            "implementation_plans",
            "requirement_analyses",
            "inspection_results",
            "tasks",
        ]

        with engine.begin() as conn:
            for table in tables_to_clear:
                try:
                    conn.execute(text(f"DELETE FROM {table};"))
                    print(f"  [OK] Cleared table '{table}'")
                except Exception as e:
                    print(f"  [SKIP] Table '{table}': {e}")

            # Reset active task and chapter in sessions
            try:
                conn.execute(text("UPDATE user_sessions SET active_task_id = NULL, active_chapter = '1';"))
                print("  [OK] Reset active_task_id to NULL and active_chapter to '1' in user_sessions")
            except Exception as e:
                print(f"  [INFO] user_sessions update: {e}")

        print("Database task data cleared successfully.")

        # Clean all workspaces directories
        workspace_locations = [
            Path(get_settings().WORKSPACE_ROOT).resolve(),
            (backend_dir.parent / "workspaces").resolve(),
        ]

        for ws_dir in workspace_locations:
            if ws_dir.exists():
                print(f"Cleaning workspaces in {ws_dir}...")
                for item in ws_dir.iterdir():
                    if item.is_dir():
                        try:
                            shutil.rmtree(item, onerror=_remove_readonly)
                            print(f"  [OK] Removed workspace '{item.name}'")
                        except Exception as e:
                            print(f"  [WARN] Could not remove '{item.name}': {e}")
                    elif item.name != ".gitkeep":
                        try:
                            item.unlink()
                            print(f"  [OK] Removed file '{item.name}'")
                        except Exception:
                            pass
                (ws_dir / ".gitkeep").touch(exist_ok=True)

        print("\nAll data reset complete! Ready to start Chapter 1 from a completely clean slate.")
    finally:
        db.close()


if __name__ == "__main__":
    clear_data()
