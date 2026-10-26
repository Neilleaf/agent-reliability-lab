"""Objective evidence scoring shared by all five benchmark families."""

import json

from agent_reliability_lab.agent.models import AgentRunResult, MessageRole
from agent_reliability_lab.evals.cases import BenchmarkCase


def reliable_run(score: dict[str, object]) -> bool:
    """Process reliability only; never infer semantic answer correctness."""
    return score.get("status") == "completed" and all(
        score.get(field) is True
        for field in (
            "tool_selection_pass",
            "argument_accuracy_pass",
            "evidence_complete",
        )
    )


def _contains(actual: object, expected: object) -> bool:
    if isinstance(expected, dict):
        return isinstance(actual, dict) and all(
            key in actual and _contains(actual[key], value)
            for key, value in expected.items()
        )
    return type(actual) is type(expected) and actual == expected


def evidence_category(requirement) -> str:
    """Stable evidence labels distinguish separate policy and rejection probes."""
    if getattr(requirement, "expected_error", None):
        return f"safe_rejection:{requirement.tool}"
    if requirement.tool == "get_policy":
        return f"policy:{requirement.arguments['policy_id']}"
    return {
        "get_order": "order",
        "track_shipment": "shipment",
        "get_invoice": "invoice",
        "get_product": "product",
        "check_inventory": "inventory",
        "get_damage_report": "damage_report",
    }.get(requirement.tool, requirement.tool)


def score_benchmark_run(
    result: AgentRunResult, case: BenchmarkCase
) -> dict[str, object]:
    """Require successful, case-matching evidence linked to the right tool call.

    Expected business decisions stay in ground truth for human review. No final
    answer text participates in automatic scoring.
    """
    requirements = case.required_evidence
    required_tools = {item.tool for item in requirements}
    calls = [
        call
        for message in result.messages
        if message.role == MessageRole.ASSISTANT
        for call in message.tool_calls
    ]
    sequence = [call.name for call in calls]
    relevant = [call for call in calls if call.name in required_tools]
    selection = required_tools.issubset(sequence)
    arguments = bool(relevant) and all(
        any(
            call.name == item.tool and call.arguments == item.arguments
            for item in requirements
        )
        for call in relevant
    )
    observed: set[int] = set()
    pending = {}
    errors = []
    for message in result.messages:
        if message.role == MessageRole.ASSISTANT:
            for call in message.tool_calls:
                pending[call.call_id] = call
        if message.role != MessageRole.TOOL:
            continue
        try:
            payload = json.loads(message.content or "")
            if not isinstance(payload, dict):
                raise TypeError("Expected tool response object")
        except (ValueError, TypeError):
            errors.append("MALFORMED_TOOL_RESPONSE")
            continue
        if payload.get("error_code"):
            errors.append(str(payload["error_code"]))
        call = pending.pop(message.tool_call_id, None)
        if call is None or call.name != message.tool_name:
            continue
        for index, item in enumerate(requirements):
            expected_error = getattr(item, "expected_error", None)
            matches_response = (
                payload.get("status") == "error"
                and payload.get("error_code") == expected_error
                if expected_error
                else payload.get("status") == "success"
                and _contains(payload.get("data"), item.expected_data)
            )
            if (
                call.name == item.tool
                and call.arguments == item.arguments
                and matches_response
            ):
                observed.add(index)
    unexpected = [name for name in sequence if name not in required_tools]
    score = {
        "status": result.status.value,
        "turns": result.turns,
        "tool_call_count": result.tool_call_count,
        "tool_sequence": sequence,
        "required_tools": sorted(required_tools),
        "missing_required_tools": sorted(required_tools - set(sequence)),
        "expected_evidence_categories": [
            evidence_category(item) for item in requirements
        ],
        "observed_evidence_categories": [
            evidence_category(item)
            for index, item in enumerate(requirements)
            if index in observed
        ],
        "missing_evidence_categories": [
            evidence_category(item)
            for index, item in enumerate(requirements)
            if index not in observed
        ],
        "tool_selection_pass": selection,
        "argument_accuracy_pass": arguments,
        "evidence_complete": len(observed) == len(requirements),
        "missing_evidence": [
            {"tool": item.tool, "arguments": item.arguments}
            for index, item in enumerate(requirements)
            if index not in observed
        ],
        "unexpected_tool_calls": unexpected,
        "tool_errors": errors,
    }
    score["reliable_run"] = reliable_run(score)
    failures = []
    for failure, present in (
        ("tool_selection_failure", not selection),
        ("invalid_tool_arguments", not arguments),
        ("incomplete_evidence", not score["evidence_complete"]),
        ("unexpected_tool", bool(unexpected)),
        ("tool_error", bool(errors)),
        ("max_turns_reached", result.status.value == "max_turns_reached"),
        ("model_error", result.status.value == "model_error"),
    ):
        if present:
            failures.append(failure)
    score["automatic_failure_types"] = failures
    return score
