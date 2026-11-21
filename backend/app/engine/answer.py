"""Bind model quotes to exact character offsets and check they support the answer."""

import re
from collections.abc import Sequence

from app.engine.llm import LLMResult, Passage
from app.engine.types import Citation, GroundedAnswer

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def bind_answer(
    document: str,
    passages: Sequence[Passage],
    raw: LLMResult,
    *,
    question: str,
    provider: str,
    strategy: str,
) -> GroundedAnswer:
    """Drop quotes that are not exact slices, then decide whether the answer is grounded.

    Grounded means every surviving citation is an exact document slice, the answer
    is lexically supported by those slices, and every number in the answer appears
    in a citation. It does not mean the answer is the one a gold label expects.
    That check lives in the evaluation harness.
    """

    by_id = {passage.chunk_id: passage for passage in passages}
    citations: list[Citation] = []
    for item in raw.citations:
        passage = by_id.get(item.chunk_id)
        if passage is None or not item.quote:
            continue
        local = passage.text.find(item.quote)
        if local < 0:
            continue
        start = passage.char_start + local
        end = start + len(item.quote)
        if document[start:end] != item.quote:
            continue
        citations.append(
            Citation(
                chunk_id=passage.chunk_id,
                char_start=start,
                char_end=end,
                text=item.quote,
                section_title=passage.section_title,
            )
        )
    grounded = bool(citations) and _answer_supported(raw.answer, citations) and _numbers_grounded(raw.answer, citations)
    return GroundedAnswer(
        question=question,
        answer=raw.answer,
        citations=tuple(citations),
        grounded=grounded,
        provider=provider,
        strategy=strategy,
    )


def citation_offsets_match(document: str, citations: Sequence[Citation]) -> bool:
    """True when every citation text is exactly the document slice it names."""

    return all(document[citation.char_start : citation.char_end] == citation.text for citation in citations)


def _answer_supported(answer: str, citations: Sequence[Citation]) -> bool:
    blob = " ".join(citation.text for citation in citations)
    if _normalize(answer) in _normalize(blob):
        return True
    answer_tokens = _content_tokens(answer)
    if not answer_tokens:
        return False
    blob_tokens = set(_content_tokens(blob))
    covered = sum(1 for token in answer_tokens if token in blob_tokens)
    return covered / len(answer_tokens) >= 0.8


def _numbers_grounded(answer: str, citations: Sequence[Citation]) -> bool:
    cited = " ".join(citation.text for citation in citations)
    return set(_NUMBER.findall(answer)) <= set(_NUMBER.findall(cited))


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _content_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2]
