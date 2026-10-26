import json
import runpy
from collections import Counter
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from agent_reliability_lab.agent.fake_model import ScriptedModel
from agent_reliability_lab.agent.models import (
    AgentMessage,
    AgentRunResult,
    AgentRunStatus,
    MessageRole,
    ModelResponse,
    ToolCall,
)
from agent_reliability_lab.agent.runner import AgentRunner
from agent_reliability_lab.evals.benchmark import reliable_run, score_benchmark_run
from agent_reliability_lab.evals.cases import (
    FAMILIES,
    build_benchmark_cases,
    prepare_case_database,
)
from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    summarize_benchmark_records,
    summarize_shipping_stability,
)
from agent_reliability_lab.retrieval.queries import get_damage_report, get_invoice
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.schema import damage_reports
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import REFERENCE_DATE, generate_snapshot
from agent_reliability_lab.synthetic.policies import (
    damage_decision,
    get_policy,
    invoice_discrepancies,
    refund_decision,
    replacement_available,
)
from agent_reliability_lab.tools.registry import execute_tool, get_tool_schema


@pytest.fixture(scope="module")
def world():
    return generate_snapshot(seed=42)


@pytest.fixture(scope="module")
def cases(world):
    return build_benchmark_cases(world)


@pytest.fixture
def engine(tmp_path):
    engine = create_database_engine(tmp_path / "case.db")
    yield engine
    engine.dispose()


@pytest.mark.parametrize(
    "days,outcome",
    [
        (-1, "outside_refund_window"),
        (0, "refund_eligible"),
        (30, "refund_eligible"),
        (31, "outside_refund_window"),
    ],
)
def test_refund_boundaries(days, outcome):
    assert (
        refund_decision(
            "delivered", "delivered", REFERENCE_DATE - timedelta(days=days), "paid"
        )
        == outcome
    )


@pytest.mark.parametrize(
    "order,shipment,payment,outcome",
    [
        ("cancelled", "none", "refunded", "already_refunded"),
        ("cancelled", "none", "paid", "cancelled_no_return_refund"),
        ("shipped", "in_transit", "paid", "not_delivered"),
        ("delivered", "delivered", "unpaid", "no_paid_amount_to_refund"),
    ],
)
def test_refund_requires_delivery_payment_and_no_duplicate(
    order, shipment, payment, outcome
):
    assert refund_decision(order, shipment, REFERENCE_DATE, payment) == outcome
    assert (
        refund_decision("delivered", "delivered", None, "paid")
        == "delivery_evidence_required"
    )


@pytest.mark.parametrize(
    "eligible,locations,expected",
    [
        (True, [{"quantity_available": 2, "quantity_reserved": 2}], False),
        (
            True,
            [
                {"quantity_available": 2, "quantity_reserved": 2},
                {"quantity_available": 3, "quantity_reserved": 2},
            ],
            True,
        ),
        (False, [{"quantity_available": 3, "quantity_reserved": 0}], False),
        (True, [], False),
    ],
)
def test_replacement_eligibility_and_usable_inventory(eligible, locations, expected):
    assert replacement_available(eligible, locations) is expected


@pytest.mark.parametrize(
    "verified,in_order,refund,stock,expected",
    [
        (True, True, "refund_eligible", True, "replace"),
        (True, True, "refund_eligible", False, "refund"),
        (False, True, "refund_eligible", True, "request_evidence"),
        (True, False, "refund_eligible", True, "request_evidence"),
        (True, True, "outside_refund_window", True, "deny"),
    ],
)
def test_damage_policy(verified, in_order, refund, stock, expected):
    assert (
        damage_decision(
            verified=verified,
            product_in_order=in_order,
            refund_outcome=refund,
            can_replace=stock,
        )
        == expected
    )


def test_policies_are_independent_and_machine_readable():
    policy = get_policy("refund")
    policy["window_days"] = 999
    assert get_policy("refund")["window_days"] == 30
    assert get_policy("unknown") is None
    assert get_policy("damage")["requires_verified_damage_report"] is True


def test_case_construction_is_deterministic_and_does_not_mutate(world, cases):
    original = world.model_dump(mode="json")
    again = build_benchmark_cases(world)
    assert [c.model_dump(mode="json") for c in cases] == [
        c.model_dump(mode="json") for c in again
    ]
    assert [c.model_dump(mode="json") for c in cases] == [
        c.model_dump(mode="json") for c in build_benchmark_cases()
    ]
    assert world.model_dump(mode="json") == original
    assert len({c.case_id for c in cases}) == 20
    assert Counter(c.family for c in cases) == {family: 4 for family in FAMILIES}
    for case in cases:
        assert case.ground_truth["expected_decision"]
        assert case.required_evidence
        assert all(get_tool_schema(e.tool) is not None for e in case.required_evidence)


def scripted_evidence(case, *, missing=None, wrong=None, extra=False):
    calls = [
        ToolCall(
            call_id=f"call-{index}",
            name=item.tool,
            arguments={
                **item.arguments,
                **({next(iter(item.arguments)): "WRONG"} if index == wrong else {}),
            },
        )
        for index, item in enumerate(case.required_evidence)
        if index != missing
    ]
    if extra:
        calls.append(
            ToolCall(
                call_id="extra",
                name="get_customer",
                arguments={"customer_id": "CUS-00100"},
            )
        )
    return ScriptedModel(
        [
            ModelResponse(tool_calls=calls),
            ModelResponse(content="This text is intentionally not scored."),
        ]
    )


@pytest.mark.parametrize("index", range(20))
def test_every_fixture_has_consistent_evidence_and_scores_complete(
    index, world, cases, engine
):
    case = cases[index]
    prepare_case_database(engine, world, case)
    result = AgentRunner(engine=engine, model=scripted_evidence(case)).run(case.task)
    score = score_benchmark_run(result, case)
    assert score["missing_evidence"] == []
    assert score["tool_errors"] == []
    assert score["reliable_run"] is True
    assert score["automatic_failure_types"] == []
    if case.family == "S04":
        order = next(
            item.expected_data["order"]
            for item in case.required_evidence
            if item.tool == "get_order"
        )
        invoice = get_invoice(engine, case.entity_ids["order_id"])
        assert (
            invoice_discrepancies(order, invoice) == case.ground_truth["discrepancies"]
        )
    if case.family == "S03":
        assert (
            get_damage_report(engine, **case.entity_ids)["verified"]
            is case.ground_truth["damage_verified"]
        )


def test_invoice_discrepancy_cases_have_explicit_expected_mismatches(cases):
    assert {
        case.case_id: case.ground_truth["discrepancies"]
        for case in cases
        if case.family == "S04"
    } == {
        "S04_correct_invoice": [],
        "S04_inflated_subtotal": ["subtotal", "total"],
        "S04_shipping_discrepancy": ["shipping_charge", "total"],
        "S04_tax_total_discrepancy": ["tax", "internal_total"],
    }


def test_fixtures_are_isolated_and_general_world_remains_clean(world, cases, engine):
    case = next(c for c in cases if c.case_id == "S03_no_stock")
    prepare_case_database(engine, world, case)
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(damage_reports)) == 1
    seed_database(engine, world)
    with engine.connect() as connection:
        assert connection.scalar(select(func.count()).select_from(damage_reports)) == 0
    for invoice in world.invoices:
        if invoice.order_id == case.entity_ids["order_id"]:
            assert get_invoice(engine, invoice.order_id) == invoice.model_dump(
                mode="json"
            )


@pytest.mark.parametrize(
    "tool,args,error",
    [
        ("get_product", {"product_id": "P9999"}, "PRODUCT_NOT_FOUND"),
        ("get_invoice", {"order_id": "ORD-99999"}, "INVOICE_NOT_FOUND"),
        ("get_policy", {"policy_id": "unknown"}, "POLICY_NOT_FOUND"),
        (
            "get_damage_report",
            {"order_id": "ORD-99999", "product_id": "P9999"},
            "DAMAGE_REPORT_NOT_FOUND",
        ),
    ],
)
def test_new_tools_errors_validation_and_schemas(tool, args, error, engine, world):
    seed_database(engine, world)
    assert execute_tool(engine, tool, args).error_code == error
    assert execute_tool(engine, tool, {}).error_code == "INVALID_TOOL_ARGUMENTS"
    assert (
        execute_tool(engine, tool, {**args, "extra": True}).error_code
        == "INVALID_TOOL_ARGUMENTS"
    )
    assert (
        execute_tool(engine, tool, {key: [] for key in args}).error_code
        == "INVALID_TOOL_ARGUMENTS"
    )
    schema = get_tool_schema(tool)
    assert schema["name"] == tool
    assert set(schema["parameters"]["required"]) == set(args)
    assert schema["parameters"]["additionalProperties"] is False


@pytest.mark.parametrize(
    "missing,wrong,extra", [(0, None, False), (None, 0, False), (None, None, True)]
)
def test_scorer_missing_wrong_and_unexpected_tools(
    missing, wrong, extra, world, cases, engine
):
    case = cases[4]
    prepare_case_database(engine, world, case)
    result = AgentRunner(
        engine=engine,
        model=scripted_evidence(case, missing=missing, wrong=wrong, extra=extra),
    ).run(case.task)
    score = score_benchmark_run(result, case)
    if missing is not None:
        assert score["tool_selection_pass"] is False
        assert "tool_selection_failure" in score["automatic_failure_types"]
    if wrong is not None:
        assert score["argument_accuracy_pass"] is False
        assert score["tool_errors"] == ["ORDER_NOT_FOUND"]
        assert "invalid_tool_arguments" in score["automatic_failure_types"]
    if extra:
        assert score["unexpected_tool_calls"] == ["get_customer"]
        # The requested four-condition definition doesn't exclude extra read tools.
        assert score["reliable_run"] is True
    else:
        assert score["evidence_complete"] is False
        assert score["reliable_run"] is False


def test_scorer_rejects_uncorrelated_wrong_or_missing_payload(cases, world, engine):
    case = cases[0]
    prepare_case_database(engine, world, case)
    result = AgentRunner(engine=engine, model=scripted_evidence(case)).run(case.task)
    for mutation in ("uncorrelated", "wrong_entity", "malformed", "empty"):
        altered = result.model_copy(deep=True)
        message = next(m for m in altered.messages if m.role == MessageRole.TOOL)
        if mutation == "uncorrelated":
            message.tool_call_id = "absent"
        elif mutation == "wrong_entity":
            payload = json.loads(message.content)
            payload["data"]["order"]["order_id"] = "ORD-99999"
            message.content = json.dumps(payload)
        else:
            message.content = (
                "invalid"
                if mutation == "malformed"
                else json.dumps({"status": "success", "data": {}})
            )
        assert score_benchmark_run(altered, case)["evidence_complete"] is False
    # A different prose conclusion cannot change any deterministic metric.
    altered = result.model_copy(deep=True)
    altered.final_answer = "Completely different prose"
    assert score_benchmark_run(altered, case) == score_benchmark_run(result, case)


@pytest.mark.parametrize(
    "failed_field",
    ["status", "tool_selection_pass", "argument_accuracy_pass", "evidence_complete"],
)
def test_reliable_run_requires_all_four_conditions(failed_field):
    score = {
        "status": "completed",
        "tool_selection_pass": True,
        "argument_accuracy_pass": True,
        "evidence_complete": True,
    }
    assert reliable_run(score)
    score[failed_field] = "model_error" if failed_field == "status" else False
    assert not reliable_run(score)


def test_benchmark_reporting_and_manual_reviews_do_not_mutate():
    good = {
        "status": "completed",
        "tool_selection_pass": True,
        "argument_accuracy_pass": True,
        "evidence_complete": True,
        "turns": 2,
        "tool_call_count": 2,
        "tool_errors": [],
        "unexpected_tool_calls": [],
    }
    bad = {
        **good,
        "status": "model_error",
        "evidence_complete": False,
        "tool_errors": ["UNKNOWN_TOOL"],
        "unexpected_tool_calls": ["oops"],
    }
    records = [
        {"case_id": "one", "run_id": "one/run_01", "family": "S01", "score": good},
        {"case_id": "two", "run_id": "two/run_01", "family": "S02", "score": bad},
    ]
    original = deepcopy(records)
    reviewed = apply_manual_reviews(
        records,
        {
            "one/run_01": {
                "conclusion_correct": True,
                "internal_consistency": True,
                "unsupported_claims": False,
            }
        },
        id_key="run_id",
    )
    summary = summarize_benchmark_records(reviewed)
    assert records == original
    assert summary["cases"] == 2
    assert summary["completion_rate"] == summary["reliable_run_rate"] == 0.5
    assert summary["by_family"]["S01"]["reliable_run_rate"] == 1.0
    assert summary["by_family"]["S02"]["reliable_run_rate"] == 0.0
    assert summary["tool_errors"] == {"UNKNOWN_TOOL": 1}
    assert summary["unexpected_tool_calls"] == {"oops": 1}
    assert summary["incomplete_evidence_count"] == 1
    assert summary["reviewed_runs"] == summary["pending_runs"] == 1
    assert (
        summary["conclusion_accuracy"]
        == summary["internal_consistency_rate"]
        == summary["unsupported_claim_free_rate"]
        == 1.0
    )
    with pytest.raises(ValueError, match="empty"):
        summarize_benchmark_records([])
    with pytest.raises(ValueError, match="Duplicate"):
        summarize_benchmark_records([records[0], records[0]])


def test_high_shipping_consistency_can_have_zero_reliability():
    records = [
        {
            "case": "delayed",
            "run_id": f"delayed/run_{i}",
            "score": {
                "tool_sequence": [],
                "tool_call_count": 0,
                "turns": 1,
                "status": "completed",
                "tool_selection_pass": False,
                "argument_accuracy_pass": True,
                "evidence_complete": False,
            },
        }
        for i in range(5)
    ]
    summary = summarize_shipping_stability(records)
    assert summary["mean_sequence_consistency"] == 1.0
    assert summary["completion_rate"] == 1.0
    assert summary["reliable_run_rate"] == 0.0
    assert summary["case_stability"]["delayed"]["reliable_run_rate"] == 0.0


def test_benchmark_runner_and_report_without_ollama(
    tmp_path, monkeypatch, capsys, cases
):
    script = runpy.run_path("experiments/run_benchmark_v1.py")
    clients = []

    def factory(*, model):
        assert model == "qwen3:4b-instruct"
        client = scripted_evidence(cases[len(clients) % len(cases)])
        clients.append(client)
        return client

    output = tmp_path / "results"
    script["run_benchmark"](output, factory)
    records = load_experiment_records(output)
    assert len(records) == len(clients) == 20
    assert all(record["score"]["reliable_run"] for record in records)
    assert len({record["run_id"] for record in records}) == 20
    assert all(
        record["manual_review"]["conclusion_correct"] is None for record in records
    )
    names = sorted(path.name for path in output.iterdir())
    with pytest.raises(FileExistsError):
        script["run_benchmark"](output, factory)
    assert sorted(path.name for path in output.iterdir()) == names
    report = runpy.run_path("experiments/summarize_benchmark_v1.py")
    monkeypatch.setitem(report["main"].__globals__, "RESULT_DIRECTORY", output)
    review_path = tmp_path / "reviews.json"
    review_path.write_text("{}", encoding="utf-8")
    monkeypatch.setitem(report["main"].__globals__, "REVIEW_PATH", review_path)
    report["main"]()
    text = capsys.readouterr().out
    assert "Total cases: 20" in text
    assert "Reviewed: 0; pending: 20" in text
    assert "Reliable runs: 100.0%" in text
    assert all(f"{family} {name}" in text for family, name in FAMILIES.items())


def test_failed_run_still_has_score(cases):
    for status in (AgentRunStatus.MODEL_ERROR, AgentRunStatus.MAX_TURNS_REACHED):
        result = AgentRunResult(
            status=status,
            final_answer=None,
            messages=[AgentMessage(role=MessageRole.USER, content="Task")],
            turns=1,
            tool_call_count=0,
        )
        score = score_benchmark_run(result, cases[0])
        assert score["reliable_run"] is False
        assert status.value in score["automatic_failure_types"]


def test_invoice_comparison_uses_decimal_money():
    order = {"subtotal": "0.10", "shipping_charge": "0.20", "tax": "0.00"}
    invoice = {**order, "total": "0.30"}
    assert invoice_discrepancies(order, invoice) == []
    invoice["total"] = Decimal("0.31")
    assert invoice_discrepancies(order, invoice) == ["total", "internal_total"]


def test_damage_can_gather_evidence_sequentially_with_runner_budget(
    world, cases, engine
):
    case = next(case for case in cases if case.case_id == "S03_replace")
    prepare_case_database(engine, world, case)
    responses = [
        ModelResponse(
            tool_calls=[
                ToolCall(
                    call_id=f"call-{index}", name=item.tool, arguments=item.arguments
                )
            ]
        )
        for index, item in enumerate(case.required_evidence)
    ]
    responses.append(ModelResponse(content="Final response for human review."))
    result = AgentRunner(
        engine=engine, model=ScriptedModel(responses), max_turns=10
    ).run(case.task)
    assert result.turns == 9
    assert score_benchmark_run(result, case)["reliable_run"] is True


def test_one_policy_lookup_cannot_satisfy_two_policies(world, cases, engine):
    case = next(case for case in cases if case.case_id == "S03_replace")
    prepare_case_database(engine, world, case)
    missing = next(
        index
        for index, item in enumerate(case.required_evidence)
        if item.arguments == {"policy_id": "damage"}
    )
    result = AgentRunner(
        engine=engine, model=scripted_evidence(case, missing=missing)
    ).run(case.task)
    score = score_benchmark_run(result, case)
    assert score["tool_selection_pass"] is True
    assert score["evidence_complete"] is False
    assert score["missing_evidence"] == [
        {"tool": "get_policy", "arguments": {"policy_id": "damage"}}
    ]


def test_reporting_recomputes_reliability_instead_of_trusting_saved_label():
    record = {
        "case_id": "case",
        "family": "S01",
        "case": "lost",
        "run_id": "case/run_01",
        "score": {
            "status": "completed",
            "tool_selection_pass": False,
            "argument_accuracy_pass": True,
            "evidence_complete": False,
            "reliable_run": True,
            "turns": 1,
            "tool_call_count": 0,
            "tool_sequence": [],
        },
    }
    assert summarize_benchmark_records([record])["reliable_run_rate"] == 0.0
    assert summarize_shipping_stability([record])["reliable_run_rate"] == 0.0
