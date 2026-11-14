"""Groq LLM provider integration module.

Adheres to the provider-isolation principle, ensuring LLM specifics are decoupled
from the rest of the DevPilot architecture.
"""

from typing import Any, Dict, Optional
from app.core.config import get_settings
from app.core.logging import logger

try:
    from groq import Groq, AuthenticationError, APITimeoutError, RateLimitError, APIError
    GROQ_SDK_AVAILABLE = True
except ImportError:
    GROQ_SDK_AVAILABLE = False
    Groq = None  # type: ignore
    AuthenticationError = Exception  # type: ignore
    APITimeoutError = Exception  # type: ignore
    RateLimitError = Exception  # type: ignore
    APIError = Exception  # type: ignore


class GroqProvider:
    """Encapsulated Groq LLM client."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.GROQ_API_KEY
        self.model = model or settings.GROQ_MODEL
        self.timeout = timeout or settings.GROQ_TIMEOUT_SECONDS
        self._client: Optional[Any] = None

    @property
    def is_configured(self) -> bool:
        """Check whether valid credentials are provided."""
        return bool(self.api_key and self.api_key.strip() and self.api_key != "your_groq_api_key_here")

    def _get_client(self) -> Any:
        """Lazy-initialize and return the Groq SDK client."""
        if not GROQ_SDK_AVAILABLE:
            raise RuntimeError("Groq Python SDK is not installed.")
        if not self.is_configured:
            raise ValueError("GROQ_API_KEY is not configured or contains placeholder value.")
        if self._client is None:
            self._client = Groq(api_key=self.api_key, timeout=self.timeout)
        return self._client

    def test_connection(self) -> Dict[str, Any]:
        """Perform a safe, minimal connectivity test against Groq Cloud.

        Never leaks API keys or internal trace secrets in responses.
        """
        if not self.is_configured:
            return {
                "configured": False,
                "status": "not_configured",
                "provider": "groq",
                "model": self.model,
                "message": "Groq API key is not configured. Set GROQ_API_KEY in your environment.",
            }

        if not GROQ_SDK_AVAILABLE:
            return {
                "configured": True,
                "status": "sdk_unavailable",
                "provider": "groq",
                "model": self.model,
                "message": "Groq Python SDK library is missing.",
            }

        try:
            client = self._get_client()
            # Send a minimal 1-token prompt to verify authentication and responsiveness
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=2,
            )
            return {
                "configured": True,
                "status": "connected",
                "provider": "groq",
                "model": self.model,
                "message": "Successfully connected to Groq Cloud API.",
            }
        except AuthenticationError:
            logger.warning("Groq authentication failure: invalid API key.")
            return {
                "configured": True,
                "status": "auth_error",
                "provider": "groq",
                "model": self.model,
                "message": "Authentication failed. Please verify your GROQ_API_KEY.",
            }
        except APITimeoutError:
            logger.warning("Groq request timed out.")
            return {
                "configured": True,
                "status": "timeout",
                "provider": "groq",
                "model": self.model,
                "message": f"Connection timed out after {self.timeout}s.",
            }
        except RateLimitError as e:
            logger.warning(f"Groq rate limit encountered: {e}")
            return {
                "configured": True,
                "status": "rate_limited",
                "provider": "groq",
                "model": self.model,
                "message": "Groq rate limit reached. Free-tier limit momentarily exceeded.",
            }
        except APIError as e:
            logger.error(f"Groq API error encountered: {e}")
            return {
                "configured": True,
                "status": "api_error",
                "provider": "groq",
                "model": self.model,
                "message": "Groq API returned an error.",
            }
        except Exception as e:
            logger.error(f"Unexpected error testing Groq connection: {e}")
            return {
                "configured": True,
                "status": "error",
                "provider": "groq",
                "model": self.model,
                "message": "An unexpected error occurred while contacting Groq.",
            }


_groq_provider_instance: Optional[GroqProvider] = None


def get_groq_provider() -> GroqProvider:
    """Return the global GroqProvider singleton."""
    global _groq_provider_instance
    if _groq_provider_instance is None:
        _groq_provider_instance = GroqProvider()
    return _groq_provider_instance
