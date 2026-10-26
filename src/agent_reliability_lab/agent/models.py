from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """A tool invocation requested by a model."""

    model_config = ConfigDict(extra="forbid")

    call_id: str
    name: str
    arguments: dict[str, object]


class AgentMessage(BaseModel):
    """Provider-neutral message exchanged during an agent run."""

    model_config = ConfigDict(extra="forbid")

    role: MessageRole
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None
    tool_name: str | None = None


class ModelResponse(BaseModel):
    """Provider-neutral output returned by a model."""

    model_config = ConfigDict(extra="forbid")

    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)


class AgentRunStatus(StrEnum):
    COMPLETED = "completed"
    MAX_TURNS_REACHED = "max_turns_reached"
    MODEL_ERROR = "model_error"


class AgentRunResult(BaseModel):
    """Final result and trace of an agent run."""

    model_config = ConfigDict(extra="forbid")

    status: AgentRunStatus
    final_answer: str | None
    messages: list[AgentMessage]
    turns: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)
    model_error: str | None = None
    runtime: "RunRuntime | None" = None


class ToolCallTiming(BaseModel):
    call_id: str
    tool_name: str
    duration_seconds: float = Field(ge=0)


class RunRuntime(BaseModel):
    duration_seconds: float = Field(ge=0)
    model_call_durations_seconds: list[float] = Field(default_factory=list)
    tool_call_timings: list[ToolCallTiming] = Field(default_factory=list)
    cost: str = "not_applicable/local"
