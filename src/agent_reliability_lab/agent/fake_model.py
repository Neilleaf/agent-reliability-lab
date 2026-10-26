from agent_reliability_lab.agent.model import ModelClientError
from agent_reliability_lab.agent.models import (
    AgentMessage,
    ModelResponse,
)


class ScriptedModel:
    """Deterministic model used for agent-loop testing."""

    def __init__(
        self,
        responses: list[ModelResponse],
    ) -> None:
        self._responses = list(responses)
        self._position = 0

    def generate(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        del messages
        del tools

        if self._position >= len(self._responses):
            raise ModelClientError("ScriptedModel has no responses remaining")

        response = self._responses[self._position]
        self._position += 1

        return response
