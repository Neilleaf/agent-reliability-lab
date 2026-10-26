from itertools import count

from ollama import Client, RequestError, ResponseError

from agent_reliability_lab.agent.model import (
    ModelClientError,
)
from agent_reliability_lab.agent.models import (
    AgentMessage,
    MessageRole,
    ModelResponse,
    ToolCall,
)


class OllamaModelClient:
    """Local Ollama implementation of the ARL model interface."""

    def __init__(
        self,
        model: str = "qwen3:4b-instruct",
    ) -> None:
        self._model = model
        self._client = Client()
        self._call_ids = count(1)

    def generate(
        self,
        messages: list[AgentMessage],
        tools: list[dict[str, object]],
    ) -> ModelResponse:
        ollama_messages = [self._convert_message(message) for message in messages]

        ollama_tools = [
            {
                "type": "function",
                "function": schema,
            }
            for schema in tools
        ]

        try:
            response = self._client.chat(
                model=self._model,
                messages=ollama_messages,
                tools=ollama_tools,
            )
        except (RequestError, ResponseError, ConnectionError) as exc:
            raise ModelClientError(str(exc)) from exc

        tool_calls: list[ToolCall] = []

        for tool_call in response.message.tool_calls or []:
            tool_calls.append(
                ToolCall(
                    call_id=self._get_call_id(tool_call),
                    name=tool_call.function.name,
                    arguments=dict(tool_call.function.arguments),
                )
            )

        return ModelResponse(
            content=response.message.content or None,
            tool_calls=tool_calls,
        )

    def _get_call_id(self, tool_call: object) -> str:
        call_id = getattr(tool_call, "id", None)

        if call_id:
            return str(call_id)

        return f"ollama-call-{next(self._call_ids)}"

    @staticmethod
    def _convert_message(
        message: AgentMessage,
    ) -> dict[str, object]:
        if message.role == MessageRole.TOOL:
            result: dict[str, object] = {
                "role": "tool",
                "content": message.content or "",
            }

            if message.tool_name is not None:
                result["tool_name"] = message.tool_name

            return result

        converted: dict[str, object] = {
            "role": message.role.value,
            "content": message.content or "",
        }

        if message.tool_calls:
            converted["tool_calls"] = [
                {
                    "function": {
                        "name": tool_call.name,
                        "arguments": tool_call.arguments,
                    }
                }
                for tool_call in message.tool_calls
            ]

        return converted
