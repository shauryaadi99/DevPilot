"""Tests for Groq LLM integration module."""

from unittest.mock import MagicMock, patch
from app.integrations.groq_client import GroqProvider, get_groq_provider
from groq import AuthenticationError, APITimeoutError


def test_groq_unconfigured_behavior():
    """Verify provider behavior when no API key is configured."""
    provider = GroqProvider(api_key="")
    assert not provider.is_configured

    result = provider.test_connection()
    assert result["configured"] is False
    assert result["status"] == "not_configured"
    assert "api_key" not in result
    assert result["provider"] == "groq"


def test_groq_placeholder_key_detected():
    """Verify provider treats placeholder string as unconfigured."""
    provider = GroqProvider(api_key="your_groq_api_key_here")
    assert not provider.is_configured
    result = provider.test_connection()
    assert result["configured"] is False
    assert result["status"] == "not_configured"


def test_groq_successful_mock_call():
    """Verify test_connection returns connected on successful API response."""
    provider = GroqProvider(api_key="gsk_mock_test_key_12345")
    assert provider.is_configured

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.test_connection()
        assert result["configured"] is True
        assert result["status"] == "connected"
        assert result["provider"] == "groq"
        assert "gsk_mock_test_key_12345" not in str(result)


def test_groq_authentication_error_handling():
    """Verify authentication failure is cleanly caught and reported."""
    provider = GroqProvider(api_key="gsk_invalid_mock_key")

    mock_client = MagicMock()
    mock_request = MagicMock()
    mock_client.chat.completions.create.side_effect = AuthenticationError(
        "Invalid API Key", response=MagicMock(status_code=401), body={"error": "unauthorized"}
    )

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.test_connection()
        assert result["status"] == "auth_error"
        assert result["configured"] is True
        assert "gsk_invalid_mock_key" not in str(result)


def test_groq_timeout_handling():
    """Verify request timeout is caught and reported."""
    provider = GroqProvider(api_key="gsk_valid_mock_key", timeout=5.0)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = APITimeoutError(request=MagicMock())

    with patch.object(provider, "_get_client", return_value=mock_client):
        result = provider.test_connection()
        assert result["status"] == "timeout"
        assert result["configured"] is True
        assert "5.0" in result["message"]


def test_groq_fallback_key_on_failure():
    """Verify that when the primary key fails with RateLimitError, the fallback key is used."""
    from groq import RateLimitError
    provider = GroqProvider()
    provider.get_available_keys = lambda: ["gsk_primary_key_rate_limited", "gsk_fallback_key_working"]

    primary_raw_client = MagicMock()
    primary_raw_client.chat.completions.create.side_effect = RateLimitError(
        "Rate limit reached", response=MagicMock(status_code=429), body={}
    )

    fallback_raw_client = MagicMock()
    fallback_response = MagicMock()
    fallback_response.choices = [MagicMock(message=MagicMock(content="Fallback response"))]
    fallback_raw_client.chat.completions.create.return_value = fallback_response

    def mock_get_raw(key):
        if key == "gsk_primary_key_rate_limited":
            return primary_raw_client
        return fallback_raw_client

    with patch.object(provider, "_get_raw_client", side_effect=mock_get_raw):
        client = provider._get_client()
        res = client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "hello"}],
        )
        assert res.choices[0].message.content == "Fallback response"
        assert primary_raw_client.chat.completions.create.called
        assert fallback_raw_client.chat.completions.create.called

