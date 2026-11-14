"""Repository inspection service.

Parses repository file trees and dependency manifests to generate structured,
fact-checked intelligence for the specialized AI agents.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
import json

from app.integrations.github_client import GitHubClient
from app.core.logging import logger

# Recognizable manifest files
KNOWN_MANIFESTS = [
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "Gemfile",
    "composer.json",
    "docker-compose.yml",
    "Dockerfile",
    "README.md",
]

EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript (React)",
    ".js": "JavaScript",
    ".jsx": "JavaScript (React)",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".sh": "Shell",
}


class InspectionService:
    """Performs deep, bounded static inspection of a repository."""

    def __init__(self, github_client: GitHubClient):
        self.client = github_client

    async def inspect_repository(
        self,
        owner: str,
        repo: str,
        default_branch: str = "main",
    ) -> Dict[str, Any]:
        """Inspect repository tree, detect languages, frameworks, entrypoints, and extract manifest data."""
        logger.info(f"Starting inspection for {owner}/{repo} on branch {default_branch}")

        # 1. Fetch file tree
        tree_items = await self.client.get_tree(owner, repo, branch=default_branch)
        blob_paths = [item["path"] for item in tree_items if item["type"] == "blob"]

        total_files = len(blob_paths)
        logger.info(f"Retrieved {total_files} files from {owner}/{repo}")

        # 2. Analyze languages by extension
        lang_counts: Dict[str, int] = {}
        for path in blob_paths:
            ext = Path(path).suffix.lower()
            if ext in EXTENSION_LANGUAGE_MAP:
                lang = EXTENSION_LANGUAGE_MAP[ext]
                lang_counts[lang] = lang_counts.get(lang, 0) + 1

        detected_languages = sorted(lang_counts.keys(), key=lambda l: lang_counts[l], reverse=True)

        # 3. Detect manifests and key files
        manifests_found: List[str] = []
        for path in blob_paths:
            base_name = Path(path).name
            if base_name in KNOWN_MANIFESTS and path not in manifests_found:
                # Keep root or top-level manifests
                if path.count("/") <= 2:
                    manifests_found.append(path)

        # 4. Fetch content of top manifests (bounded to first 3KB each)
        manifests_summary: Dict[str, str] = {}
        for m_path in manifests_found[:8]:  # Limit to 8 most critical manifests
            content = await self.client.get_file_content(owner, repo, m_path, branch=default_branch)
            if content:
                # Store truncated summary for agent context
                manifests_summary[m_path] = content[:3000]

        # 5. Detect frameworks and tools from manifests & paths
        detected_frameworks: List[str] = []
        detected_entrypoints: List[str] = []
        confirmed_facts: List[str] = [
            f"Total tracked files: {total_files}",
            f"Primary detected languages: {', '.join(detected_languages[:3]) or 'Unknown'}",
        ]

        # Scan all package.json files (root and subprojects e.g., backend/, frontend/)
        for m_path, m_content in manifests_summary.items():
            if m_path.endswith("package.json"):
                try:
                    pkg_data = json.loads(m_content)
                    deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                    if "next" in deps and "Next.js" not in detected_frameworks:
                        detected_frameworks.append("Next.js")
                    if "react" in deps and "React" not in detected_frameworks:
                        detected_frameworks.append("React")
                    if "express" in deps and "Express.js" not in detected_frameworks:
                        detected_frameworks.append("Express.js")
                    if "mongoose" in deps:
                        if "Mongoose" not in detected_frameworks:
                            detected_frameworks.append("Mongoose")
                        if "MongoDB" not in detected_frameworks:
                            detected_frameworks.append("MongoDB")
                    elif "mongodb" in deps and "MongoDB" not in detected_frameworks:
                        detected_frameworks.append("MongoDB")
                    if "vite" in deps and "Vite" not in detected_frameworks:
                        detected_frameworks.append("Vite")
                    if "tailwindcss" in deps and "Tailwind CSS" not in detected_frameworks:
                        detected_frameworks.append("Tailwind CSS")

                    # Identify existing security & auth dependencies
                    if "bcrypt" in deps or "bcryptjs" in deps:
                        hasher = "bcryptjs" if "bcryptjs" in deps else "bcrypt"
                        confirmed_facts.append(f"Existing password hashing library: {hasher} (in {m_path})")
                    if "jsonwebtoken" in deps:
                        confirmed_facts.append(f"Existing JWT library: jsonwebtoken (in {m_path})")

                    pkg_name = pkg_data.get("name")
                    if pkg_name:
                        confirmed_facts.append(f"Node.js package: {pkg_name} ({m_path})")
                except Exception:
                    pass

        # Scan README for stack mentions if still missing
        if "README.md" in manifests_summary:
            readme_lower = manifests_summary["README.md"].lower()
            if "mern" in readme_lower:
                confirmed_facts.append("Identified stack pattern: MERN (MongoDB, Express, React, Node)")
                if "MongoDB" not in detected_frameworks:
                    detected_frameworks.append("MongoDB")
                if "Express.js" not in detected_frameworks:
                    detected_frameworks.append("Express.js")
                if "React" not in detected_frameworks:
                    detected_frameworks.append("React")

        # Scan python requirements
        for py_man in ["requirements.txt", "pyproject.toml"]:
            for m_path, m_content in manifests_summary.items():
                if m_path.endswith(py_man):
                    p_text = m_content.lower()
                    if "fastapi" in p_text and "FastAPI" not in detected_frameworks:
                        detected_frameworks.append("FastAPI")
                    if "django" in p_text and "Django" not in detected_frameworks:
                        detected_frameworks.append("Django")
                    if "flask" in p_text and "Flask" not in detected_frameworks:
                        detected_frameworks.append("Flask")
                    if "sqlalchemy" in p_text and "SQLAlchemy" not in detected_frameworks:
                        detected_frameworks.append("SQLAlchemy")
                    if ("pymongo" in p_text or "motor" in p_text) and "MongoDB" not in detected_frameworks:
                        detected_frameworks.append("MongoDB")
                    if "pytest" in p_text:
                        confirmed_facts.append("Test framework: Pytest")

        # Scan entry points
        common_entrypoints = [
            "backend/src/server.js", "backend/src/app.js", "backend/server.js", "backend/index.js",
            "server.js", "app.js", "src/server.js", "src/app.js", "src/index.js", "index.js",
            "frontend/src/main.jsx", "frontend/src/App.jsx", "frontend/src/index.js",
            "src/main.jsx", "src/App.jsx", "src/index.tsx", "src/main.tsx", "src/app/page.tsx",
            "main.py", "app/main.py", "src/main.py", "app.py",
            "index.ts", "src/index.ts", "src/main.rs", "main.go"
        ]
        for ep in common_entrypoints:
            if ep in blob_paths and ep not in detected_entrypoints:
                detected_entrypoints.append(ep)

        # Domain directory discovery for confirmed architectural facts
        models_found = [p for p in blob_paths if "/models/" in p or p.startswith("models/")]
        controllers_found = [p for p in blob_paths if "/controllers/" in p or p.startswith("controllers/")]
        routes_found = [p for p in blob_paths if "/routes/" in p or p.startswith("routes/")]
        pages_found = [p for p in blob_paths if "/pages/" in p or p.startswith("pages/")]

        if models_found:
            confirmed_facts.append(f"Database models: {', '.join(models_found[:6])}")
        if controllers_found:
            confirmed_facts.append(f"API controllers: {', '.join(controllers_found[:6])}")
        if routes_found:
            confirmed_facts.append(f"API routes: {', '.join(routes_found[:6])}")
        if pages_found:
            confirmed_facts.append(f"Frontend pages: {', '.join(pages_found[:6])}")

        if detected_frameworks:
            confirmed_facts.append(f"Detected frameworks: {', '.join(detected_frameworks)}")
        if detected_entrypoints:
            confirmed_facts.append(f"Identified entrypoints: {', '.join(detected_entrypoints)}")

        unknowns: List[str] = [
            "Internal deployment environment and cloud secrets",
            "Production runtime metrics and external service configurations",
        ]

        # Ensure key_paths includes architectural components and not just the first 50 alphabetically
        highlight_paths = list(dict.fromkeys(
            detected_entrypoints + models_found + controllers_found + routes_found + pages_found + blob_paths[:40]
        ))

        return {
            "tree_summary": {
                "total_files": total_files,
                "manifest_count": len(manifests_found),
                "key_paths": highlight_paths[:60],
            },
            "detected_languages": detected_languages,
            "detected_frameworks": list(set(detected_frameworks)),
            "detected_entrypoints": detected_entrypoints,
            "manifests_summary": manifests_summary,
            "confirmed_facts": confirmed_facts,
            "unknowns": unknowns,
        }

