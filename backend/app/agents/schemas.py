"""Pydantic schemas for specialized agents' structured outputs."""

from typing import Any, Dict, List, Union
from pydantic import BaseModel, Field, field_validator


def _flatten_string_list(v: Any) -> List[str]:
    """Helper to safely flatten nested lists or strings into List[str]."""
    if not v:
        return []
    if isinstance(v, str):
        return [v.strip()]
    if isinstance(v, list):
        result = []
        for item in v:
            if isinstance(item, list):
                result.extend(_flatten_string_list(item))
            elif isinstance(item, str) and item.strip():
                result.append(item.strip())
            elif isinstance(item, dict):
                result.append(str(item))
        return result
    return [str(v)]


class ProductAnalystOutput(BaseModel):
    """Validated structured output from the Product Analyst Agent."""

    requirement_summary: str = Field(description="Clear, concise summary of what needs to be built.")
    functional_requirements: List[str] = Field(default_factory=list, description="Explicit functional deliverables and capabilities.")
    nonfunctional_requirements: List[str] = Field(default_factory=list, description="Performance, security, maintainability, or UX constraints.")
    acceptance_criteria: List[str] = Field(default_factory=list, description="Testable acceptance criteria in Given/When/Then format.")
    ambiguities: List[str] = Field(default_factory=list, description="Identified ambiguities in the user request with assumed defaults.")
    clarification_questions: List[str] = Field(default_factory=list, description="Optional questions for the user if critical decisions remain open.")

    @field_validator("functional_requirements", "nonfunctional_requirements", "acceptance_criteria", "ambiguities", "clarification_questions", mode="before")
    @classmethod
    def normalize_string_lists(cls, v: Any) -> List[str]:
        return _flatten_string_list(v)


class FileToCreate(BaseModel):
    """Specification of a new file to be created."""
    path: str = Field(description="Relative path of the new file.")
    purpose: str = Field(default="Create file for implementation.", description="Detailed purpose of the new file.")


class FileToModify(BaseModel):
    """Specification of an existing file to be modified."""
    path: str = Field(description="Relative path of the existing file.")
    reason: str = Field(default="Modify file for implementation.", description="Justification for why this file must be modified.")
    changes_summary: str = Field(default="Apply necessary updates.", description="Summary of changes to be made.")


class ApiContractChange(BaseModel):
    """Specification of an API contract addition or change."""
    endpoint: str = Field(description="HTTP path or endpoint identifier.")
    method: str = Field(default="POST", description="HTTP method (GET, POST, PUT, DELETE, etc.).")
    description: str = Field(default="Endpoint update for requirement.", description="Description of request/response payload changes.")


class ImplementationStep(BaseModel):
    """Ordered step in the implementation plan."""
    step_number: int = Field(default=1, description="Sequential step index.")
    title: str = Field(description="Brief title of the step.")
    description: str = Field(default="", description="Detailed actionable instructions for this step.")
    affected_files: List[str] = Field(default_factory=list, description="List of file paths involved in this step.")

    @field_validator("affected_files", mode="before")
    @classmethod
    def normalize_affected_files(cls, v: Any) -> List[str]:
        return _flatten_string_list(v)


class ArchitectPlanOutput(BaseModel):
    """Validated structured output from the Architect Agent."""

    summary: str = Field(description="Executive summary of the architectural strategy.")
    repository_understanding: str = Field(default="Repository stack and conventions identified.", description="Synthesis of existing codebase architecture, languages, and conventions.")
    confirmed_observations: List[str] = Field(default_factory=list, description="Confirmed facts established directly from inspected repository files.")
    files_to_create: List[FileToCreate] = Field(default_factory=list, description="New files that must be created.")
    files_to_modify: List[FileToModify] = Field(default_factory=list, description="Existing files that must be modified.")
    api_contract_changes: List[ApiContractChange] = Field(default_factory=list, description="API or data-contract modifications required.")
    implementation_steps: List[ImplementationStep] = Field(default_factory=list, description="Step-by-step ordered sequence of changes.")
    dependencies: List[str] = Field(default_factory=list, description="Any new libraries or packages required (prefer zero).")
    testing_strategy: Dict[str, Any] = Field(default_factory=dict, description="Test plan covering unit, integration, and verification steps.")
    risks_and_assumptions: List[str] = Field(default_factory=list, description="Identified risks, edge cases, and explicit assumptions made.")

    @field_validator("confirmed_observations", "dependencies", "risks_and_assumptions", mode="before")
    @classmethod
    def normalize_string_lists(cls, v: Any) -> List[str]:
        return _flatten_string_list(v)

    @field_validator("testing_strategy", mode="before")
    @classmethod
    def normalize_testing_strategy(cls, v: Any) -> Dict[str, Any]:
        if not v:
            return {"unit_tests": [], "integration_tests": []}
        if isinstance(v, dict):
            return v
        if isinstance(v, list):
            return {"unit_tests": _flatten_string_list(v), "integration_tests": []}
        if isinstance(v, str):
            return {"unit_tests": [v], "integration_tests": []}
        return {"unit_tests": [str(v)]}

    @field_validator("files_to_create", mode="before")
    @classmethod
    def normalize_files_to_create(cls, v: Any) -> List[Any]:
        if not v:
            return []
        if isinstance(v, list):
            items = []
            for item in v:
                if isinstance(item, str):
                    items.append({"path": item, "purpose": "Create file for implementation."})
                elif isinstance(item, dict):
                    items.append({
                        "path": item.get("path") or item.get("file") or item.get("name") or "new_file",
                        "purpose": item.get("purpose") or item.get("description") or "Create file for implementation.",
                    })
                else:
                    items.append(item)
            return items
        return []

    @field_validator("files_to_modify", mode="before")
    @classmethod
    def normalize_files_to_modify(cls, v: Any) -> List[Any]:
        if not v:
            return []
        if isinstance(v, list):
            items = []
            for item in v:
                if isinstance(item, str):
                    items.append({"path": item, "reason": "Modify file for implementation.", "changes_summary": "Apply required updates."})
                elif isinstance(item, dict):
                    items.append({
                        "path": item.get("path") or item.get("file") or item.get("name") or "modified_file",
                        "reason": item.get("reason") or item.get("purpose") or "Modify file for implementation.",
                        "changes_summary": item.get("changes_summary") or item.get("changes") or item.get("description") or "Apply updates.",
                    })
                else:
                    items.append(item)
            return items
        return []

    @field_validator("implementation_steps", mode="before")
    @classmethod
    def normalize_implementation_steps(cls, v: Any) -> List[Any]:
        if not v:
            return []
        if isinstance(v, list):
            items = []
            for idx, item in enumerate(v, start=1):
                if isinstance(item, str):
                    items.append({
                        "step_number": idx,
                        "title": item[:40],
                        "description": item,
                        "affected_files": [],
                    })
                elif isinstance(item, dict):
                    aff = item.get("affected_files") or item.get("files") or []
                    if isinstance(aff, str):
                        aff = [aff]
                    items.append({
                        "step_number": item.get("step_number") or idx,
                        "title": item.get("title") or item.get("step") or f"Step {idx}",
                        "description": item.get("description") or item.get("details") or item.get("title") or f"Execute step {idx}",
                        "affected_files": _flatten_string_list(aff),
                    })
                else:
                    items.append(item)
            return items
        return []


