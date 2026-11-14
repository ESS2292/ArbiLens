"""Okapi BM25 over in-memory chunks. No extra dependencies."""

import math
from collections.abc import Sequence

from app.engine.tokenize import tokenize
from app.engine.types import Chunk


class BM25Index:
    """BM25 index for one document's chunks."""

    def __init__(self, chunks: Sequence[Chunk], *, k1: float = 1.5, b: float = 0.75) -> None:
        self.chunks = list(chunks)
        self.k1 = k1
        self.b = b
        self._tf: list[dict[str, int]] = []
        self._doc_lens: list[int] = []
        self._df: dict[str, int] = {}
        for chunk in self.chunks:
            counts: dict[str, int] = {}
            tokens = tokenize(chunk.text)
            for token in tokens:
                counts[token] = counts.get(token, 0) + 1
            self._tf.append(counts)
            self._doc_lens.append(len(tokens))
            for token in counts:
                self._df[token] = self._df.get(token, 0) + 1
        self._n = len(self.chunks)
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
        ranked = [(index, score) for index, score in enumerate(scores) if score > 0.0]
        ranked.sort(key=lambda item: (-item[1], item[0]))
        return ranked
