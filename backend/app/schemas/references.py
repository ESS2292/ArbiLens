from pydantic import BaseModel, ConfigDict, Field, field_validator


class SourceCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_type: str = Field(min_length=1, max_length=64)
    clause_id: str | None = None
    chunk_id: str | None = None
    document_version_id: str | None = None
    page_start: int | None = Field(default=None, ge=1)
    page_end: int | None = Field(default=None, ge=1)

    @field_validator("reference_type")
    @classmethod
    def validate_reference_type(cls, value: str) -> str:
        normalized = value.strip()
        if normalized not in {"clause", "document_context"}:
            raise ValueError("reference_type must be clause or document_context")
        return normalized

    @field_validator("page_end")
    @classmethod
    def validate_page_range(cls, value: int | None, info):
        page_start = info.data.get("page_start")
        if value is not None and page_start is not None and value < page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return value
