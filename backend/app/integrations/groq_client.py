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


class GroqCompletionsWrapper:
    """Wrapper around client.chat.completions to transparently handle key failover."""

    def __init__(self, provider: "GroqProvider"):
        self._provider = provider

    def create(self, *args, **kwargs) -> Any:
        keys = self._provider.get_available_keys()
        if not keys:
            raise ValueError("No Groq API keys configured.")

        last_error = None
        for idx, key in enumerate(keys):
            client = self._provider._get_raw_client(key)
            try:
                return client.chat.completions.create(*args, **kwargs)
            except (AuthenticationError, RateLimitError, APITimeoutError, APIError) as exc:
                last_error = exc
                masked_key = f"...{key[-4:]}" if len(key) >= 4 else "key"
                if idx + 1 < len(keys):
                    next_key = keys[idx + 1]
                    next_masked = f"...{next_key[-4:]}" if len(next_key) >= 4 else "next_key"
                    logger.warning(
                        f"Groq API call with key {masked_key} encountered {exc.__class__.__name__}: {exc}. "
                        f"Automatically failing over to fallback key {next_masked}."
                    )
                else:
                    logger.error(f"Groq API call failed across all {len(keys)} available key(s): {exc}")
                    raise
            except Exception as exc:
                status_code = getattr(exc, "status_code", None)
                is_rate_or_size = status_code in (401, 413, 429, 500, 502, 503) or "rate_limit" in str(exc).lower() or "too large" in str(exc).lower()
                if is_rate_or_size and idx + 1 < len(keys):
                    masked_key = f"...{key[-4:]}" if len(key) >= 4 else "key"
                    next_key = keys[idx + 1]
                    next_masked = f"...{next_key[-4:]}" if len(next_key) >= 4 else "next_key"
                    logger.warning(
                        f"Groq API call status {status_code} with key {masked_key}: {exc}. "
                        f"Failing over to fallback key {next_masked}."
                    )
                    last_error = exc
                    continue
                raise

        if last_error:
            raise last_error


class GroqChatWrapper:
    def __init__(self, provider: "GroqProvider"):
        self.completions = GroqCompletionsWrapper(provider)


class GroqClientWrapper:
    """Smart Groq SDK client wrapper with automatic multi-key failover."""

    def __init__(self, provider: "GroqProvider"):
        self._provider = provider
        self.chat = GroqChatWrapper(provider)

    def __getattr__(self, name: str) -> Any:
        # Delegate any other attributes (e.g. models, embeddings) to the active raw client
        keys = self._provider.get_available_keys()
        primary_key = keys[0] if keys else None
        if not primary_key:
            raise ValueError("No Groq API keys configured.")
        active_client = self._provider._get_raw_client(primary_key)
        return getattr(active_client, name)


class GroqProvider:
    """Encapsulated Groq LLM client with automatic fallback key support."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
    ):
        settings = get_settings()
        self._explicit_key = api_key is not None
        self.api_key = api_key if self._explicit_key else settings.GROQ_API_KEY
        self.fallback_api_key = settings.GROQ_API_FALLBACK_KEY
        self.model = model or settings.GROQ_MODEL
        self.timeout = timeout or settings.GROQ_TIMEOUT_SECONDS
        self._raw_clients: Dict[str, Any] = {}
        self._wrapper_client: Optional[GroqClientWrapper] = None

    def get_available_keys(self) -> list[str]:
        """Return list of configured Groq API keys in priority order (primary, then fallback)."""
        keys: list[str] = []
        if self._explicit_key:
            if self.api_key and self.api_key.strip() and self.api_key != "your_groq_api_key_here":
                keys.append(self.api_key.strip())
            return keys

        settings = get_settings()
        if not settings.GROQ_API_KEY:
            settings = get_settings(reload=True)
        for k in [settings.GROQ_API_KEY, settings.GROQ_API_FALLBACK_KEY]:
            if k and k.strip() and k != "your_groq_api_key_here" and k not in keys:
                keys.append(k.strip())
        return keys

    @property
    def is_configured(self) -> bool:
        """Check whether at least one valid API key is configured."""
        return len(self.get_available_keys()) > 0

    def _get_raw_client(self, key: str) -> Any:
        """Get or initialize a raw Groq SDK client for a specific API key."""
        if not GROQ_SDK_AVAILABLE:
            raise RuntimeError("Groq Python SDK is not installed.")
        if key not in self._raw_clients:
            self._raw_clients[key] = Groq(api_key=key, timeout=self.timeout)
        return self._raw_clients[key]

    def _get_client(self) -> Any:
        """Return the resilient GroqClientWrapper supporting automatic key failover."""
        if not GROQ_SDK_AVAILABLE:
            raise RuntimeError("Groq Python SDK is not installed.")
        if not self.is_configured:
            raise ValueError("GROQ_API_KEY is not configured or contains placeholder value.")
        if self._wrapper_client is None:
            self._wrapper_client = GroqClientWrapper(self)
        return self._wrapper_client

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

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2,
        response_format: Optional[dict[str, str]] = None,
        max_tokens: Optional[int] = None,
    ) -> Any:
        """Async-compatible chat completion wrapper using asyncio.to_thread."""
        import asyncio
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format:
            kwargs["response_format"] = response_format
        if max_tokens:
            kwargs["max_tokens"] = max_tokens

        res = await asyncio.to_thread(client.chat.completions.create, **kwargs)

        class ChatResult:
            def __init__(self, content: str):
                self.content = content

        choice_text = res.choices[0].message.content if res.choices else ""
        return ChatResult(content=choice_text)


_groq_provider_instance: Optional[GroqProvider] = None


def get_groq_provider() -> GroqProvider:
    """Return the global GroqProvider singleton."""
    global _groq_provider_instance
    if _groq_provider_instance is None:
        _groq_provider_instance = GroqProvider()
    return _groq_provider_instance

