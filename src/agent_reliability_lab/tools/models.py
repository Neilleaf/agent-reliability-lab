from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator


class ToolStatus(StrEnum):
    SUCCESS = "success"
    ERROR = "error"


class ToolResponse(BaseModel):
    """Structured response returned by an agent-facing tool."""

    model_config = ConfigDict(extra="forbid")

    status: ToolStatus
    data: dict[str, object] | None = None
    error_code: str | None = None
    message: str

    @model_validator(mode="after")
    def response_shape_must_match_status(self) -> Self:
        if self.status == ToolStatus.SUCCESS and self.error_code is not None:
            raise ValueError("successful responses cannot contain an error_code")

        if self.status == ToolStatus.ERROR and self.error_code is None:
            raise ValueError("error responses require an error_code")

        return self
