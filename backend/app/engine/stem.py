"""Light stemmer for clause-marker matching.

The stemmer is deliberately small. It folds plural and a few derivational
endings so ``invoice`` matches ``invoices`` and ``terminate`` matches
``termination``. It is not applied to BM25, so retrieval scores stay on the
same tokenizer as before.
"""


def stem_token(token: str) -> str:
    """Return a lowercase stem. Tokens shorter than five characters are unchanged."""

    word = token.lower()
    if len(word) <= 4:
        return word
    if word.endswith("ation"):
        return word[:-5] + "ate"
    if word.endswith("ing") and len(word) > 6:
        return word[:-3]
    if word.endswith("ied"):
        return word[:-3] + "y"
    if word.endswith("ies"):
        return word[:-3] + "y"
    if word.endswith("es") and word[-3] in {"s", "x", "z"}:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word
