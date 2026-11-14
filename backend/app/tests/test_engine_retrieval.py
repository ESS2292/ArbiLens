"""BM25, offline embeddings, fusion, and the optional reranker."""

import pytest

from app.engine.bm25 import BM25Index
from app.engine.chunking import chunk_clause_aware
from app.engine.embeddings import (
    FakeEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    ProviderSettings,
    cosine,
    default_embedder,
    load_provider_settings,
)
from app.engine.errors import ProviderError
from app.engine.fusion import reciprocal_rank_fusion
from app.engine.http import UrllibTransport
from app.engine.rerank import LexicalReranker
from app.engine.retrieve import retrieve
from app.engine.strategy import RetrievalStrategy, baseline_strategy, upgraded_strategy
from app.engine.types import Chunk, Hit


def _chunk(index: int, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"c{index}",
        text=text,
        char_start=0,
        char_end=len(text),
        section_title=None,
        strategy="test",
    )


def test_bm25_ranks_the_chunk_that_contains_the_query_terms() -> None:
    chunks = [
        _chunk(0, "Invoices are due within thirty days of receipt."),
        _chunk(1, "The aggregate liability of Provider under this agreement is unlimited."),
    ]
    ranked = BM25Index(chunks).rank("thirty days")
    assert ranked[0][0] == 0
    assert BM25Index(chunks).rank("") == []
    assert BM25Index([]).rank("days") == []


def test_reciprocal_rank_fusion_matches_the_formula() -> None:
    fused = reciprocal_rank_fusion([["a", "b"], ["b"]], k=60)
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)
    assert reciprocal_rank_fusion([[], []]) == {}
    with pytest.raises(ValueError):
        reciprocal_rank_fusion([["a"]], k=0)


def test_fake_embedder_maps_synonyms_onto_the_same_concept() -> None:
    embedder = FakeEmbeddingProvider()
    liability, synonym, payment = embedder.embed(
        [
            "Limitation of Liability. The aggregate liability is stated in this section.",
            "Which ceiling bounds monetary exposure?",
            "Invoices are due within thirty days of receipt.",
        ]
    )
    assert cosine(synonym, liability) > cosine(synonym, payment)


def test_hybrid_retrieval_finds_a_synonym_that_bm25_misses() -> None:
    text = (
        "1. Payment Terms\nInvoices are due within thirty days of receipt.\n"
        "2. Limitation of Liability\nThe aggregate liability of Provider is stated here.\n"
    )
    chunks = chunk_clause_aware(text, max_chars=4000)
    question = "Which ceiling bounds monetary exposure?"
    baseline = retrieve(chunks, question, baseline_strategy())
    upgraded = retrieve(chunks, question, upgraded_strategy(), embedder=FakeEmbeddingProvider())
    assert all("aggregate liability" not in hit.chunk.text for hit in baseline)
    assert "aggregate liability" in upgraded[0].chunk.text


def test_lexical_reranker_breaks_a_near_tie_and_preserves_a_clear_lead() -> None:
    weak = _chunk(0, "Invoices are due within thirty days of receipt.")
    strong = _chunk(1, "The aggregate liability of Provider is the operative promise.")
    reranker = LexicalReranker()
    flipped = reranker.rerank(
        "Which ceiling bounds monetary exposure?",
        [Hit(chunk=weak, score=0.0200), Hit(chunk=strong, score=0.0194)],
    )
    assert flipped[0].chunk.chunk_id == "c1"
    assert flipped[0].rerank_score is not None
    held = reranker.rerank(
        "Which ceiling bounds monetary exposure?",
        [Hit(chunk=weak, score=0.030), Hit(chunk=strong, score=0.010)],
    )
    assert held[0].chunk.chunk_id == "c0"


def test_retrieve_rejects_a_missing_embedder_and_blank_queries() -> None:
    chunks = [_chunk(0, "Invoices are due within thirty days.")]
    strategy = RetrievalStrategy(name="emb", chunking="fixed_window", use_embeddings=True, use_bm25=False)
    with pytest.raises(ValueError):
        retrieve(chunks, "invoice", strategy)
    assert retrieve(chunks, "   ", baseline_strategy()) == []


class _RecordingTransport:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.urls: list[str] = []

    def post_json(
        self,
        url: str,
        payload: dict[str, object],
        headers: dict[str, str],
        timeout: float,
    ) -> dict[str, object]:
        self.urls.append(url)
        assert headers["Authorization"] == "Bearer test-key"
        assert timeout == 5
        assert payload["input"] == ["alpha"]
        return self.payload


def _settings() -> ProviderSettings:
    return ProviderSettings(
        llm_provider="openai",
        embedding_provider="openai",
        base_url="https://example.test/v1",
        api_key="test-key",
        llm_model="gpt-test",
        embedding_model="embed-test",
        timeout_seconds=5,
    )


def test_openai_embedder_sorts_rows_and_rejects_a_bad_payload() -> None:
    transport = _RecordingTransport(
        {"data": [{"index": 0, "embedding": [0.25, 0.5]}]},
    )
    provider = OpenAICompatibleEmbeddingProvider(_settings(), transport)
    assert provider.embed(["alpha"]) == [[0.25, 0.5]]
    assert transport.urls == ["https://example.test/v1/embeddings"]
    assert provider.embed([]) == []
    with pytest.raises(ProviderError):
        OpenAICompatibleEmbeddingProvider(
            ProviderSettings(
                llm_provider="openai",
                embedding_provider="openai",
                base_url="https://example.test/v1",
                api_key="",
                llm_model="gpt-test",
                embedding_model="embed-test",
                timeout_seconds=5,
            )
        )
    broken = _RecordingTransport({"data": []})
    with pytest.raises(ProviderError):
        OpenAICompatibleEmbeddingProvider(_settings(), broken).embed(["alpha"])


def test_provider_settings_default_to_offline_and_reject_bad_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARBILENS_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("ARBILENS_EMBEDDING_PROVIDER", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    settings = load_provider_settings()
    assert settings.llm_provider == "fake"
    assert settings.embedding_provider == "fake"
    assert default_embedder(settings).name == "fake"
    monkeypatch.setenv("ARBILENS_EMBEDDING_PROVIDER", "other")
    with pytest.raises(ProviderError):
        default_embedder()
    monkeypatch.setenv("ARBILENS_EMBEDDING_PROVIDER", "fake")
    monkeypatch.setenv("ARBILENS_LLM_TIMEOUT_SECONDS", "nope")
    with pytest.raises(ProviderError):
        load_provider_settings()


def test_urllib_transport_reads_json_and_surfaces_http_errors() -> None:
    from http.server import BaseHTTPRequestHandler, HTTPServer
    from threading import Thread

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers.get("Content-Length", "0"))
            self.rfile.read(length)
            if self.path == "/fail":
                body = b'{"error":"no"}'
                self.send_response(400)
            else:
                body = b'{"ok": true}'
                self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return None

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        port = server.server_address[1]
        transport = UrllibTransport()
        assert transport.post_json(f"http://127.0.0.1:{port}/ok", {"q": 1}, {}, 5) == {"ok": True}
        with pytest.raises(ProviderError, match="HTTP 400"):
            transport.post_json(f"http://127.0.0.1:{port}/fail", {}, {}, 5)
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
