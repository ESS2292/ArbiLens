"""Tokenizer shared by BM25, the lexical reranker, and the offline embedder."""

import re

_TOKEN = re.compile(r"[a-z0-9]+")

# Function words only. Legal terms such as "liability" and "terminate" stay indexed.
STOPWORDS = frozenset(
    {
        "a",
        "about",
        "after",
        "all",
        "also",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "before",
        "between",
        "by",
        "do",
        "does",
        "each",
        "for",
        "from",
        "has",
        "have",
        "how",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "many",
        "may",
        "must",
        "of",
        "on",
        "only",
        "or",
        "other",
        "shall",
        "such",
        "than",
        "that",
        "these",
        "those",
        "the",
        "their",
        "them",
        "then",
        "there",
        "they",
        "this",
        "to",
        "under",
        "what",
        "when",
        "where",
        "will",
        "which",
        "who",
        "with",
    }
)


def tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens with stopwords removed."""

    return [token for token in _TOKEN.findall(text.lower()) if token not in STOPWORDS and len(token) > 1]
