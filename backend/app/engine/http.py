"""JSON POST transport for OpenAI-compatible providers. Stdlib only."""

import json
import urllib.error
import urllib.request
from collections.abc import Mapping
from typing import Any, Protocol

from app.engine.errors import ProviderError


class Transport(Protocol):
    """Something that can POST a JSON body and return a JSON object."""

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        """POST ``payload`` and return the decoded JSON object."""
        ...


class UrllibTransport:
    """Production transport. Tests inject a fake instead of using this."""

    def post_json(
        self,
        url: str,
        payload: Mapping[str, Any],
        headers: Mapping[str, str],
        timeout: float,
    ) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=data,
            headers={**dict(headers), "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:300]
            raise ProviderError(f"Provider HTTP {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ProviderError(f"Provider connection failed: {exc.reason}") from exc
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ProviderError("Provider returned non-JSON.") from exc
        if not isinstance(parsed, dict):
            raise ProviderError("Provider JSON was not an object.")
        return parsed
