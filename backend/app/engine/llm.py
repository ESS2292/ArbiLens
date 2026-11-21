"""LLM providers that answer from retrieved passages and quote them."""

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.engine.concepts import support_score
from app.engine.embeddings import ProviderSettings, load_provider_settings
from app.engine.errors import ProviderError
from app.engine.http import Transport, UrllibTransport
from app.engine.sentences import iter_sentence_spans

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)


@dataclass(frozen=True)
class Passage:
    """A retrieved chunk handed to the reader model."""

    chunk_id: str
    char_start: int
    char_end: int
    text: str
    section_title: str | None


@dataclass(frozen=True)
class LLMCitation:
    """A quote the model claims is an exact substring of a passage."""

    chunk_id: str
    quote: str


@dataclass(frozen=True)
class LLMResult:
    """Unverified model output. The binder checks quotes before they are shown."""

    answer: str
    citations: tuple[LLMCitation, ...]


class LLMProvider(Protocol):
    """Answers a question using only the supplied passages."""

    name: str

    def answer(self, *, question: str, passages: Sequence[Passage]) -> LLMResult:
        """Return an answer and the quotes it relies on."""
        ...


class FakeLLMProvider:
    """Extractive reader. The answer sentence is copied from a passage."""

    name = "fake"

    def answer(self, *, question: str, passages: Sequence[Passage]) -> LLMResult:
        if not passages:
            return LLMResult("No supporting clause was retrieved for this question.", ())
        best: tuple[float, int, Passage, str] | None = None
        for passage_index, passage in enumerate(passages):
            for _start, _end, sentence in iter_sentence_spans(passage.text):
                score = support_score(question, sentence)
                if best is None or score > best[0]:
                    best = (score, passage_index, passage, sentence)
        if best is None or best[0] <= 0.0:
            fallback = _first_sentence(passages[0])
            return LLMResult(fallback, (LLMCitation(passages[0].chunk_id, fallback),))
        _score, _index, passage, sentence = best
        return LLMResult(sentence, (LLMCitation(passage.chunk_id, sentence),))


class OpenAICompatibleLLMProvider:
    """Chat-completions client. The endpoint must accept JSON-object responses."""

    name = "openai"

    def __init__(self, settings: ProviderSettings, transport: Transport | None = None) -> None:
        if not settings.api_key:
            raise ProviderError("OPENAI_API_KEY is required when ARBILENS_LLM_PROVIDER=openai.")
        self._settings = settings
        self._transport = transport if transport is not None else UrllibTransport()

    def answer(self, *, question: str, passages: Sequence[Passage]) -> LLMResult:
        payload = self._transport.post_json(
            f"{self._settings.base_url}/chat/completions",
            {
                "model": self._settings.llm_model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": _render_prompt(question, passages)},
                ],
            },
            {"Authorization": f"Bearer {self._settings.api_key}"},
            self._settings.timeout_seconds,
        )
        return _parse_chat_payload(payload)


def default_llm(settings: ProviderSettings | None = None) -> LLMProvider:
    """Build the reader selected by the environment. The default is offline."""

    resolved = settings if settings is not None else load_provider_settings()
    if resolved.llm_provider == "fake":
        return FakeLLMProvider()
    if resolved.llm_provider == "openai":
        return OpenAICompatibleLLMProvider(resolved)
    raise ProviderError(f"Unknown ARBILENS_LLM_PROVIDER {resolved.llm_provider!r}. Use 'fake' or 'openai'.")


_SYSTEM_PROMPT = (
    "You answer questions about a contract using only the passages provided. "
    "Return a JSON object with keys 'answer' and 'citations'. "
    "Each citation has 'chunk_id' and 'quote'. "
    "Every quote must be an exact substring of one passage. "
    "Do not invent amounts, dates, or party names that are not in a quote. "
    "If the passages do not support an answer, set answer to "
    "'The retrieved clauses do not support an answer.' and citations to []."
)


def _render_prompt(question: str, passages: Sequence[Passage]) -> str:
    blocks = [f"Question:\n{question}", "Passages:"]
    for passage in passages:
        title = passage.section_title or "(no heading)"
        blocks.append(
            "\n".join(
                [
                    "---",
                    f"chunk_id: {passage.chunk_id}",
                    f"section: {title}",
                    f"char_start: {passage.char_start}",
                    f"char_end: {passage.char_end}",
                    passage.text,
                ]
            )
        )
    return "\n".join(blocks)


def _parse_chat_payload(payload: dict[str, object]) -> LLMResult:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ProviderError("Chat response did not contain choices.")
    first = choices[0]
    if not isinstance(first, dict):
        raise ProviderError("Chat choice was not an object.")
    message = first.get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise ProviderError("Chat choice did not contain message content.")
    parsed = _parse_json_object(message["content"])
    answer = parsed.get("answer")
    raw_citations = parsed.get("citations", [])
    if not isinstance(answer, str) or not answer.strip():
        raise ProviderError("Model JSON is missing a non-empty answer.")
    if not isinstance(raw_citations, list):
        raise ProviderError("Model JSON citations must be a list.")
    citations: list[LLMCitation] = []
    for item in raw_citations:
        if not isinstance(item, dict):
            raise ProviderError("A citation was not an object.")
        chunk_id = item.get("chunk_id")
        quote = item.get("quote")
        if not isinstance(chunk_id, str) or not isinstance(quote, str) or not quote.strip():
            raise ProviderError("A citation is missing chunk_id or quote.")
        citations.append(LLMCitation(chunk_id, quote))
    return LLMResult(answer.strip(), tuple(citations))


def _parse_json_object(content: str) -> dict[str, object]:
    text = _FENCE_RE.sub("", content.strip())
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError("Model content was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("Model JSON was not an object.")
    return parsed


def _first_sentence(passage: Passage) -> str:
    sentences = iter_sentence_spans(passage.text)
    if sentences:
        return sentences[0][2]
    stripped = passage.text.strip()
    return stripped or passage.text
