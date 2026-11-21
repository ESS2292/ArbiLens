"""Chunk boundary tests. Offsets are exact slices of the source string."""

import pytest

from app.engine.chunking import (
    chunk_clause_aware,
    chunk_document,
    chunk_fixed_window,
    is_heading,
    section_break_title,
)
from app.engine.strategy import baseline_strategy, upgraded_strategy


def test_heading_detector_accepts_numbered_sections_and_rejects_sentences() -> None:
    assert is_heading("2. Payment Terms")
    assert is_heading("Section 4. Liability")
    assert not is_heading("Invoices are due within thirty days of receipt.")
    assert not is_heading("1. " + "word " * 20)


def test_heading_detector_accepts_article_roman_and_emdash() -> None:
    assert is_heading("Article IV — Compensation")
    assert is_heading("Article II")
    assert is_heading("ARTICLE V — FEES")
    assert section_break_title("Article VII") == "Article VII"
    assert not is_heading("Article IV — Compensation is described in the order form and continues here.")


def test_heading_detector_accepts_lettered_subsections() -> None:
    assert is_heading("(a) Fees")
    assert is_heading("(b) Secrecy")
    assert not is_heading("(a) Cinder Bakery shall pay invoices within ten days.")


def test_heading_detector_accepts_all_caps_standalone_lines() -> None:
    assert is_heading("PAYMENT TERMS")
    assert is_heading("LIMITATION OF LIABILITY")
    assert not is_heading("PAYMENT TERMS APPLY TO EVERY INVOICE SENT AFTER THE ORDER.")
    assert not is_heading("OK")


def test_heading_detector_accepts_unnumbered_title_case() -> None:
    assert is_heading("Ownership Of New Labels")
    assert is_heading("Confidentiality")
    assert not is_heading("Once the bill is paid the labels belong to the buyer")
    assert not is_heading("Of")


def test_blank_line_marks_an_unnumbered_sentence_case_heading() -> None:
    text = (
        "1. Grant\n"
        "The grant does not decide ownership.\n"
        "\n"
        "Ownership of new drawings\n"
        "Once the client has paid, the drawings belong to the client.\n"
    )
    chunks = chunk_clause_aware(text, max_chars=4000)
    assert [chunk.section_title for chunk in chunks] == ["1. Grant", "Ownership of new drawings"]
    assert "belong to the client" in chunks[1].text
    assert not is_heading("Ownership of new drawings")


def test_inline_label_starts_a_section_without_hiding_the_sentence() -> None:
    line = "Payment terms: Linen Shop shall pay invoices within twelve days."
    assert not is_heading(line)
    assert section_break_title(line) == "Payment terms"
    text = line + "\nConfidentiality: each party shall keep confidential information secret.\n"
    chunks = chunk_clause_aware(text, max_chars=4000)
    assert [chunk.section_title for chunk in chunks] == ["Payment terms", "Confidentiality"]
    assert "twelve days" in chunks[0].text
    assert "".join(chunk.text for chunk in chunks) == text


def test_oversized_section_splits_on_sentence_boundaries() -> None:
    sentence = "The supplier performs one discrete task and then stops."
    body = " ".join([sentence] * 6)
    text = f"1. Services\n{body}\n2. Payment Terms\nInvoices are due on receipt.\n"
    chunks = chunk_clause_aware(text, max_chars=80)
    assert "".join(chunk.text for chunk in chunks) == text
    services = [chunk for chunk in chunks if chunk.section_title == "1. Services"]
    assert len(services) > 1
    body_chunks = [chunk.text for chunk in services if sentence[:20] in chunk.text]
    assert body_chunks
    assert all(sentence in chunk_text for chunk_text in body_chunks)
    payment = next(chunk for chunk in chunks if chunk.section_title == "2. Payment Terms")
    assert "Invoices are due on receipt." in payment.text


def test_clause_aware_chunks_partition_the_document() -> None:
    text = (
        "Preamble line.\n"
        "1. Services\n"
        "The supplier performs the work.\n"
        "2. Payment Terms\n"
        "Invoices are due within thirty days.\n"
    )
    chunks = chunk_clause_aware(text, max_chars=4000)
    assert "".join(chunk.text for chunk in chunks) == text
    assert [chunk.section_title for chunk in chunks] == [None, "1. Services", "2. Payment Terms"]
    for chunk in chunks:
        assert text[chunk.char_start : chunk.char_end] == chunk.text


def test_fixed_windows_ignore_clause_boundaries() -> None:
    sentence = "Customer shall indemnify the provider against third-party claims arising here."
    text = "1. Indemnification\n" + ("Background sentence.\n" * 8) + sentence + "\n"
    chunks = chunk_fixed_window(text, size=80, overlap=0)
    assert "".join(chunk.text for chunk in chunks) == text
    assert all(len(chunk.text) <= 80 for chunk in chunks)
    assert not any(sentence in chunk.text for chunk in chunks)


def test_overlap_advances_and_keeps_exact_slices() -> None:
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunk_fixed_window(text, size=10, overlap=3)
    assert chunks[0].text == text[0:10]
    assert chunks[1].char_start == 7
    assert text[chunks[1].char_start : chunks[1].char_end] == chunks[1].text
    assert chunks[-1].char_end == len(text)


def test_long_clause_splits_inside_the_section_only() -> None:
    body = "\n\n".join(f"Paragraph {index} stays inside the clause." for index in range(20))
    text = f"1. Services\n{body}\n2. Payment Terms\nInvoices are due on receipt.\n"
    chunks = chunk_clause_aware(text, max_chars=120)
    assert "".join(chunk.text for chunk in chunks) == text
    payment = next(chunk for chunk in chunks if chunk.section_title == "2. Payment Terms")
    assert "Invoices are due on receipt." in payment.text
    assert "Paragraph 0" not in payment.text
    assert sum(1 for chunk in chunks if chunk.section_title == "1. Services") > 1


def test_empty_text_and_invalid_sizes() -> None:
    assert chunk_fixed_window("", size=10, overlap=0) == []
    assert chunk_clause_aware("", max_chars=10) == []
    with pytest.raises(ValueError):
        chunk_fixed_window("abc", size=0, overlap=0)
    with pytest.raises(ValueError):
        chunk_fixed_window("abc", size=4, overlap=4)
    with pytest.raises(ValueError):
        chunk_clause_aware("abc", max_chars=0)


def test_strategy_presets_select_the_named_chunker() -> None:
    text = "1. Services\nThe supplier performs the work described in the order.\n"
    baseline = chunk_document(text, baseline_strategy())
    upgraded = chunk_document(text, upgraded_strategy())
    assert baseline[0].strategy == "fixed_window"
    assert upgraded[0].strategy == "clause_aware"
    assert upgraded[0].section_title == "1. Services"


def test_strategy_rejects_unknown_modes() -> None:
    from app.engine.strategy import RetrievalStrategy

    with pytest.raises(ValueError):
        RetrievalStrategy(name="bad", chunking="tokens")
    with pytest.raises(ValueError):
        RetrievalStrategy(name="bad", chunking="fixed_window", rrf_k=0)
