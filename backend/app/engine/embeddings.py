"""Embedding providers.

``FakeEmbeddingProvider`` hashes tokens and turns a fixed legal-concept list
into extra dimensions. It is deterministic and needs no model download.
``OpenAICompatibleEmbeddingProvider`` calls ``POST {base}/embeddings`` on any
OpenAI-compatible endpoint.
"""

import hashlib
import math
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol

from app.engine.concepts import CONCEPT_NAMES, active_concepts
from app.engine.errors import ProviderError
from app.engine.http import Transport, UrllibTransport
from app.engine.tokenize import tokenize

HASH_DIM = 128
CONCEPT_WEIGHT = 5.0


def embed_text(text: str) -> list[float]:
    """Deterministic unit vector for ``text``."""

    vector = [0.0] * (HASH_DIM + len(CONCEPT_NAMES))
    tokens = tokenize(text)
    for token in tokens:
        _accumulate(vector, token)
    for left, right in zip(tokens, tokens[1:], strict=False):
        _accumulate(vector, f"{left}_{right}")
    active = active_concepts(text)
    for index, name in enumerate(CONCEPT_NAMES):
        if name in active:
            vector[HASH_DIM + index] = CONCEPT_WEIGHT
    return _l2_normalize(vector)


def cosine(left: Sequence[float], right: Sequence[float]) -> float:
    """Cosine similarity. Both vectors are expected to be the same length."""

    if len(left) != len(right) or not left:
        raise ValueError("vectors must be non-empty and the same length")
    return sum(a * b for a, b in zip(left, right, strict=True))


class EmbeddingProvider(Protocol):
    """Embeds a batch of strings. Order of the result matches ``texts``."""

    name: str

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one vector per input string."""
        ...


class FakeEmbeddingProvider:
    """Offline embedder used by tests, the eval gate, and the default CLI."""

    name = "fake"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [embed_text(text) for text in texts]


@dataclass(frozen=True)
class ProviderSettings:
    """Environment-derived settings for OpenAI-compatible providers."""

    llm_provider: str
    embedding_provider: str
    base_url: str
    api_key: str
    llm_model: str
    embedding_model: str
    timeout_seconds: float


def load_provider_settings(environ: Mapping[str, str] | None = None) -> ProviderSettings:
    """Read provider settings. Defaults keep the process offline."""

    env = os.environ if environ is None else environ
    llm_provider = env.get("ARBILENS_LLM_PROVIDER", "fake").strip().lower() or "fake"
    embedding_provider = env.get("ARBILENS_EMBEDDING_PROVIDER", "fake").strip().lower() or "fake"
    base_url = (
        env.get("ARBILENS_OPENAI_BASE_URL") or env.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    ).rstrip("/")
    timeout_raw = env.get("ARBILENS_LLM_TIMEOUT_SECONDS", "30")
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise ProviderError("ARBILENS_LLM_TIMEOUT_SECONDS must be a number.") from exc
    if timeout_seconds <= 0:
        raise ProviderError("ARBILENS_LLM_TIMEOUT_SECONDS must be positive.")
    return ProviderSettings(
        llm_provider=llm_provider,
        embedding_provider=embedding_provider,
        base_url=base_url,
        api_key=env.get("OPENAI_API_KEY", ""),
        llm_model=env.get("ARBILENS_LLM_MODEL") or env.get("OPENAI_MODEL") or "gpt-4.1-mini",
        embedding_model=env.get("ARBILENS_EMBEDDING_MODEL", "text-embedding-3-small"),
        timeout_seconds=timeout_seconds,
    )


class OpenAICompatibleEmbeddingProvider:
    """Client for ``POST /embeddings`` on an OpenAI-compatible server."""

    name = "openai"

    def __init__(
        self,
        settings: ProviderSettings,
        transport: Transport | None = None,
    ) -> None:
        if not settings.api_key:
            raise ProviderError("OPENAI_API_KEY is required when ARBILENS_EMBEDDING_PROVIDER=openai.")
        self._settings = settings
        self._transport = transport if transport is not None else UrllibTransport()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        payload = self._transport.post_json(
            f"{self._settings.base_url}/embeddings",
            {"model": self._settings.embedding_model, "input": list(texts)},
            {"Authorization": f"Bearer {self._settings.api_key}"},
            self._settings.timeout_seconds,
        )
        rows = payload.get("data")
        if not isinstance(rows, list) or len(rows) != len(texts):
            raise ProviderError("Embedding response did not contain one vector per input.")
        ordered = sorted(rows, key=_embedding_index)
        vectors: list[list[float]] = []
        for row in ordered:
            if not isinstance(row, dict):
                raise ProviderError("Embedding row was not an object.")
            vector = row.get("embedding")
            if not isinstance(vector, list) or not vector or not all(isinstance(item, int | float) for item in vector):
                raise ProviderError("Embedding row did not contain a numeric vector.")
            vectors.append([float(item) for item in vector])
        return vectors


def default_embedder(settings: ProviderSettings | None = None) -> EmbeddingProvider:
    """Build the embedder selected by the environment."""

    resolved = settings if settings is not None else load_provider_settings()
    if resolved.embedding_provider == "fake":
        return FakeEmbeddingProvider()
    if resolved.embedding_provider == "openai":
        return OpenAICompatibleEmbeddingProvider(resolved)
    raise ProviderError(f"Unknown ARBILENS_EMBEDDING_PROVIDER {resolved.embedding_provider!r}. Use 'fake' or 'openai'.")


def _accumulate(vector: list[float], feature: str) -> None:
    digest = hashlib.sha256(feature.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % HASH_DIM
    sign = 1.0 if digest[4] % 2 == 0 else -1.0
    vector[bucket] += sign


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0.0:
        return vector
    return [value / norm for value in vector]


def _embedding_index(row: Any) -> int:
    if not isinstance(row, dict) or not isinstance(row.get("index"), int):
        raise ProviderError("Embedding row is missing an integer index.")
    return int(row["index"])
