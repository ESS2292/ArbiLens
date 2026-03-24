import pytest

from app.core.errors import AppError
from app.schemas.ai import ClauseExtractionResponseSchema, RiskExplanationSchema
from app.services.ai import OpenAIResponsesService


class _FakeResponsesClient:
    def __init__(self, output_text: str) -> None:
        self._output_text = output_text
        self.responses = self

    def create(self, **_: object):
        class _Payload:
            def __init__(self, text: str) -> None:
                self.output_text = text

        return _Payload(self._output_text)


def test_openai_structured_response_validation_accepts_valid_json() -> None:
    service = OpenAIResponsesService(
        client=_FakeResponsesClient(
            '{"summary":"Risk summary","rationale":"Rule-based rationale","recommendation":"Mitigate it","confidence":0.8}'
        )
    )

    response = service.generate_structured_output(
        system_prompt="system",
        user_prompt="user",
        response_schema=RiskExplanationSchema,
        metadata={"test": True},
    )

    assert isinstance(response, RiskExplanationSchema)
    assert response.confidence == 0.8


def test_openai_structured_response_rejects_malformed_json() -> None:
    service = OpenAIResponsesService(client=_FakeResponsesClient('{"summary": '))

    with pytest.raises(AppError) as exc:
        service.generate_structured_output(
            system_prompt="system",
            user_prompt="user",
            response_schema=RiskExplanationSchema,
        )

    assert exc.value.code == "ai_malformed_response"


def test_openai_structured_response_rejects_empty_payload() -> None:
    service = OpenAIResponsesService(client=_FakeResponsesClient(""))

    with pytest.raises(AppError) as exc:
        service.generate_structured_output(
            system_prompt="system",
            user_prompt="user",
            response_schema=RiskExplanationSchema,
        )

    assert exc.value.code == "ai_empty_response"


def test_openai_structured_response_validation_rejects_invalid_schema() -> None:
    service = OpenAIResponsesService(
        client=_FakeResponsesClient('{"clauses":[{"clause_type":"termination","confidence":"high"}]}')
    )

    with pytest.raises(AppError) as exc:
        service.generate_structured_output(
            system_prompt="system",
            user_prompt="user",
            response_schema=ClauseExtractionResponseSchema,
        )

    assert exc.value.code == "ai_schema_validation_failed"


def test_openai_structured_response_rejects_risk_explanation_with_identical_summary_and_rationale() -> None:
    service = OpenAIResponsesService(
        client=_FakeResponsesClient(
            '{"summary":"Same text","rationale":"Same text","recommendation":"Mitigate it","confidence":0.8}'
        )
    )

    with pytest.raises(AppError) as exc:
        service.generate_structured_output(
            system_prompt="system",
            user_prompt="user",
            response_schema=RiskExplanationSchema,
        )

    assert exc.value.code == "ai_schema_validation_failed"
