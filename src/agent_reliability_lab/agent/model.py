from typing import Protocol

from agent_reliability_lab.agent.models import (
    AgentMessage,
    ModelResponse,
)


class ModelClientError(RuntimeError):
    """Raised when a model client cannot generate a response."""


def safe_model_error(error: ModelClientError) -> str:
    """Classify errors without echoing arbitrary provider text or credentials."""
    message = str(error).lower()
    if any(
        word in message for word in ("connection", "refused", "connect", "unreachable")
    ):
        return "Model connection unavailable (connection refused or unreachable)."
    if any(
        word in message
        for word in ("not found", "unavailable model", "model unavailable")
    ):
        return "Model unavailable or not found."
    if "scriptedmodel" in message:
        return "Scripted model has no responses remaining."
    return "Model provider response error."


class ModelClient(Protocol):
    """Interface required by AgentRunner."""

    def generate(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        """Generate the next model response."""
        ...
