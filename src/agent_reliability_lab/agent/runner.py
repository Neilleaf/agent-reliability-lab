from sqlalchemy import Engine

from agent_reliability_lab.agent.model import (
    ModelClient,
    ModelClientError,
)
from agent_reliability_lab.agent.models import (
    AgentMessage,
    AgentRunResult,
    AgentRunStatus,
    MessageRole,
)
from agent_reliability_lab.tools.registry import (
    execute_tool,
    get_all_tool_schemas,
)

DEFAULT_SYSTEM_PROMPT = """
You are an operations assistant for Northstar Supply Co.

Use the available tools to retrieve business facts before making claims.

Do not assume that a customer's statement is accurate when Northstar's
records can be checked.

Do not invent customer, order, shipment, product, or inventory information.

If required information is unavailable, state that clearly.
""".strip()


class AgentRunner:
    """Execute a tool-using model until it produces a final answer."""

    def __init__(
        self,
        *,
        engine: Engine,
        model: ModelClient,
        max_turns: int = 10,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
    ) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        self._engine = engine
        self._model = model
        self._max_turns = max_turns
        self._system_prompt = system_prompt

    def run(
        self,
        task: str,
    ) -> AgentRunResult:
        messages = [
            AgentMessage(
                role=MessageRole.SYSTEM,
                content=self._system_prompt,
            ),
            AgentMessage(
                role=MessageRole.USER,
                content=task,
            ),
        ]

        tool_schemas = get_all_tool_schemas()
        tool_call_count = 0

        for turn in range(1, self._max_turns + 1):
            try:
                response = self._model.generate(
                    messages,
                    tool_schemas,
                )
            except ModelClientError:
                return AgentRunResult(
                    status=AgentRunStatus.MODEL_ERROR,
                    final_answer=None,
                    messages=messages,
                    turns=turn,
                    tool_call_count=tool_call_count,
                )

            messages.append(
                AgentMessage(
                    role=MessageRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_call_count += 1

                    tool_result = execute_tool(
                        self._engine,
                        tool_call.name,
                        tool_call.arguments,
                    )

                    messages.append(
                        AgentMessage(
                            role=MessageRole.TOOL,
                            content=tool_result.model_dump_json(),
                            tool_call_id=tool_call.call_id,
                            tool_name=tool_call.name,
                        )
                    )

                continue

            if response.content:
                return AgentRunResult(
                    status=AgentRunStatus.COMPLETED,
                    final_answer=response.content,
                    messages=messages,
                    turns=turn,
                    tool_call_count=tool_call_count,
                )

        return AgentRunResult(
            status=AgentRunStatus.MAX_TURNS_REACHED,
            final_answer=None,
            messages=messages,
            turns=self._max_turns,
            tool_call_count=tool_call_count,
        )
