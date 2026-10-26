from collections.abc import Callable
from time import perf_counter

from sqlalchemy import Engine

from agent_reliability_lab.agent.model import (
    ModelClient,
    ModelClientError,
    safe_model_error,
)
from agent_reliability_lab.agent.models import (
    AgentMessage,
    AgentRunResult,
    AgentRunStatus,
    MessageRole,
    RunRuntime,
    ToolCallTiming,
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
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be at least 1")

        self._engine = engine
        self._model = model
        self._max_turns = max_turns
        self._system_prompt = system_prompt
        self._clock = clock

    def run(
        self,
        task: str,
    ) -> AgentRunResult:
        started = self._clock()
        model_durations = []
        tool_timings = []

        def finish(status, answer, turn, error=None):
            return AgentRunResult(
                status=status,
                final_answer=answer,
                messages=messages,
                turns=turn,
                tool_call_count=tool_call_count,
                model_error=error,
                runtime=RunRuntime(
                    duration_seconds=self._clock() - started,
                    model_call_durations_seconds=model_durations,
                    tool_call_timings=tool_timings,
                ),
            )

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
            model_started = self._clock()
            try:
                response = self._model.generate(
                    messages,
                    tool_schemas,
                )
            except ModelClientError as exc:
                model_durations.append(self._clock() - model_started)
                return finish(
                    AgentRunStatus.MODEL_ERROR, None, turn, safe_model_error(exc)
                )

            model_durations.append(self._clock() - model_started)

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

                    tool_started = self._clock()
                    tool_result = execute_tool(
                        self._engine,
                        tool_call.name,
                        tool_call.arguments,
                    )
                    tool_timings.append(
                        ToolCallTiming(
                            call_id=tool_call.call_id,
                            tool_name=tool_call.name,
                            duration_seconds=self._clock() - tool_started,
                        )
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
                return finish(AgentRunStatus.COMPLETED, response.content, turn)

        return finish(AgentRunStatus.MAX_TURNS_REACHED, None, self._max_turns)
