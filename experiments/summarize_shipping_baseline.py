from pathlib import Path

from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    load_manual_reviews,
    summarize_shipping_records,
)

REVIEW_PATH = Path("experiments/reviews/shipping_baseline_v1.json")

RESULT_DIRECTORY = Path("experiments/results/shipping_baseline_v1")


def format_rate(value: object) -> str:
    if value is None:
        return "manual review pending"

    if not isinstance(value, float):
        raise TypeError("Expected a float rate.")

    return f"{value:.1%}"


def main() -> None:
    records = load_experiment_records(RESULT_DIRECTORY)

    reviews = load_manual_reviews(REVIEW_PATH)

    records = apply_manual_reviews(
        records,
        reviews,
    )

    summary = summarize_shipping_records(records)

    print("=" * 60)
    print("AGENT RELIABILITY LAB — SHIPPING BASELINE V1")
    print("=" * 60)

    print(f"\nCases: {summary['cases']}")

    print("\nAUTOMATIC METRICS")
    print(f"  Tool selection:          {format_rate(summary['tool_selection_rate'])}")
    print(
        f"  Argument accuracy:       {format_rate(summary['argument_accuracy_rate'])}"
    )
    print(
        "  Evidence completeness:   "
        f"{format_rate(summary['evidence_completeness_rate'])}"
    )
    print(f"  Average turns:           {summary['average_turns']:.2f}")
    print(f"  Average tool calls:      {summary['average_tool_calls']:.2f}")

    print("\nMANUAL REVIEW METRICS")
    print(f"  Conclusion accuracy:     {format_rate(summary['conclusion_accuracy'])}")
    print(
        "  Internal consistency:    "
        f"{format_rate(summary['internal_consistency_rate'])}"
    )
    print(
        "  No unsupported claims:   "
        f"{format_rate(summary['unsupported_claim_free_rate'])}"
    )

    print("\nCASES")

    for record in records:
        ground_truth = record.get("ground_truth", {})
        manual_review = record.get("manual_review", {})

        status = (
            ground_truth.get("shipment_status")
            if isinstance(ground_truth, dict)
            else None
        )

        conclusion = (
            manual_review.get("conclusion_correct")
            if isinstance(manual_review, dict)
            else None
        )

        review_status = "reviewed" if isinstance(conclusion, bool) else "review pending"

        print(f"  {record.get('order_id')} [{status}] — {review_status}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
