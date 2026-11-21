"""Decide whether a citation supports a claim, including a paraphrase.

The offline judge is lexical. It is not a trained entailment model. An optional
OpenAI-compatible judge uses the same result shape when a server is configured.
The evaluation gate always uses the offline judge.
"""

import json
import os
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.engine.concepts import CONCEPTS, active_concepts
from app.engine.embeddings import ProviderSettings
from app.engine.errors import ProviderError
from app.engine.http import Transport, UrllibTransport
from app.engine.tokenize import tokenize
from app.engine.types import Citation

_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_UNCAPPED = ("unlimited", "without limitation", "no ceiling", "no cap")
_CAPPED = ("shall not exceed", "not exceed", "capped at", "limited to", "is limited")
_SUPPORT_FLOOR = 0.6


@dataclass(frozen=True)
class FaithfulnessVerdict:
    """Whether the citations support the claim, and why."""

    faithful: bool
    reason: str
    judge: str


class FaithfulnessJudge(Protocol):
    """Scores one claim against the citations that accompany an answer."""

    name: str

    def judge(self, claim: str, citations: Sequence[Citation]) -> FaithfulnessVerdict:
        """Return a verdict. Empty citations are unfaithful."""
        ...


class DeterministicFaithfulnessJudge:
    """Offline judge. A claim is supported only when the citation says the same facts.

    A content word counts as supported when it appears in the citation or when
    it is part of a legal concept that both the claim and the citation trigger.
    Numbers in the claim must appear as digits in the citation. A capped claim
    is rejected when the citation says the exposure is uncapped, and the reverse.
    The judge fails closed: a paraphrase outside the concept list is unfaithful
    even if a person would accept it.
    """

    name = "deterministic"

    def judge(self, claim: str, citations: Sequence[Citation]) -> FaithfulnessVerdict:
        if not citations:
            return FaithfulnessVerdict(False, "no citation", self.name)
        cited = "\n".join(citation.text for citation in citations)
        missing_numbers = set(_NUMBER.findall(claim)) - set(_NUMBER.findall(cited))
        if missing_numbers:
            listed = ", ".join(sorted(missing_numbers))
            return FaithfulnessVerdict(False, f"numbers not in the citation: {listed}", self.name)
        if _polarity_clash(claim, cited):
            return FaithfulnessVerdict(False, "the citation contradicts the claim's cap", self.name)
        shared = active_concepts(claim) & active_concepts(cited)
        if active_concepts(claim) and not shared:
            return FaithfulnessVerdict(False, "the citation does not discuss the claim's topic", self.name)
        coverage = _token_coverage(claim, cited, shared)
        if coverage < _SUPPORT_FLOOR:
            return FaithfulnessVerdict(False, f"only {coverage:.0%} of the claim is in the citation", self.name)
        return FaithfulnessVerdict(True, "citation covers the claim", self.name)


class OpenAICompatibleFaithfulnessJudge:
    """Ask an OpenAI-compatible chat endpoint whether the quotes support the claim."""

    name = "openai"

    def __init__(self, settings: ProviderSettings, transport: Transport | None = None) -> None:
        if not settings.api_key:
            raise ProviderError("OPENAI_API_KEY is required when ARBILENS_JUDGE_PROVIDER=openai.")
        self._settings = settings
        self._transport = transport if transport is not None else UrllibTransport()

    def judge(self, claim: str, citations: Sequence[Citation]) -> FaithfulnessVerdict:
        if not citations:
            return FaithfulnessVerdict(False, "no citation", self.name)
        quotes = "\n".join(f"- {citation.text}" for citation in citations)
        payload = self._transport.post_json(
            f"{self._settings.base_url}/chat/completions",
            {
                "model": self._settings.llm_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You judge whether contract quotes support a claim. "
                            "Return JSON with keys faithful (boolean) and reason (string). "
                            "Faithful means every factual part of the claim is stated in the quotes. "
                            "A paraphrase can be faithful. A quote about a different obligation is not."
                        ),
                    },
                    {"role": "user", "content": f"Claim:\n{claim}\n\nQuotes:\n{quotes}"},
                ],
            },
            {"Authorization": f"Bearer {self._settings.api_key}"},
            self._settings.timeout_seconds,
        )
        parsed = _parse_verdict(payload)
        return FaithfulnessVerdict(parsed[0], parsed[1], self.name)


def judge_for_settings(settings: ProviderSettings | None = None) -> FaithfulnessJudge:
    """Return the configured judge. The default is the offline deterministic one.

    ``ARBILENS_JUDGE_PROVIDER`` is separate from the reader and the embedder so
    an API key in the environment cannot change the evaluation gate.
    """

    from app.engine.embeddings import load_provider_settings

    resolved = settings if settings is not None else load_provider_settings()
    selected = os.environ.get("ARBILENS_JUDGE_PROVIDER", "deterministic").strip().lower() or "deterministic"
    if selected == "deterministic":
        return DeterministicFaithfulnessJudge()
    if selected == "openai":
        return OpenAICompatibleFaithfulnessJudge(resolved)
    raise ProviderError(f"Unknown ARBILENS_JUDGE_PROVIDER {selected!r}. Use 'deterministic' or 'openai'.")


def _polarity_clash(claim: str, cited: str) -> bool:
    claim_uncapped = _has_any(claim, _UNCAPPED)
    claim_capped = _has_any(claim, _CAPPED)
    cited_uncapped = _has_any(cited, _UNCAPPED)
    cited_capped = _has_any(cited, _CAPPED)
    if claim_uncapped and cited_capped and not cited_uncapped:
        return True
    if claim_capped and cited_uncapped and not cited_capped:
        return True
    return False


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def _token_coverage(claim: str, cited: str, shared_concepts: set[str]) -> float:
    claim_tokens = tokenize(claim)
    if not claim_tokens:
        return 0.0
    cited_tokens = set(tokenize(cited))
    supported = sum(1 for token in claim_tokens if token in cited_tokens or _in_shared_concept(token, shared_concepts))
    return supported / len(claim_tokens)


def _in_shared_concept(token: str, shared_concepts: set[str]) -> bool:
    for concept in shared_concepts:
        for phrase in CONCEPTS[concept]:
            if token in phrase.split():
                return True
    return False


def _parse_verdict(payload: dict[str, object]) -> tuple[bool, str]:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise ProviderError("Judge response did not contain choices.")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ProviderError("Judge response did not contain message content.")
    try:
        parsed = json.loads(message["content"])
    except json.JSONDecodeError as exc:
        raise ProviderError("Judge content was not valid JSON.") from exc
    if not isinstance(parsed, dict) or not isinstance(parsed.get("faithful"), bool):
        raise ProviderError("Judge JSON is missing a boolean faithful field.")
    reason = parsed.get("reason", "")
    if not isinstance(reason, str) or not reason.strip():
        raise ProviderError("Judge JSON is missing a reason.")
    return parsed["faithful"], reason.strip()
