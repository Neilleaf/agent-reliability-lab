from typing import Protocol

from agent_reliability_lab.agent.models import (
    AgentMessage,
    ModelResponse,
)


class ModelClientError(RuntimeError):
    """Raised when a model client cannot generate a response."""


class ModelClient(Protocol):
    """Interface required by AgentRunner."""

    def generate(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        """Generate the next model response."""
        ...
