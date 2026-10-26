import json
from collections import Counter
from pathlib import Path

from agent_reliability_lab.evals.benchmark import reliable_run
from agent_reliability_lab.evals.diagnostics import (
    missing_tool_frequencies,
    record_diagnostics,
)


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
    *,
    id_key: str = "order_id",
) -> list[dict[str, object]]:
    """Attach manual reviews without modifying source records."""
    reviewed_records: list[dict[str, object]] = []

    for record in records:
        reviewed_record = dict(record)

        record_id = record.get(id_key)

        if isinstance(record_id, str) and record_id in reviews:
            reviewed_record["manual_review"] = reviews[record_id]

        reviewed_records.append(reviewed_record)

    return reviewed_records


def summarize_shipping_stability(
    records: list[dict[str, object]],
) -> dict[str, object]:
    """Summarize exact behavior; case means weight each case equally.

    Modes break ties by lexical sequence order or smallest call count.
    Completion measures runner termination, not answer correctness.
    """
    summary = summarize_shipping_records(records)
    grouped: dict[str, list[dict[str, object]]] = {}
    seen: set[str] = set()
    for record in records:
        case = record.get("case")
        run_id = record.get("run_id")
        if not isinstance(case, str) or not isinstance(run_id, str):
            raise TypeError("Stability records require string case and run_id.")
        if run_id in seen:
            raise ValueError(f"Duplicate stability run ID: {run_id}")
        seen.add(run_id)
        grouped.setdefault(case, []).append(record)

    cases = {}
    for case, runs in sorted(grouped.items()):
        sequences = []
        counts = []
        completed = 0
        for record in runs:
            score = record["score"]
            sequence = score.get("tool_sequence")
            count = score.get("tool_call_count")
            if not isinstance(sequence, list) or not all(
                isinstance(name, str) for name in sequence
            ):
                raise TypeError("Tool sequence must be a list of strings.")
            if type(count) is not int or count < 0:
                raise TypeError("Tool-call count must be a nonnegative integer.")
            sequences.append(tuple(sequence))
            counts.append(count)
            completed += score.get("status") == "completed"
        sequence_counts = Counter(sequences)
        call_counts = Counter(counts)
        modal_sequence = min(sequence_counts, key=lambda x: (-sequence_counts[x], x))
        modal_count = min(call_counts, key=lambda x: (-call_counts[x], x))
        cases[case] = {
            "runs": len(runs),
            "modal_tool_sequence": list(modal_sequence),
            "sequence_consistency": sequence_counts[modal_sequence] / len(runs),
            "modal_tool_call_count": modal_count,
            "tool_count_consistency": call_counts[modal_count] / len(runs),
            "completion_rate": completed / len(runs),
            "reliable_run_rate": sum(reliable_run(record["score"]) for record in runs)
            / len(runs),
        }

    reviewed = sum(
        isinstance(record.get("manual_review"), dict)
        and all(
            isinstance(record["manual_review"].get(field), bool)
            for field in (
                "conclusion_correct",
                "internal_consistency",
                "unsupported_claims",
            )
        )
        for record in records
    )
    summary.update(
        {
            "total_runs": len(records),
            "reliable_run_rate": sum(
                reliable_run(record["score"]) for record in records
            )
            / len(records),
            "cases": len(cases),
            "runs_per_case": {case: data["runs"] for case, data in cases.items()},
            "case_stability": cases,
            "completion_rate": sum(
                record["score"].get("status") == "completed" for record in records
            )
            / len(records),
            "mean_sequence_consistency": sum(
                data["sequence_consistency"] for data in cases.values()
            )
            / len(cases),
            "mean_tool_count_consistency": sum(
                data["tool_count_consistency"] for data in cases.values()
            )
            / len(cases),
            "reviewed_runs": reviewed,
            "pending_runs": len(records) - reviewed,
        }
    )
    return summary


def summarize_benchmark_records(records: list[dict[str, object]]) -> dict[str, object]:
    """Aggregate process reliability, family metrics, failures, and human labels."""
    summary = summarize_shipping_records(records)
    by_family: dict[str, list[dict[str, object]]] = {}
    seen = set()
    for record in records:
        case_id = record.get("case_id")
        family = record.get("family")
        if not isinstance(case_id, str) or not isinstance(family, str):
            raise TypeError("Benchmark records require string case_id and family.")
        if case_id in seen:
            raise ValueError(f"Duplicate benchmark case: {case_id}")
        seen.add(case_id)
        by_family.setdefault(family, []).append(record)

    def metrics(runs):
        result = summarize_shipping_records(runs)
        result["completion_rate"] = sum(
            record["score"].get("status") == "completed" for record in runs
        ) / len(runs)
        result["reliable_run_rate"] = sum(
            reliable_run(record["score"]) for record in runs
        ) / len(runs)
        return result

    summary.update(metrics(records))
    summary["by_family"] = {
        family: metrics(runs) for family, runs in sorted(by_family.items())
    }
    summary["tool_errors"] = dict(
        Counter(
            error
            for record in records
            for error in record["score"].get("tool_errors", [])
        )
    )
    summary["unexpected_tool_calls"] = dict(
        Counter(
            name
            for record in records
            for name in record["score"].get("unexpected_tool_calls", [])
        )
    )
    summary["incomplete_evidence_count"] = sum(
        record["score"].get("evidence_complete") is not True for record in records
    )
    summary["reviewed_runs"] = sum(
        isinstance(record.get("manual_review"), dict)
        and all(
            isinstance(record["manual_review"].get(key), bool)
            for key in (
                "conclusion_correct",
                "internal_consistency",
                "unsupported_claims",
            )
        )
        for record in records
    )
    summary["pending_runs"] = len(records) - summary["reviewed_runs"]
    summary["failed_cases"] = [
        record_diagnostics(record)
        for record in records
        if not reliable_run(record["score"])
    ]
    summary["missing_tools_by_family"] = {
        family: missing_tool_frequencies(runs)
        for family, runs in sorted(by_family.items())
    }
    return summary
