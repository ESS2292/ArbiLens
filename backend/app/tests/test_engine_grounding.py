"""Grounded answers, clause tags, and the deterministic risk rubric."""

import pytest

from app.engine.answer import bind_answer
from app.engine.chunking import chunk_clause_aware
from app.engine.embeddings import FakeEmbeddingProvider, ProviderSettings
from app.engine.errors import ProviderError
from app.engine.extract import extract_clauses
from app.engine.llm import (
    FakeLLMProvider,
    LLMCitation,
    LLMResult,
    OpenAICompatibleLLMProvider,
    Passage,
    default_llm,
)
from app.engine.pipeline import analyze_document, ask_document
from app.engine.risks import evaluate_risk_flags
from app.engine.sentences import iter_sentence_spans
from app.engine.strategy import upgraded_strategy
from app.engine.taxonomy import CLAUSE_MARKERS
from app.engine.types import ClauseView
from app.models.enums import ClauseType as ModelClauseType


def test_decimal_points_do_not_split_sentences() -> None:
    text = "1. Service Levels\nThe monthly uptime percentage promised is 99.9 percent.\n"
    sentences = [sentence for _start, _end, sentence in iter_sentence_spans(text)]
    assert sentences == ["The monthly uptime percentage promised is 99.9 percent."]


def test_extractive_answer_cites_the_exact_sentence() -> None:
    document = (
        "1. Limitation of Liability\n"
        "The aggregate liability of Provider under this agreement is unlimited.\n"
        "2. Payment Terms\n"
        "Invoices are due within thirty days of receipt.\n"
    )
    answer = ask_document(
        document,
        "Which ceiling bounds monetary exposure?",
        upgraded_strategy(),
        embedder=FakeEmbeddingProvider(),
        llm=FakeLLMProvider(),
    )
    assert answer.provider == "fake"
    assert answer.grounded
    assert answer.citations
    citation = answer.citations[0]
    assert document[citation.char_start : citation.char_end] == citation.text
    assert "unlimited" in citation.text


def test_binder_drops_invented_quotes_and_ungrounded_numbers() -> None:
    document = "1. Payment Terms\nInvoices are due within thirty days of receipt.\n"
    passage = Passage("c0", 0, len(document), document, "1. Payment Terms")
    invented = bind_answer(
        document,
        [passage],
        LLMResult("Thirty days.", (LLMCitation("c0", "this quote was not in the passage"),)),
        question="When are invoices due?",
        provider="stub",
        strategy="upgraded",
    )
    assert invented.citations == ()
    assert invented.grounded is False
    numbered = bind_answer(
        document,
        [passage],
        LLMResult(
            "Pay within 15 days.",
            (LLMCitation("c0", "Invoices are due within thirty days of receipt."),),
        ),
        question="When are invoices due?",
        provider="stub",
        strategy="upgraded",
    )
    assert numbered.citations
    assert numbered.grounded is False


def test_openai_reader_parses_json_and_rejects_malformed_choices() -> None:
    class Transport:
        def post_json(
            self,
            url: str,
            payload: dict[str, object],
            headers: dict[str, str],
            timeout: float,
        ) -> dict[str, object]:
            assert url.endswith("/chat/completions")
            assert payload["temperature"] == 0
            content = '{"answer":"Thirty days.","citations":[{"chunk_id":"c0","quote":"thirty"}]}'
            return {"choices": [{"message": {"content": f"```json\n{content}\n```"}}]}

    settings = ProviderSettings(
        llm_provider="openai",
        embedding_provider="fake",
        base_url="https://example.test/v1",
        api_key="test-key",
        llm_model="gpt-test",
        embedding_model="embed-test",
        timeout_seconds=5,
    )
    result = OpenAICompatibleLLMProvider(settings, Transport()).answer(question="When?", passages=[])
    assert result.answer == "Thirty days."
    assert result.citations[0].quote == "thirty"
    with pytest.raises(ProviderError):
        OpenAICompatibleLLMProvider(
            ProviderSettings(
                llm_provider="openai",
                embedding_provider="fake",
                base_url="https://example.test/v1",
                api_key="",
                llm_model="gpt-test",
                embedding_model="embed-test",
                timeout_seconds=5,
            )
        )

    class Broken:
        def post_json(
            self,
            url: str,
            payload: dict[str, object],
            headers: dict[str, str],
            timeout: float,
        ) -> dict[str, object]:
            return {"choices": [{"message": {"content": "not-json"}}]}

    with pytest.raises(ProviderError):
        OpenAICompatibleLLMProvider(settings, Broken()).answer(question="When?", passages=[])


def test_default_llm_rejects_unknown_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARBILENS_LLM_PROVIDER", "mystery")
    with pytest.raises(ProviderError):
        default_llm()


def test_stemmed_markers_match_morphology_and_ignore_assignment_distractors() -> None:
    payment = "1. Payment Terms\nThe buyer shall pay each invoice within nine days.\n"
    payment_types = [clause.clause_type for clause in extract_clauses(chunk_clause_aware(payment, max_chars=1000))]
    assert payment_types == ["payment_terms"]

    distractor = "2. Tools\nThe studio keeps the pictures made for this assignment inside a drawer.\n"
    distractor_types = [
        clause.clause_type for clause in extract_clauses(chunk_clause_aware(distractor, max_chars=1000))
    ]
    assert "assignment" not in distractor_types

    real = "3. Assignment\nNeither party may assign this agreement without written consent.\n"
    real_types = [clause.clause_type for clause in extract_clauses(chunk_clause_aware(real, max_chars=1000))]
    assert "assignment" in real_types


def test_marker_list_covers_the_database_enum_except_general() -> None:
    assert set(CLAUSE_MARKERS) == {item.value for item in ModelClauseType if item is not ModelClauseType.general}
    text = "1. Confidentiality\nEach party shall protect confidential information.\n"
    clauses = extract_clauses(chunk_clause_aware(text, max_chars=1000))
    assert [clause.clause_type for clause in clauses] == ["confidentiality"]
    assert clauses[0].char_start == 0


def test_risk_rubric_matches_the_historical_rules() -> None:
    flags = evaluate_risk_flags(
        [
            ClauseView("limitation_of_liability", "Supplier liability is unlimited and without limitation.", 0.9),
            ClauseView("indemnification", "Customer shall indemnify provider against all claims.", 0.4),
            ClauseView("indemnification", "Client shall indemnify provider.", 0.9),
            ClauseView("termination", "Provider may terminate for convenience at any time.", 0.8),
            ClauseView("dispute_resolution", "Exclusive venue lies in the vendor's courts.", 0.7),
        ]
    )
    by_code = {flag.rule_code: flag for flag in flags}
    assert by_code["uncapped_liability"].severity == "critical"
    assert by_code["uncapped_liability"].score == 95
    assert by_code["one_sided_indemnity"].clause_index == 2
    assert "unilateral_termination" in by_code
    assert "unfavorable_dispute_language" in by_code
    assert "missing_confidentiality" in by_code
    assert "weak_data_protection" in by_code
    balanced = evaluate_risk_flags(
        [
            ClauseView("limitation_of_liability", "Aggregate liability shall not exceed the charges paid."),
            ClauseView("indemnification", "Each party shall indemnify the other party."),
            ClauseView("termination", "Either party may terminate for convenience."),
            ClauseView("confidentiality", "Each party shall protect confidential information."),
            ClauseView("data_protection", "The vendor will maintain reasonable security."),
            ClauseView("dispute_resolution", "The parties will discuss disagreements."),
        ]
    )
    assert balanced == []


def test_analyze_reports_clauses_and_risks_without_a_model() -> None:
    document = "1. Indemnification\nCustomer shall indemnify the provider against third-party claims.\n"
    analysis = analyze_document(document, upgraded_strategy())
    assert any(clause.clause_type == "indemnification" for clause in analysis.clauses)
    assert any(risk.rule_code == "one_sided_indemnity" for risk in analysis.risks)
    assert ModelClauseType.indemnification.value == "indemnification"


def test_empty_question_has_no_citations() -> None:
    answer = FakeLLMProvider().answer(question="Anything?", passages=[])
    assert answer.citations == ()
    assert "No supporting clause" in answer.answer
