"""Unit tests for Code Reviewer Agent (Chapter 4)."""

from app.agents.code_reviewer import CodeReviewerAgent
from app.agents.schemas import CodeReviewOutput, ReviewIssue


def test_parse_review_response_blocks_on_critical():
    reviewer = CodeReviewerAgent()
    json_payload = """{
  "outcome": "APPROVED",
  "summary": "Dangerous code detected.",
  "correctness_assessment": "Unsafe",
  "security_assessment": "Critical injection",
  "quality_score": 3,
  "issues": [
    {
      "severity": "CRITICAL",
      "file_path": "auth.js",
      "line_number": 2,
      "description": "Arbitrary code execution via eval",
      "suggested_fix": "Remove eval call"
    }
  ],
  "approval_recommendation": "Block deployment immediately."
}"""
    result = reviewer.parse_review_response(json_payload)
    # Critical issue MUST override APPROVED to BLOCKED
    assert result.outcome == "BLOCKED"
    assert result.quality_score == 3
    assert len(result.issues) == 1
    assert result.issues[0].severity == "CRITICAL"


def test_parse_review_response_changes_requested_on_high():
    reviewer = CodeReviewerAgent()
    json_payload = """{
  "outcome": "APPROVED",
  "summary": "Missing error handling in async route.",
  "correctness_assessment": "Partially correct",
  "security_assessment": "Moderate risk",
  "quality_score": 6,
  "issues": [
    {
      "severity": "HIGH",
      "file_path": "src/app.js",
      "line_number": 15,
      "description": "Unhandled promise rejection risk",
      "suggested_fix": "Wrap in try/catch block"
    }
  ],
  "approval_recommendation": "Request Developer to wrap in try/catch."
}"""
    result = reviewer.parse_review_response(json_payload)
    assert result.outcome == "CHANGES_REQUESTED"
    assert result.quality_score == 6
    assert len(result.issues) == 1


def test_parse_review_response_clean_approved():
    reviewer = CodeReviewerAgent()
    json_payload = """{
  "outcome": "APPROVED",
  "summary": "Clean and well-tested implementation.",
  "correctness_assessment": "Fully satisfies requirements.",
  "security_assessment": "Secure with bcrypt and token expiration.",
  "quality_score": 9,
  "issues": [],
  "approval_recommendation": "Proceed to delivery."
}"""
    result = reviewer.parse_review_response(json_payload)
    assert result.outcome == "APPROVED"
    assert result.quality_score == 9
    assert len(result.issues) == 0
