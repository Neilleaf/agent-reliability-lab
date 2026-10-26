"""QA audits policy inputs and all declared evidence against real fixture tools."""

from copy import deepcopy
from datetime import date

import pytest

from agent_reliability_lab.evals.benchmark import _contains
from agent_reliability_lab.evals.cases import (
    build_benchmark_cases,
    prepare_case_database,
)
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.synthetic.generator import generate_snapshot
from agent_reliability_lab.synthetic.policies import (
    damage_decision,
    get_policy,
    invoice_discrepancies,
    refund_decision,
    replacement_available,
)
from agent_reliability_lab.tools.registry import TOOL_REGISTRY, execute_tool

# These are business dependencies, not a list copied from model behavior.
DECISION_INPUTS = {
    "S01": {"get_order": "order identity/state", "track_shipment": "shipment state"},
    "S02": {
        "get_order": "return status",
        "get_invoice": "payment/refund state",
        "track_shipment": "delivery date",
        "get_policy": "refund rules",
    },
    "S03": {
        "get_order": "purchased item/return status",
        "get_invoice": "payment state",
        "track_shipment": "delivery window",
        "get_policy": "damage/refund rules",
        "get_product": "product eligibility",
        "check_inventory": "cross-warehouse replacement availability",
        "get_damage_report": "damage verification",
    },
    "S04": {
        "get_order": "authoritative totals",
        "get_invoice": "stored totals",
        "get_policy": "comparison rules",
    },
    "S05": {
        "get_product": "product eligibility",
        "check_inventory": "cross-warehouse availability",
        "get_policy": "replacement rules",
    },
}


def audit_decision(case, data):
    """Recompute policy outcomes and independently checked ground-truth facts.

    Product lookup and inventory both expose eligibility. Their agreement is an
    evidence-integrity check, not permission to discard a declared V1 lookup.
    """
    expected_policies = {
        "S01": [],
        "S02": ["refund"],
        "S03": ["damage", "refund"],
        "S04": ["invoice"],
        "S05": ["replacement"],
    }[case.family]
    if case.family == "S03" and not data["damage_report"]["verified"]:
        expected_policies = ["damage"]
    for policy in expected_policies:
        assert data[f"policy:{policy}"] == get_policy(policy)
    for key, response in data.items():
        if key.startswith("policy:"):
            assert response == get_policy(key.split(":")[1])
    if case.family == "S01":
        assert (
            data["order"]["order_id"]
            == data["shipment"]["order_id"]
            == case.entity_ids["order_id"]
        )
        return {
            "expected_decision": data["shipment"]["shipment_status"],
            "shipment_status": data["shipment"]["shipment_status"],
        }
    if case.family == "S04":
        mismatches = invoice_discrepancies(data["order"], data["invoice"])
        return {
            "discrepancies": mismatches,
            "expected_decision": "correct_discrepancy"
            if mismatches
            else "correct_invoice",
        }
    truth = {}
    if case.family == "S03" and not data["damage_report"]["verified"]:
        assert any(
            item["product_id"] == case.entity_ids["product_id"]
            for item in data["order"]["order_items"]
        )
        return {"expected_decision": "request_evidence", "damage_verified": False}
    if case.family in ("S02", "S03"):
        shipment = data.get("shipment", {})
        delivered = shipment.get("actual_delivery_date")
        refund = refund_decision(
            data["order"]["order_status"],
            shipment.get("shipment_status", "none"),
            date.fromisoformat(delivered) if delivered else None,
            data["invoice"]["payment_status"],
        )
        truth["expected_decision"] = refund
    if case.family in ("S03", "S05"):
        eligible = data["product"]["replacement_eligible"]
        if eligible:
            assert data["product"] == data["inventory"]["product"]
            stock = replacement_available(eligible, data["inventory"]["locations"])
            assert stock == data["inventory"]["replacement_available"]
        else:
            stock = False
        truth.update(replacement_available=stock, replacement_eligible=eligible)
        if case.family == "S03":
            in_order = any(
                item["product_id"] == case.entity_ids["product_id"]
                for item in data["order"]["order_items"]
            )
            verified = data["damage_report"]["verified"]
            truth.update(
                damage_verified=verified,
                expected_decision=damage_decision(
                    verified=verified,
                    product_in_order=in_order,
                    refund_outcome=refund,
                    can_replace=stock,
                ),
            )
        else:
            truth["expected_decision"] = "available" if stock else "unavailable"
    return truth


@pytest.mark.parametrize("index", range(20))
def test_case_requirements_are_possible_and_support_ground_truth(index, tmp_path):
    world = generate_snapshot(seed=42)
    case = build_benchmark_cases(world)[index]
    engine = create_database_engine(tmp_path / "qa.db")
    try:
        prepare_case_database(engine, world, case)
        evidence = {}
        for requirement in case.required_evidence:
            assert requirement.tool in DECISION_INPUTS[case.family]
            definition = TOOL_REGISTRY[requirement.tool]
            definition.argument_model.model_validate(requirement.arguments)
            for key, value in requirement.arguments.items():
                if key == "policy_id":
                    assert get_policy(value) is not None
                else:
                    assert case.entity_ids[key] == value
            response = execute_tool(engine, requirement.tool, requirement.arguments)
            assert response.status.value == "success"
            assert _contains(response.data, requirement.expected_data)
            if requirement.tool == "get_policy":
                evidence[f"policy:{requirement.arguments['policy_id']}"] = (
                    response.data["policy"]
                )
            elif requirement.tool == "check_inventory":
                evidence["inventory"] = response.data
            else:
                evidence.update(response.data)
        assert all(
            case.ground_truth[key] == value
            for key, value in audit_decision(case, evidence).items()
        )
        # Every requested evidence category supports a policy decision/input or
        # integrity check; deleting it must make a complete audit impossible.
        for category in evidence:
            incomplete = deepcopy(evidence)
            del incomplete[category]
            with pytest.raises((KeyError, AssertionError)):
                assert all(
                    case.ground_truth[key] == value
                    for key, value in audit_decision(case, incomplete).items()
                )
    finally:
        engine.dispose()


def test_qa_corrections_preserve_expected_outcomes_and_only_remove_irrelevant_checks():
    cases = {case.case_id: case for case in build_benchmark_cases()}
    assert "track_shipment" not in {
        item.tool for item in cases["S02_not_delivered"].required_evidence
    }
    assert (
        cases["S02_not_delivered"].ground_truth["expected_decision"] == "not_delivered"
    )
    assert {item.tool for item in cases["S03_unverified_damage"].required_evidence} == {
        "get_order",
        "get_policy",
        "get_damage_report",
    }
    assert cases["S03_unverified_damage"].ground_truth == {
        "expected_decision": "request_evidence",
        "replacement_available": True,
        "replacement_eligible": True,
        "damage_verified": False,
    }
    for case_id in ("S03_ineligible_product", "S05_ineligible_product"):
        assert "check_inventory" not in {
            item.tool for item in cases[case_id].required_evidence
        }
        assert cases[case_id].ground_truth["replacement_available"] is False
        assert cases[case_id].ground_truth["replacement_eligible"] is False
