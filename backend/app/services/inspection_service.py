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

        # Scan package.json
        if "package.json" in manifests_summary:
            try:
                pkg_data = json.loads(manifests_summary["package.json"])
                deps = {**pkg_data.get("dependencies", {}), **pkg_data.get("devDependencies", {})}
                if "next" in deps:
                    detected_frameworks.append("Next.js")
                if "react" in deps:
                    detected_frameworks.append("React")
                if "express" in deps:
                    detected_frameworks.append("Express.js")
                if "tailwindcss" in deps:
                    detected_frameworks.append("Tailwind CSS")
                confirmed_facts.append(f"Node.js package name: {pkg_data.get('name', 'unnamed')}")
            except Exception:
                pass

        # Scan python requirements
        for py_man in ["requirements.txt", "pyproject.toml"]:
            if py_man in manifests_summary:
                p_text = manifests_summary[py_man].lower()
                if "fastapi" in p_text:
                    detected_frameworks.append("FastAPI")
                if "django" in p_text:
                    detected_frameworks.append("Django")
                if "flask" in p_text:
                    detected_frameworks.append("Flask")
                if "sqlalchemy" in p_text:
                    detected_frameworks.append("SQLAlchemy")
                if "pytest" in p_text:
                    confirmed_facts.append("Test framework: Pytest")

        # Scan entry points
        common_entrypoints = [
            "main.py", "app/main.py", "src/main.py", "app.py",
            "index.ts", "src/index.ts", "src/app/page.tsx", "server.js",
            "src/main.rs", "main.go"
        ]
        for ep in common_entrypoints:
            if ep in blob_paths:
                detected_entrypoints.append(ep)

        if detected_frameworks:
            confirmed_facts.append(f"Detected frameworks: {', '.join(detected_frameworks)}")
        if detected_entrypoints:
            confirmed_facts.append(f"Identified entrypoints: {', '.join(detected_entrypoints)}")

        unknowns: List[str] = [
            "Internal deployment environment and cloud secrets",
            "Production runtime metrics and external service configurations",
        ]

        return {
            "tree_summary": {
                "total_files": total_files,
                "manifest_count": len(manifests_found),
                "key_paths": blob_paths[:50],  # Sample representative paths
            },
            "detected_languages": detected_languages,
            "detected_frameworks": list(set(detected_frameworks)),
            "detected_entrypoints": detected_entrypoints,
            "manifests_summary": manifests_summary,
            "confirmed_facts": confirmed_facts,
            "unknowns": unknowns,
        }

