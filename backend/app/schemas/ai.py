from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import ClauseType


class ClauseCandidateSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clause_type: ClauseType
    title: str | None = Field(default=None, max_length=255)
    extracted_text: str = Field(min_length=1, max_length=8000)
    confidence: float = Field(ge=0, le=1)
    source_chunk_index: int = Field(ge=0)
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("extracted_text")
    @classmethod
    def normalize_extracted_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("extracted_text must not be blank")
        return normalized

    @field_validator("page_end")
    @classmethod
    def validate_page_range(cls, value: int | None, info):
        page_start = info.data.get("page_start")
        if value is not None and page_start is not None and value < page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return value


class ClauseExtractionResponseSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    clauses: list[ClauseCandidateSchema]


class RiskExplanationSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    rationale: str = Field(min_length=1, max_length=2000)
    recommendation: str = Field(min_length=1, max_length=1200)
    confidence: float = Field(ge=0, le=1)

    @field_validator("summary", "rationale", "recommendation")
    @classmethod
    def normalize_text_fields(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text fields must not be blank")
        return normalized

    @model_validator(mode="after")
    def validate_summary_is_distinct(self):
        if self.summary == self.rationale:
            raise ValueError("summary and rationale should not be identical")
        return self
