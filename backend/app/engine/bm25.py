"""Okapi BM25 over in-memory chunks. No extra dependencies."""

import math
from collections.abc import Sequence

from app.engine.sentences import iter_sentence_spans
from app.engine.tokenize import tokenize
from app.engine.types import Chunk


class BM25Index:
    """BM25 index for one document's chunks."""

    def __init__(self, chunks: Sequence[Chunk], *, k1: float = 1.5, b: float = 0.75, unit: str = "chunk") -> None:
        if unit not in {"chunk", "sentence"}:
            raise ValueError("unit must be 'chunk' or 'sentence'")
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self.unit = unit
        self._tf: list[dict[str, int]] = []
        self._doc_lens: list[int] = []
        self._df: dict[str, int] = {}
        self._owners: list[int] = []
        for chunk_index, chunk in enumerate(self.chunks):
            pieces = _pieces(chunk.text, unit)
            for text in pieces:
                counts: dict[str, int] = {}
                tokens = tokenize(text)
                for token in tokens:
                    counts[token] = counts.get(token, 0) + 1
                self._tf.append(counts)
                self._doc_lens.append(len(tokens))
                self._owners.append(chunk_index)
                for token in counts:
                    self._df[token] = self._df.get(token, 0) + 1
        self._n = len(self._tf)
        self._avgdl = (sum(self._doc_lens) / self._n) if self._n else 0.0

    def rank(self, query: str) -> list[tuple[int, float]]:
        """Return ``(chunk_index, score)`` for chunks with a positive score.

        Ties break toward the earlier chunk so the ranking is deterministic.
        """

        tokens = tokenize(query)
        if not tokens or self._n == 0 or self._avgdl == 0:
            return []
        scores = [0.0] * self._n
        for token in tokens:
            document_frequency = self._df.get(token, 0)
            if document_frequency == 0:
                continue
            idf = math.log(1.0 + (self._n - document_frequency + 0.5) / (document_frequency + 0.5))
            for index, counts in enumerate(self._tf):
                frequency = counts.get(token, 0)
                if frequency == 0:
                    continue
                denominator = frequency + self.k1 * (1.0 - self.b + self.b * self._doc_lens[index] / self._avgdl)
                scores[index] += idf * (frequency * (self.k1 + 1.0)) / denominator
        if self.unit == "sentence":
            best: dict[int, float] = {}
            for index, score in enumerate(scores):
                if score <= 0.0:
                    continue
                owner = self._owners[index]
                if owner not in best or score > best[owner]:
                    best[owner] = score
            ranked = list(best.items())
        else:
            ranked = [(index, score) for index, score in enumerate(scores) if score > 0.0]
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return ranked


def _pieces(text: str, unit: str) -> list[str]:
    if unit == "chunk":
        return [text]
    sentences = [sentence for _start, _end, sentence in iter_sentence_spans(text)]
    return sentences or [text]
