from pathlib import Path

from agent_reliability_lab.evals.cases import FAMILIES
from agent_reliability_lab.evals.diagnostics import print_failed_cases
from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    load_manual_reviews,
    summarize_benchmark_records,
)

RESULT_DIRECTORY = Path("experiments/results/benchmark_v1")
REVIEW_PATH = Path("experiments/reviews/benchmark_v1.json")


def format_rate(value: object) -> str:
    return "manual review pending" if value is None else f"{value:.1%}"


def main() -> None:
    records = load_experiment_records(RESULT_DIRECTORY)
    if not records:
        print(
            "No benchmark results found. Run: uv run python experiments/run_benchmark_v1.py"
        )
        return
    records = apply_manual_reviews(
        records, load_manual_reviews(REVIEW_PATH), id_key="run_id"
    )
    summary = summarize_benchmark_records(records)
    print("AGENT RELIABILITY LAB - BENCHMARK V1")
    print(
        "HISTORICAL pre-QA results. Run arl benchmark for the corrected requirements; arl summary reports both namespaces."
    )
    print("Model: " + ", ".join(sorted({record["model"] for record in records})))
    print(f"Total cases: {summary['cases']}")
    print("\nOVERALL")
    for label, key in (
        ("Completion rate", "completion_rate"),
        ("Tool selection", "tool_selection_rate"),
        ("Argument accuracy", "argument_accuracy_rate"),
        ("Evidence completeness", "evidence_completeness_rate"),
        ("Reliable runs", "reliable_run_rate"),
    ):
        print(f"  {label}: {format_rate(summary[key])}")
    print(f"  Average turns: {summary['average_turns']:.2f}")
    print(f"  Average tool calls: {summary['average_tool_calls']:.2f}")
    print("\nBY FAMILY")
    for family, name in FAMILIES.items():
        data = summary["by_family"].get(family)
        print(f"{family} {name}")
        if data is None:
            print("  No results")
            continue
        print(f"  Cases: {data['cases']}")
        for label, key in (
            ("Tool selection", "tool_selection_rate"),
            ("Evidence completeness", "evidence_completeness_rate"),
            ("Reliable runs", "reliable_run_rate"),
        ):
            print(f"  {label}: {format_rate(data[key])}")
        print("  Most frequently missing:")
        missing = summary["missing_tools_by_family"][family]
        if not missing:
            print("    None")
        for tool, count in missing.items():
            print(f"    {tool}: {count}/{data['cases']}")
    print("\nFAILURE INFORMATION")
    print(f"  Tool errors: {summary['tool_errors']}")
    print(f"  Unexpected tool calls: {summary['unexpected_tool_calls']}")
    print(f"  Incomplete evidence: {summary['incomplete_evidence_count']}")
    print_failed_cases(summary["failed_cases"])
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
