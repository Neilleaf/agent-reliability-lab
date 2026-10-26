from pathlib import Path

from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    load_manual_reviews,
    summarize_shipping_stability,
)

RESULT_DIRECTORY = Path("experiments/results/shipping_stability_v1")
REVIEW_PATH = Path("experiments/reviews/shipping_stability_v1.json")


def format_rate(value: object) -> str:
    return "manual review pending" if value is None else f"{value:.1%}"


def main() -> None:
    records = load_experiment_records(RESULT_DIRECTORY)
    if not records:
        print(
            "No stability results found. Run: uv run python experiments/run_shipping_stability.py"
        )
        return
    reviews = load_manual_reviews(REVIEW_PATH)
    records = apply_manual_reviews(records, reviews, id_key="run_id")
    summary = summarize_shipping_stability(records)
    print("AGENT RELIABILITY LAB - SHIPPING STABILITY V1")
    print("Model: " + ", ".join(sorted({record["model"] for record in records})))
    print(f"Cases: {summary['cases']}")
    print(f"Runs per case: {summary['runs_per_case']}")
    print(f"Total runs: {summary['total_runs']}")
    print("\nAUTOMATIC RELIABILITY")
    for label, key in (
        ("Tool selection", "tool_selection_rate"),
        ("Argument accuracy", "argument_accuracy_rate"),
        ("Evidence completeness", "evidence_completeness_rate"),
        ("Completion rate", "completion_rate"),
        ("Reliable runs", "reliable_run_rate"),
    ):
        print(f"  {label}: {format_rate(summary[key])}")
    print(f"  Average turns: {summary['average_turns']:.2f}")
    print(f"  Average tool calls: {summary['average_tool_calls']:.2f}")
    print("\nSTABILITY")
    for case, data in summary["case_stability"].items():
        print(f"{case} ({data['runs']} runs):")
        print(f"  Modal tool sequence: {data['modal_tool_sequence']}")
        print(f"  Sequence consistency: {format_rate(data['sequence_consistency'])}")
        print(f"  Modal tool-call count: {data['modal_tool_call_count']}")
        print(
            f"  Tool-count consistency: {format_rate(data['tool_count_consistency'])}"
        )
        print(f"  Completion rate: {format_rate(data['completion_rate'])}")
        print(f"  Reliable runs: {format_rate(data['reliable_run_rate'])}")
    print(
        "Consistency measures repeated behavior; reliable runs require completed, correct tool use and complete evidence."
    )
    print("\nOVERALL")
    print(
        f"  Mean sequence consistency: {format_rate(summary['mean_sequence_consistency'])}"
    )
    print(
        f"  Mean tool-count consistency: {format_rate(summary['mean_tool_count_consistency'])}"
    )
    print("\nMANUAL REVIEW")
    print(f"  Reviewed: {summary['reviewed_runs']}; pending: {summary['pending_runs']}")
    for label, key in (
        ("Conclusion accuracy", "conclusion_accuracy"),
        ("Internal consistency", "internal_consistency_rate"),
        ("No unsupported claims", "unsupported_claim_free_rate"),
    ):
        print(f"  {label}: {format_rate(summary[key])}")


if __name__ == "__main__":
    main()
