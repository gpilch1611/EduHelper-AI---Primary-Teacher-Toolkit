# groq_client.py – Thin wrapper around the Groq REST API

from __future__ import annotations

import json
import threading
from typing import Callable, Generator
import urllib.request
import urllib.error

from config import GROQ_API_KEY, GROQ_MODEL, GROQ_BASE_URL


class GroqClient:
    """Minimal synchronous + streaming Groq client (no extra dependencies)."""

    def __init__(self) -> None:
        self.api_key = GROQ_API_KEY
        self.model   = GROQ_MODEL
        self.base_url = GROQ_BASE_URL

    # ── Connectivity check ────────────────────────────────────────────────────

    def ping(self) -> bool:
        """Return True if the API key is valid and reachable."""
        try:
            self.complete("Say OK", max_tokens=4)
            return True
        except Exception:
            return False

    # ── Core request helper ───────────────────────────────────────────────────

    def _post(self, payload: dict) -> dict:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())

    # ── Non-streaming completion ──────────────────────────────────────────────

    def complete(self, prompt: str, system: str = "", max_tokens: int = 2048,
                 temperature: float = 0.7) -> str:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model":       self.model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      False,
        }
        result = self._post(payload)
        return result["choices"][0]["message"]["content"]

    # ── Streaming completion ──────────────────────────────────────────────────

    def stream(self, prompt: str, system: str = "",
               max_tokens: int = 2048,
               temperature: float = 0.7) -> Generator[str, None, None]:
        """Yield text chunks as they arrive from the API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model":       self.model,
            "messages":    messages,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "stream":      True,
        }
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data:"):
                    continue
                payload_str = line[5:].strip()
                if payload_str == "[DONE]":
                    break
                chunk = json.loads(payload_str)
                delta = chunk["choices"][0]["delta"]
                if "content" in delta and delta["content"]:
                    yield delta["content"]

    # ── Async helper (runs stream in a thread, posts chunks via callback) ──────

    def stream_async(self, prompt: str, system: str = "",
                     on_chunk: Callable[[str], None] = None,
                     on_done:  Callable[[], None]    = None,
                     on_error: Callable[[str], None] = None,
                     max_tokens: int = 2048,
                     temperature: float = 0.7) -> threading.Thread:
        """Fire-and-forget: returns the daemon thread immediately."""

        def _worker():
            try:
                for chunk in self.stream(prompt, system, max_tokens, temperature):
                    if on_chunk:
                        on_chunk(chunk)
                if on_done:
                    on_done()
            except Exception as exc:
                if on_error:
                    on_error(str(exc))

        t = threading.Thread(target=_worker, daemon=True)
        t.start()
        return t


# Module-level singleton
groq = GroqClient()
