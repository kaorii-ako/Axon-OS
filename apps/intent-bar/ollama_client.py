"""Ollama HTTP client for Intent Bar."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import httpx

OLLAMA_BASE_URL: str = "http://localhost:11434"
DEFAULT_MODEL: str = "llama3.2:3b"

_ERROR_NOT_RUNNING: str = "[error] Ollama is not running."


class OllamaClient:
    """Thin synchronous wrapper around the Ollama REST API."""

    def __init__(
        self,
        base_url: str = OLLAMA_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # ------------------------------------------------------------------
    # Health / discovery
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True when the Ollama daemon is reachable."""
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    def list_models(self) -> list[str]:
        """Return the names of locally available models."""
        try:
            response = self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return [m["name"] for m in data.get("models", [])]
        except (httpx.ConnectError, httpx.TimeoutException):
            return []
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Generate (single-turn completion)
    # ------------------------------------------------------------------

    def generate(self, prompt: str, system: str = "") -> str:
        """Return a complete response for *prompt* (non-streaming)."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            response = self._client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except (httpx.ConnectError, httpx.TimeoutException):
            return _ERROR_NOT_RUNNING
        except Exception as exc:
            return f"[error] {exc}"

    def generate_stream(self, prompt: str, system: str = "") -> Iterator[str]:
        """Yield response tokens for *prompt* one by one (streaming)."""
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk: dict[str, Any] = json.loads(line)
                    token: str = chunk.get("response", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
        except (httpx.ConnectError, httpx.TimeoutException):
            yield _ERROR_NOT_RUNNING

    # ------------------------------------------------------------------
    # Chat (multi-turn)
    # ------------------------------------------------------------------

    def chat(self, messages: list[dict[str, Any]], system: str = "") -> str:
        """Return a complete assistant reply for *messages* (non-streaming)."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if system:
            payload["system"] = system

        try:
            response = self._client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except (httpx.ConnectError, httpx.TimeoutException):
            return _ERROR_NOT_RUNNING
        except Exception as exc:
            return f"[error] {exc}"

    def chat_stream(
        self, messages: list[dict[str, Any]], system: str = ""
    ) -> Iterator[str]:
        """Yield assistant reply tokens for *messages* one by one (streaming)."""
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
        }
        if system:
            payload["system"] = system

        try:
            with self._client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json=payload,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    chunk: dict[str, Any] = json.loads(line)
                    token: str = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done", False):
                        break
        except (httpx.ConnectError, httpx.TimeoutException):
            yield _ERROR_NOT_RUNNING

    # ------------------------------------------------------------------
    # Resource management
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> "OllamaClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
