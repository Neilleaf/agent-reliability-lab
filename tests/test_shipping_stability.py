import json
import runpy
from copy import deepcopy
from pathlib import Path

import pytest

from agent_reliability_lab.agent.fake_model import ScriptedModel
from agent_reliability_lab.agent.models import ModelResponse
from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    load_manual_reviews,
    summarize_shipping_stability,
)


def make_record(case, repetition, sequence, status="completed"):
    return {
        "case": case,
        "run_id": f"{case}/run_{repetition:02d}",
        "order_id": "ORD-00001",
        "score": {
            "tool_sequence": sequence,
            "tool_call_count": len(sequence),
            "status": status,
            "turns": len(sequence) + 1,
            "tool_selection_pass": True,
            "argument_accuracy_pass": repetition != 2,
            "evidence_complete": status == "completed",
        },
        "manual_review": {"conclusion_correct": None},
    }


def test_stability_aggregates_modes_and_completion():
    records = [
        make_record("lost", 1, ["get_order", "track_shipment"]),
        make_record("lost", 2, ["get_order", "track_shipment"]),
        make_record("lost", 3, [], "model_error"),
        make_record("delayed", 1, ["track_shipment"], "max_turns_reached"),
    ]
    original = deepcopy(records)
    summary = summarize_shipping_stability(records)
    assert records == original
    assert summary["total_runs"] == 4
    assert summary["cases"] == 2
    assert summary["runs_per_case"] == {"lost": 3, "delayed": 1}
    assert summary["tool_selection_rate"] == 1.0
    assert summary["argument_accuracy_rate"] == 0.75
    assert summary["evidence_completeness_rate"] == 0.5
    assert summary["average_turns"] == 2.25
    assert summary["average_tool_calls"] == 1.25
    assert summary["completion_rate"] == 0.5
    lost = summary["case_stability"]["lost"]
    assert lost["modal_tool_sequence"] == ["get_order", "track_shipment"]
    assert lost["modal_tool_call_count"] == 2
    assert lost["sequence_consistency"] == pytest.approx(2 / 3)
    assert lost["tool_count_consistency"] == pytest.approx(2 / 3)
    assert lost["completion_rate"] == pytest.approx(2 / 3)
    assert summary["mean_sequence_consistency"] == pytest.approx(5 / 6)
    assert summary["mean_tool_count_consistency"] == pytest.approx(5 / 6)
    assert summary["pending_runs"] == 4
    assert summary["conclusion_accuracy"] is None


def test_stability_modes_break_ties_independently_of_input_order():
    records = [
        make_record("lost", 1, ["track_shipment", "get_order"]),
        make_record("lost", 2, ["get_order"]),
    ]
    summary = summarize_shipping_stability(records)
    assert summary == summarize_shipping_stability(list(reversed(records)))
    case = summary["case_stability"]["lost"]
    assert case["modal_tool_sequence"] == ["get_order"]
    assert case["modal_tool_call_count"] == 1
    assert case["sequence_consistency"] == 0.5
    assert case["tool_count_consistency"] == 0.5


def test_stability_manual_reviews_match_run_ids_without_mutation():
    records = [make_record("lost", i, []) for i in (1, 2)]
    original = deepcopy(records)
    review = {
        "conclusion_correct": True,
        "internal_consistency": True,
        "unsupported_claims": False,
        "failure_types": [],
        "notes": "Human review",
    }
    reviewed = apply_manual_reviews(records, {"lost/run_02": review}, id_key="run_id")
    assert records == original
    assert reviewed[0] == records[0]
    assert reviewed[1]["manual_review"] == review
    assert all(a is not b for a, b in zip(records, reviewed))
    summary = summarize_shipping_stability(reviewed)
    assert summary["reviewed_runs"] == 1
    assert summary["pending_runs"] == 1
    assert summary["conclusion_accuracy"] == 1.0
    assert summary["unsupported_claim_free_rate"] == 1.0


def test_empty_stability_input():
    with pytest.raises(ValueError, match="empty experiment"):
        summarize_shipping_stability([])


def test_duplicate_run_ids_rejected():
    record = make_record("lost", 1, [])
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_shipping_stability([record, record])


@pytest.mark.parametrize(
    "field,value",
    [("tool_sequence", None), ("tool_sequence", [1]), ("tool_call_count", -1)],
)
def test_invalid_behavior_rejected(field, value):
    record = make_record("lost", 1, [])
    record["score"][field] = value
    with pytest.raises(TypeError):
        summarize_shipping_stability([record])


def test_experiment_preserves_twenty_independent_runs(tmp_path, monkeypatch, capsys):
    script = runpy.run_path("experiments/run_shipping_stability.py")
    clients = []

    def model_factory(*, model):
        assert model == "qwen3:4b-instruct"
        client = ScriptedModel(responses=[ModelResponse(content="Test answer")])
        clients.append(client)
        return client

    script["run_stability"](tmp_path / "results", model_factory)
    records = load_experiment_records(tmp_path / "results")
    assert len(clients) == len(records) == 20
    assert len({record["run_id"] for record in records}) == 20
    for record in records:
        order_id = record["order_id"]
        assert record["task"] == (
            f"A customer says order {order_id} is lost. "
            "Investigate the order using Northstar's records "
            "and tell me what is actually happening. "
            "Do not assume the customer's claim is correct."
        )
        assert record["seed"] == 42
        assert record["manual_review"] == {
            "conclusion_correct": None,
            "internal_consistency": None,
            "unsupported_claims": None,
            "failure_types": [],
            "notes": None,
        }
        assert record["trace"]["status"] == "completed"
    filenames = sorted(path.name for path in (tmp_path / "results").glob("*.json"))
    with pytest.raises(FileExistsError):
        script["run_stability"](tmp_path / "results", model_factory)
    assert (
        sorted(path.name for path in (tmp_path / "results").glob("*.json")) == filenames
    )
    assert len(clients) == 20

    report = runpy.run_path("experiments/summarize_shipping_stability.py")
    monkeypatch.setitem(
        report["main"].__globals__, "RESULT_DIRECTORY", tmp_path / "results"
    )
    reviews_path = tmp_path / "reviews.json"
    reviews_path.write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setitem(report["main"].__globals__, "REVIEW_PATH", reviews_path)
    report["main"]()
    output = capsys.readouterr().out
    assert "Total runs: 20" in output
    assert "Reviewed: 0; pending: 20" in output
    assert "Completion rate: 100.0%" in output
    assert (
        load_manual_reviews(Path("experiments/reviews/shipping_stability_v1.json"))
        == {}
    )
