"""Read-only diagnostics, including traces saved before diagnostic fields existed."""

from collections import Counter

from agent_reliability_lab.agent.models import AgentRunResult
from agent_reliability_lab.evals.benchmark import reliable_run, score_benchmark_run
from agent_reliability_lab.evals.cases import BenchmarkCase


def record_diagnostics(record: dict[str, object]) -> dict[str, object]:
    """Use saved case requirements, never substitute current benchmark fixtures."""
    score = record.get("score")
    if not isinstance(score, dict):
        raise TypeError("Record requires a score object.")
    diagnostic_score = score
    metadata = record.get("case_metadata")
    trace = record.get("trace")
    if isinstance(metadata, dict) and isinstance(trace, dict):
        if "security_case_id" in metadata:
            from agent_reliability_lab.evals.security import SecurityCase

            case = SecurityCase.model_validate(metadata)
        else:
            case = BenchmarkCase.model_validate(metadata)
        diagnostic_score = score_benchmark_run(
            AgentRunResult.model_validate(trace), case
        )
    required = diagnostic_score.get("required_tools")
    observed = diagnostic_score.get("tool_sequence", [])
    return {
        "case_id": record.get("security_case_id", record.get("case_id")),
        "required_tools": required,
        "observed_tool_sequence": observed,
        "missing_required_tools": diagnostic_score.get("missing_required_tools"),
        "expected_evidence_categories": diagnostic_score.get(
            "expected_evidence_categories"
        ),
        "observed_evidence_categories": diagnostic_score.get(
            "observed_evidence_categories"
        ),
        "missing_evidence_categories": diagnostic_score.get(
            "missing_evidence_categories"
        ),
        "tool_errors": diagnostic_score.get("tool_errors", []),
        "unexpected_tools": diagnostic_score.get("unexpected_tool_calls", []),
        "status": score.get("status"),
        "reliable_run": reliable_run(score),
    }


def missing_tool_frequencies(records: list[dict[str, object]]) -> dict[str, int]:
    """Count cases omitting each required tool once, including repeated policies."""
    counts = Counter()
    for record in records:
        missing = record_diagnostics(record)["missing_required_tools"]
        if missing is not None:
            counts.update(set(missing))
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def print_failed_cases(diagnostics: list[dict[str, object]]) -> None:
    print("\nFAILED CASES")
    failed = [
        item
        for item in diagnostics
        if not item["reliable_run"] or item.get("security_pass") is False
    ]
    if not failed:
        print("  None")
    for item in failed:
        print(item["case_id"])
        for label, key in (
            ("Required tools", "required_tools"),
            ("Observed tools", "observed_tool_sequence"),
            ("Missing tools", "missing_required_tools"),
            ("Expected evidence", "expected_evidence_categories"),
            ("Observed evidence", "observed_evidence_categories"),
            ("Missing evidence", "missing_evidence_categories"),
            ("Tool errors", "tool_errors"),
            ("Unexpected tools", "unexpected_tools"),
            ("Status", "status"),
        ):
            value = item[key]
            print(
                f"  {label}: {value if value is not None else 'unavailable in saved record'}"
            )
        print(f"  Reliable: {str(item['reliable_run']).lower()}")
        if "security_pass" in item:
            print(f"  Security pass: {str(item['security_pass']).lower()}")
            print(f"  Unknown-tool attempts: {item['attempted_unknown_tools']}")
            print(f"  Prohibited-action attempts: {item['prohibited_action_attempts']}")
