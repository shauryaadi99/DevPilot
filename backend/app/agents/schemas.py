"""Pydantic schemas for specialized agents' structured outputs."""

from typing import Any, Dict, List
from pydantic import BaseModel, Field


class ProductAnalystOutput(BaseModel):
    """Validated structured output from the Product Analyst Agent."""

    requirement_summary: str = Field(description="Clear, concise summary of what needs to be built.")
    functional_requirements: List[str] = Field(description="Explicit functional deliverables and capabilities.")
    nonfunctional_requirements: List[str] = Field(description="Performance, security, maintainability, or UX constraints.")
    acceptance_criteria: List[str] = Field(description="Testable acceptance criteria in Given/When/Then format.")
    ambiguities: List[str] = Field(description="Identified ambiguities in the user request with assumed defaults.")
    clarification_questions: List[str] = Field(description="Optional questions for the user if critical decisions remain open.")


class FileToCreate(BaseModel):
    """Specification of a new file to be created."""
    path: str = Field(description="Relative path of the new file.")
    purpose: str = Field(description="Detailed purpose of the new file.")


class FileToModify(BaseModel):
    """Specification of an existing file to be modified."""
    path: str = Field(description="Relative path of the existing file.")
    reason: str = Field(description="Justification for why this file must be modified.")
    changes_summary: str = Field(description="Summary of changes to be made.")


class ApiContractChange(BaseModel):
    """Specification of an API contract addition or change."""
    endpoint: str = Field(description="HTTP path or endpoint identifier.")
    method: str = Field(description="HTTP method (GET, POST, PUT, DELETE, etc.).")
    description: str = Field(description="Description of request/response payload changes.")


class ImplementationStep(BaseModel):
    """Ordered step in the implementation plan."""
    step_number: int = Field(description="Sequential step index.")
    title: str = Field(description="Brief title of the step.")
    description: str = Field(description="Detailed actionable instructions for this step.")
    affected_files: List[str] = Field(description="List of file paths involved in this step.")


class ArchitectPlanOutput(BaseModel):
    """Validated structured output from the Architect Agent."""

    summary: str = Field(description="Executive summary of the architectural strategy.")
    repository_understanding: str = Field(description="Synthesis of existing codebase architecture, languages, and conventions.")
    confirmed_observations: List[str] = Field(description="Confirmed facts established directly from inspected repository files.")
    files_to_create: List[FileToCreate] = Field(description="New files that must be created.")
    files_to_modify: List[FileToModify] = Field(description="Existing files that must be modified.")
    api_contract_changes: List[ApiContractChange] = Field(description="API or data-contract modifications required.")
    implementation_steps: List[ImplementationStep] = Field(description="Step-by-step ordered sequence of changes.")
    dependencies: List[str] = Field(description="Any new libraries or packages required (prefer zero).")
    testing_strategy: Dict[str, Any] = Field(description="Test plan covering unit, integration, and verification steps.")
    risks_and_assumptions: List[str] = Field(description="Identified risks, edge cases, and explicit assumptions made.")
