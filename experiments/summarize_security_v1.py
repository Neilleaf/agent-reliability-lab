from pathlib import Path

from agent_reliability_lab.evals.diagnostics import print_failed_cases
from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    load_manual_reviews,
)
from agent_reliability_lab.evals.security import summarize_security_records

RESULT_DIRECTORY = Path("experiments/results/security_v1")
REVIEW_PATH = Path("experiments/reviews/security_v1.json")


def format_rate(value):
    return "pending / no observations" if value is None else f"{value:.1%}"


def main() -> None:
    records = load_experiment_records(RESULT_DIRECTORY)
    if not records:
        print(
            "No security results found. Run: uv run python experiments/run_security_v1.py"
        )
        return
    records = apply_manual_reviews(
        records, load_manual_reviews(REVIEW_PATH), id_key="run_id"
    )
    summary = summarize_security_records(records)
    print("AGENT RELIABILITY LAB - SECURITY V1")
    print("Model: " + ", ".join(sorted({record["model"] for record in records})))
    print(f"Cases: {summary['cases']}")
    print("\nOVERALL")
    for label, key in (
        ("Completion", "completion_rate"),
        ("Tool selection", "tool_selection_rate"),
        ("Argument accuracy", "argument_accuracy_rate"),
        ("Evidence completeness", "evidence_completeness_rate"),
        ("Reliable runs", "reliable_run_rate"),
        ("Security pass", "security_pass_rate"),
        ("Unknown-tool attempt rate", "unknown_tool_attempt_rate"),
        ("Prohibited-action attempt rate", "prohibited_action_attempt_rate"),
        ("Malformed-call safe handling", "malformed_call_handling_rate"),
    ):
        print(f"  {label}: {format_rate(summary[key])}")
    for label, key in (
        ("Unknown-tool attempts", "unknown_tool_attempts"),
        ("Unknown tools safely rejected", "unknown_tools_safely_rejected"),
        ("Prohibited-action attempts", "prohibited_action_attempts"),
        ("Malformed-call failures (safe rejections)", "malformed_call_failures"),
        ("Successful unavailable actions", "successful_unavailable_actions"),
        ("Tool errors", "tool_errors"),
        ("Unexpected tools", "unexpected_tool_calls"),
    ):
        print(f"  {label}: {summary[key]}")
    print(f"  Average turns: {summary['average_turns']:.2f}")
    print(f"  Average tool calls: {summary['average_tool_calls']:.2f}")
    print("\nBY ATTACK CATEGORY")
    for category, data in summary["by_attack_category"].items():
        print(f"{category}: {data['cases']} cases")
        print(f"  Reliable runs: {format_rate(data['reliable_run_rate'])}")
        print(
            f"  Evidence completeness: {format_rate(data['evidence_completeness_rate'])}"
        )
        print(f"  Unknown tools: {data['unknown_tool_attempts']}")
        print(f"  Prohibited attempts: {data['prohibited_action_attempts']}")
        print(f"  Malformed-call safe rejections: {data['malformed_call_failures']}")
        print(f"  Tool errors: {data['tool_errors']}")
    print_failed_cases(summary["failed_cases"])
    print("\nMANUAL REVIEW")
    print(f"  Reviewed: {summary['reviewed_runs']}; pending: {summary['pending_runs']}")
    for label, key in (
        ("Conclusion accuracy", "conclusion_accuracy"),
        ("Internal consistency", "internal_consistency_rate"),
        ("No unsupported claims", "unsupported_claim_free_rate"),
        ("Policy violations", "policy_violation_rate"),
        ("Followed user bypass", "followed_user_bypass_instruction_rate"),
    ):
        print(f"  {label}: {format_rate(summary[key])}")


if __name__ == "__main__":
    main()
