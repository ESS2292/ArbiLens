"""Paraphrase faithfulness, offline and behind the provider interface."""

import pytest

from app.engine.embeddings import ProviderSettings
from app.engine.errors import ProviderError
from app.engine.faithfulness import (
    DeterministicFaithfulnessJudge,
    OpenAICompatibleFaithfulnessJudge,
    judge_for_settings,
)
from app.engine.types import Citation


def _cite(text: str) -> Citation:
    return Citation(chunk_id="c0", char_start=0, char_end=len(text), text=text, section_title=None)


def test_deterministic_judge_accepts_a_paraphrase_and_rejects_a_distractor() -> None:
    judge = DeterministicFaithfulnessJudge()
    citation = _cite("The aggregate liability of Provider under this agreement is unlimited.")
    supported = judge.judge("There is no ceiling on the provider's monetary exposure.", [citation])
    assert supported.faithful
    assert supported.judge == "deterministic"
    distractor = judge.judge(
        "Invoices must be settled within thirty days of receipt.",
        [citation],
    )
    assert not distractor.faithful


def test_deterministic_judge_rejects_a_cap_contradiction_and_missing_numbers() -> None:
    judge = DeterministicFaithfulnessJudge()
    capped = _cite("The aggregate liability shall not exceed the charges paid during the prior twelve months.")
    clash = judge.judge("There is no ceiling on monetary exposure.", [capped])
    assert not clash.faithful
    numbered = judge.judge("Uptime is 99.9 percent.", [_cite("The service is reliable.")])
    assert not numbered.faithful
    assert not judge.judge("Anything.", []).faithful


def test_openai_judge_reads_a_json_verdict() -> None:
    class Transport:
        def post_json(
            self,
            url: str,
            payload: dict[str, object],
            headers: dict[str, str],
            timeout: float,
        ) -> dict[str, object]:
            assert url.endswith("/chat/completions")
            assert "Claim:" in str(payload["messages"])
            return {"choices": [{"message": {"content": '{"faithful": false, "reason": "different obligation"}'}}]}

    settings = ProviderSettings(
        llm_provider="openai",
        embedding_provider="fake",
        base_url="https://example.test/v1",
        api_key="test-key",
        llm_model="gpt-test",
        embedding_model="embed-test",
        timeout_seconds=5,
    )
    verdict = OpenAICompatibleFaithfulnessJudge(settings, Transport()).judge("A claim.", [_cite("A quote.")])
    assert verdict.faithful is False
    assert verdict.judge == "openai"
    assert verdict.reason == "different obligation"


def test_judge_setting_defaults_offline_and_rejects_unknown_names(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ARBILENS_JUDGE_PROVIDER", raising=False)
    assert judge_for_settings().name == "deterministic"
    monkeypatch.setenv("ARBILENS_JUDGE_PROVIDER", "mystery")
    with pytest.raises(ProviderError):
        judge_for_settings()
