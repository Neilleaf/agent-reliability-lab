import json
from pathlib import Path


def load_experiment_records(
    directory: Path,
) -> list[dict[str, object]]:
    """Load all JSON experiment records from a directory."""
    records: list[dict[str, object]] = []

    for path in sorted(directory.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))

        if not isinstance(payload, dict):
            raise TypeError(f"Experiment record must be an object: {path}")

        records.append(payload)

    return records


def _boolean_rate(
    values: list[object],
) -> float | None:
    reviewed = [value for value in values if isinstance(value, bool)]

    if not reviewed:
        return None

    return sum(reviewed) / len(reviewed)


def _false_rate(
    values: list[object],
) -> float | None:
    reviewed = [value for value in values if isinstance(value, bool)]

    if not reviewed:
        return None

    return sum(value is False for value in reviewed) / len(reviewed)


def summarize_shipping_records(
    records: list[dict[str, object]],
) -> dict[str, object]:
    """Aggregate shipping benchmark records."""
    if not records:
        raise ValueError("Cannot summarize an empty experiment.")

    scores: list[dict[str, object]] = []
    manual_reviews: list[dict[str, object]] = []

    for record in records:
        score = record.get("score")

        if not isinstance(score, dict):
            raise TypeError("Experiment record is missing a valid score.")

        scores.append(score)

        manual_review = record.get("manual_review")

        if isinstance(manual_review, dict):
            manual_reviews.append(manual_review)
        else:
            manual_reviews.append({})

    total_cases = len(records)

    tool_selection_rate = (
        sum(score.get("tool_selection_pass") is True for score in scores) / total_cases
    )

    argument_accuracy_rate = (
        sum(score.get("argument_accuracy_pass") is True for score in scores)
        / total_cases
    )

    evidence_completeness_rate = (
        sum(score.get("evidence_complete") is True for score in scores) / total_cases
    )

    turns = [score["turns"] for score in scores if isinstance(score.get("turns"), int)]

    tool_calls = [
        score["tool_call_count"]
        for score in scores
        if isinstance(score.get("tool_call_count"), int)
    ]

    conclusion_values = [review.get("conclusion_correct") for review in manual_reviews]

    consistency_values = [
        review.get("internal_consistency") for review in manual_reviews
    ]

    unsupported_claim_values = [
        review.get("unsupported_claims") for review in manual_reviews
    ]

    return {
        "cases": total_cases,
        "tool_selection_rate": tool_selection_rate,
        "argument_accuracy_rate": argument_accuracy_rate,
        "evidence_completeness_rate": (evidence_completeness_rate),
        "average_turns": sum(turns) / len(turns),
        "average_tool_calls": (sum(tool_calls) / len(tool_calls)),
        "conclusion_accuracy": _boolean_rate(conclusion_values),
        "internal_consistency_rate": _boolean_rate(consistency_values),
        "unsupported_claim_free_rate": _false_rate(unsupported_claim_values),
    }


def load_manual_reviews(
    path: Path,
) -> dict[str, dict[str, object]]:
    """Load manual benchmark reviews keyed by order ID."""
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise TypeError("Manual review file must contain an object.")

    reviews: dict[str, dict[str, object]] = {}

    for record_id, review in payload.items():
        if not isinstance(record_id, str):
            raise TypeError("Manual review keys must be strings.")

        if not isinstance(review, dict):
            raise TypeError(f"Manual review for {record_id} must be an object.")

        reviews[record_id] = review

    return reviews


def apply_manual_reviews(
    records: list[dict[str, object]],
    reviews: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
    """Attach manual reviews without modifying source records."""
    reviewed_records: list[dict[str, object]] = []

    for record in records:
        reviewed_record = dict(record)

        record_id = record.get("order_id")

        if isinstance(record_id, str) and record_id in reviews:
            reviewed_record["manual_review"] = reviews[record_id]

        reviewed_records.append(reviewed_record)

    return reviewed_records
