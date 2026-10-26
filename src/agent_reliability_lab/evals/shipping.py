import json

from agent_reliability_lab.agent.models import (
    AgentRunResult,
    MessageRole,
)


def score_shipping_run(
    result: AgentRunResult,
    *,
    expected_order_id: str,
    expected_shipment_status: str,
) -> dict[str, object]:
    """Score deterministic parts of a shipment investigation."""
    tool_calls = [
        tool_call
        for message in result.messages
        if message.role == MessageRole.ASSISTANT
        for tool_call in message.tool_calls
    ]

    tool_names = [tool_call.name for tool_call in tool_calls]

    required_tools = {
        "get_order",
        "track_shipment",
    }

    tool_selection_pass = required_tools.issubset(set(tool_names))

    relevant_calls = [
        tool_call for tool_call in tool_calls if tool_call.name in required_tools
    ]

    argument_accuracy_pass = all(
        tool_call.arguments.get("order_id") == expected_order_id
        for tool_call in relevant_calls
    )

    tool_errors: list[str] = []
    observed_shipment_status: str | None = None

    for message in result.messages:
        if message.role != MessageRole.TOOL or message.content is None:
            continue

        payload = json.loads(message.content)

        error_code = payload.get("error_code")

        if error_code is not None:
            tool_errors.append(error_code)

        if message.tool_name == "track_shipment":
            data = payload.get("data")

            if isinstance(data, dict):
                shipment = data.get("shipment")

                if isinstance(shipment, dict):
                    status = shipment.get("shipment_status")

                    if isinstance(status, str):
                        observed_shipment_status = status

    evidence_complete = (
        tool_selection_pass and observed_shipment_status == expected_shipment_status
    )

    unexpected_tool_calls = [name for name in tool_names if name not in required_tools]

    return {
        "status": result.status.value,
        "turns": result.turns,
        "tool_call_count": result.tool_call_count,
        "tool_sequence": tool_names,
        "tool_selection_pass": tool_selection_pass,
        "argument_accuracy_pass": argument_accuracy_pass,
        "evidence_complete": evidence_complete,
        "expected_shipment_status": expected_shipment_status,
        "observed_shipment_status": observed_shipment_status,
        "tool_errors": tool_errors,
        "unexpected_tool_calls": unexpected_tool_calls,
    }
