import json
import logging
from typing import Any, TypeVar

from openai import APIConnectionError, APITimeoutError, OpenAI, RateLimitError
from openai import APIError as OpenAIAPIError
from pydantic import BaseModel, ValidationError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.errors import AppError

logger = logging.getLogger(__name__)
StructuredResponseT = TypeVar("StructuredResponseT", bound=BaseModel)


TRANSIENT_OPENAI_ERRORS = (
    APITimeoutError,
    APIConnectionError,
    RateLimitError,
    OpenAIAPIError,
)


class OpenAIResponsesService:
    def __init__(self, client: OpenAI | None = None) -> None:
        self.settings = get_settings()
        self.client = client
        if self.client is None:
            self._ensure_configured()
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.openai_timeout_seconds,
                max_retries=0,
            )

    def generate_structured_output(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_schema: type[StructuredResponseT],
        metadata: dict[str, Any] | None = None,
    ) -> StructuredResponseT:
        payload = self._create_response(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_name=response_schema.__name__,
            json_schema=response_schema.model_json_schema(),
            metadata=metadata or {},
        )
        try:
            output_text = getattr(payload, "output_text", None)
            if not output_text:
                raise AppError(
                    "OpenAI returned an empty structured response.",
                    status_code=502,
                    code="ai_empty_response",
                )
            return response_schema.model_validate(json.loads(output_text))
        except json.JSONDecodeError as exc:
            raise AppError(
                "OpenAI returned malformed JSON.",
                status_code=502,
                code="ai_malformed_response",
            ) from exc
        except ValidationError as exc:
            raise AppError(
                "OpenAI returned a response that did not match the expected schema.",
                status_code=502,
                code="ai_schema_validation_failed",
                details=[{"message": error["msg"], "location": str(error["loc"])} for error in exc.errors()],
            ) from exc

    def _create_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_name: str,
        json_schema: dict[str, Any],
        metadata: dict[str, Any],
    ):
        for attempt in Retrying(
            retry=retry_if_exception_type(TRANSIENT_OPENAI_ERRORS),
            stop=stop_after_attempt(self.settings.openai_max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            reraise=True,
        ):
            with attempt:
                logger.info(
                    "Requesting OpenAI structured response",
                    extra={
                        "provider": "openai",
                        "schema_name": schema_name,
                        "model": self.settings.openai_model,
                        "metadata": metadata,
                        "user_prompt_length": len(user_prompt),
                        "attempt_number": attempt.retry_state.attempt_number,
                    },
                )
                try:
                    return self.client.responses.create(
                        model=self.settings.openai_model,
                        input=[
                            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
                        ],
                        text={
                            "format": {
                                "type": "json_schema",
                                "name": schema_name,
                                "schema": json_schema,
                                "strict": True,
                            }
                        },
                        temperature=self.settings.openai_temperature,
                    )
                except TRANSIENT_OPENAI_ERRORS:
                    logger.warning(
                        "Transient OpenAI Responses API failure",
                        extra={"provider": "openai", "schema_name": schema_name, "metadata": metadata},
                    )
                    raise
                except Exception as exc:
                    logger.exception(
                        "OpenAI Responses API request failed",
                        extra={"provider": "openai", "schema_name": schema_name, "metadata": metadata},
                    )
                    raise AppError(
                        "AI provider request failed.",
                        status_code=502,
                        code="ai_provider_error",
                    ) from exc
        raise AppError("AI provider request failed.", status_code=502, code="ai_provider_error")

    def _ensure_configured(self) -> None:
        if not self.settings.openai_api_key:
            raise AppError(
                "OpenAI is not configured for this environment.",
                status_code=503,
                code="ai_not_configured",
            )
