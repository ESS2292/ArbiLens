from pydantic import BaseModel


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
