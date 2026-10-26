import json
from copy import deepcopy
from pathlib import Path

import pytest

from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_manual_reviews,
    summarize_shipping_records,
)


def test_shipping_report_aggregates_metrics() -> None:
    records = [
        {
            "score": {
                "tool_selection_pass": True,
                "argument_accuracy_pass": True,
                "evidence_complete": True,
                "turns": 2,
                "tool_call_count": 2,
            },
            "manual_review": {
                "conclusion_correct": True,
                "internal_consistency": True,
                "unsupported_claims": False,
            },
        },
        {
            "score": {
                "tool_selection_pass": True,
                "argument_accuracy_pass": False,
                "evidence_complete": False,
                "turns": 3,
                "tool_call_count": 3,
            },
            "manual_review": {
                "conclusion_correct": False,
                "internal_consistency": False,
                "unsupported_claims": True,
            },
        },
    ]

    summary = summarize_shipping_records(records)

    assert summary["cases"] == 2
    assert summary["tool_selection_rate"] == 1.0
    assert summary["argument_accuracy_rate"] == 0.5
    assert summary["evidence_completeness_rate"] == 0.5
    assert summary["average_turns"] == 2.5
    assert summary["average_tool_calls"] == 2.5
    assert summary["conclusion_accuracy"] == 0.5
    assert summary["internal_consistency_rate"] == 0.5
    assert summary["unsupported_claim_free_rate"] == 0.5


def test_shipping_report_allows_pending_manual_review() -> None:
    records = [
        {
            "score": {
                "tool_selection_pass": True,
                "argument_accuracy_pass": True,
                "evidence_complete": True,
                "turns": 2,
                "tool_call_count": 2,
            },
            "manual_review": {
                "conclusion_correct": None,
                "internal_consistency": None,
                "unsupported_claims": None,
            },
        }
    ]

    summary = summarize_shipping_records(records)

    assert summary["conclusion_accuracy"] is None
    assert summary["internal_consistency_rate"] is None
    assert summary["unsupported_claim_free_rate"] is None


def test_manual_reviews_are_applied_by_order_id() -> None:
    records = [
        {
            "order_id": "ORD-00001",
            "manual_review": {
                "conclusion_correct": None,
            },
        }
    ]

    reviews = {
        "ORD-00001": {
            "conclusion_correct": True,
            "internal_consistency": True,
            "unsupported_claims": False,
        }
    }

    reviewed_records = apply_manual_reviews(
        records,
        reviews,
    )

    manual_review = reviewed_records[0]["manual_review"]

    assert isinstance(manual_review, dict)
    assert manual_review["conclusion_correct"] is True

    original_review = records[0]["manual_review"]

    assert isinstance(original_review, dict)
    assert original_review["conclusion_correct"] is None


def test_manual_reviews_preserve_unmatched_records_and_source() -> None:
    records = [
        {"order_id": "ORD-00002", "manual_review": {"conclusion_correct": None}},
        {"order_id": "ORD-00001", "manual_review": {"notes": "Existing review"}},
        {"order_id": "ORD-00003"},
    ]
    original_records = deepcopy(records)
    reviews = {"ORD-00002": {"conclusion_correct": True}}

    reviewed_records = apply_manual_reviews(records, reviews)

    assert reviewed_records[0]["manual_review"] == reviews["ORD-00002"]
    assert reviewed_records[1:] == original_records[1:]
    assert records == original_records
    assert reviewed_records is not records
    assert all(
        result is not source for result, source in zip(reviewed_records, records)
    )


def test_load_manual_reviews(tmp_path: Path) -> None:
    reviews = {"ORD-00001": {"conclusion_correct": True, "failure_types": []}}
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps(reviews), encoding="utf-8")

    assert load_manual_reviews(path) == reviews


@pytest.mark.parametrize("payload", [[], None, True, 42, "invalid"])
def test_load_manual_reviews_rejects_invalid_top_level(
    tmp_path: Path, payload: object
) -> None:
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(TypeError, match="must contain an object"):
        load_manual_reviews(path)


@pytest.mark.parametrize("review", [[], None, True, 42, "invalid"])
def test_load_manual_reviews_rejects_invalid_entries(
    tmp_path: Path, review: object
) -> None:
    path = tmp_path / "reviews.json"
    path.write_text(json.dumps({"ORD-00001": review}), encoding="utf-8")

    with pytest.raises(
        TypeError, match="Manual review for ORD-00001 must be an object"
    ):
        load_manual_reviews(path)
