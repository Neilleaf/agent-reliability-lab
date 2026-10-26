"""Consolidated saved-result reporting; never executes models or rewrites data."""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from agent_reliability_lab.evals.reporting import (
    apply_manual_reviews,
    load_experiment_records,
    load_manual_reviews,
    summarize_benchmark_records,
    summarize_shipping_records,
    summarize_shipping_stability,
)
from agent_reliability_lab.evals.security import summarize_security_records
from agent_reliability_lab.experiments import RESULT_NAMESPACES, definition_digest

HISTORY = {
    "shipping_baseline_v1": ("baseline", "historical shipping baseline V1"),
    "shipping_stability_v1": (
        "stability",
        "historical shipping stability V1 (earlier tool set)",
    ),
    "benchmark_v1": (
        "benchmark",
        "historical Benchmark V1, pre-QA requirements; rerun required",
    ),
    "security_v1": (
        "security",
        "saved Security V1 baseline; unchanged boundary policy",
    ),
}


def runtime_summary(records):
    runtimes = []
    for record in records:
        runtime = record.get("runtime")
        if runtime is None and isinstance(record.get("trace"), dict):
            runtime = record["trace"].get("runtime")
        if isinstance(runtime, dict):
            runtimes.append(runtime)
    durations = [
        runtime["duration_seconds"]
        for runtime in runtimes
        if isinstance(runtime.get("duration_seconds"), (int, float))
    ]
    model_times = [
        value
        for runtime in runtimes
        for value in runtime.get("model_call_durations_seconds", [])
    ]
    tool_times = [
        timing["duration_seconds"]
        for runtime in runtimes
        for timing in runtime.get("tool_call_timings", [])
    ]
    return {
        "instrumented_runs": len(durations),
        "total_runs": len(records),
        "average_duration_seconds": mean(durations) if durations else None,
        "total_duration_seconds": sum(durations) if durations else None,
        "average_model_call_seconds": mean(model_times) if model_times else None,
        "average_tool_call_seconds": mean(tool_times) if tool_times else None,
        "cost": "not_applicable/local",
        "tokens": "not measured",
    }


def collect_reports(
    root=Path("experiments/results"), reviews_root=Path("experiments/reviews")
):
    reports = []
    if not root.exists():
        return reports
    for directory in sorted(path for path in root.iterdir() if path.is_dir()):
        namespace = directory.name
        current_suite = next(
            (suite for suite, value in RESULT_NAMESPACES.items() if value == namespace),
            None,
        )
        if namespace not in HISTORY and current_suite is None:
            continue
        suite, label = HISTORY.get(
            namespace, (current_suite, f"{namespace}: current evaluation definition")
        )
        groups = defaultdict(list)
        paths = (
            [directory]
            if namespace in HISTORY
            else sorted(path for path in directory.iterdir() if path.is_dir())
        )
        for path in paths:
            for record in load_experiment_records(path):
                groups[(path, record.get("model", "unknown"))].append(record)
        for (path, model), records in groups.items():
            review_path = (
                reviews_root / f"{namespace}.json"
                if namespace in HISTORY
                else reviews_root / namespace / f"{path.name}.json"
            )
            if review_path.exists():
                records = apply_manual_reviews(
                    records,
                    load_manual_reviews(review_path),
                    id_key="order_id" if suite == "baseline" else "run_id",
                )
            summarizer = {
                "baseline": summarize_shipping_records,
                "stability": summarize_shipping_stability,
                "benchmark": summarize_benchmark_records,
                "security": summarize_security_records,
            }[suite]
            summary = summarizer(records)
            if suite == "baseline":
                from agent_reliability_lab.evals.benchmark import reliable_run

                summary["completion_rate"] = sum(
                    record["score"].get("status") == "completed" for record in records
                ) / len(records)
                summary["reliable_run_rate"] = sum(
                    reliable_run(record["score"]) for record in records
                ) / len(records)
            runtime = runtime_summary(records)
            reviewed = summary.get("reviewed_runs")
            if reviewed is None:
                reviewed = sum(
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
            report = {
                "namespace": namespace,
                "suite": suite,
                "label": label,
                "model": model,
                "directory": str(path),
                "runs": len(records),
                "summary": summary,
                "runtime": runtime,
                "reviewed": reviewed,
                "pending": len(records) - reviewed,
            }
            if current_suite:
                from agent_reliability_lab.evals.cases import build_benchmark_cases
                from agent_reliability_lab.evals.security import build_security_cases

                definitions = (
                    build_security_cases()
                    if suite == "security"
                    else build_benchmark_cases()
                )
                digests = {
                    case.case_id: definition_digest(case.model_dump(mode="json"))
                    for case in definitions
                }
                if suite == "stability":
                    definitions = [case for case in definitions if case.family == "S01"]
                expected_ids = {
                    f"{case.ground_truth['shipment_status'] if suite == 'stability' else case.case_id}/run_{repetition:02d}"
                    for case in definitions
                    for repetition in range(1, 6 if suite == "stability" else 2)
                }
                expected = len(expected_ids)
                report["expected_runs"] = expected
                report["complete"] = {
                    record.get("run_id") for record in records
                } == expected_ids
                report["revision_matches"] = all(
                    record.get("evaluation_revision") == namespace
                    and record.get("case_definition_sha256")
                    == digests.get(record.get("case_id"))
                    and record.get("case_definition_sha256")
                    == definition_digest(record.get("case_metadata", {}))
                    for record in records
                )
                if not report["revision_matches"]:
                    report["label"] = (
                        f"{namespace}: saved definitions differ from current code"
                    )
            if suite == "security":
                # Derive probe outcomes from saved calls; do not rescore or rewrite V1.
                outcomes = {}
                for record in records:
                    if record.get("attack_category") != "malformed_identifiers":
                        continue
                    calls = [
                        call
                        for message in record.get("trace", {}).get("messages", [])
                        if message.get("role") == "assistant"
                        for call in message.get("tool_calls", [])
                    ]
                    requirements = record.get("case_metadata", {}).get(
                        "required_evidence", []
                    )
                    exact = any(
                        call["name"] == item["tool"]
                        and call["arguments"] == item["arguments"]
                        for call in calls
                        for item in requirements
                    )
                    outcomes[record["case_id"]] = (
                        "lookup_not_attempted"
                        if not calls
                        else "identifier_substituted"
                        if not exact
                        else "exact_lookup_attempted"
                    )
                report["malformed_identifier_diagnosis"] = outcomes
            reports.append(report)
    return reports


def headline_findings(reports):
    findings = []
    for report in reports:
        summary = report["summary"]
        prefix = f"{report['namespace']} / {report['model']}"
        completion = summary.get("completion_rate")
        evidence = summary.get("evidence_completeness_rate")
        reliable = summary.get("reliable_run_rate")
        consistency = summary.get("mean_sequence_consistency")
        if completion is not None and evidence is not None and completion > evidence:
            findings.append(
                f"{prefix}: completion {completion:.1%} exceeds evidence completeness {evidence:.1%}."
            )
        if consistency is not None and reliable is not None and consistency > reliable:
            findings.append(
                f"{prefix}: sequence consistency {consistency:.1%} exceeds reliability {reliable:.1%}."
            )
        if (
            report["suite"] == "security"
            and summary.get("prohibited_action_attempt_rate") == 0
            and evidence < 1
        ):
            findings.append(
                f"{prefix}: no prohibited calls were attempted, while evidence completeness was {evidence:.1%}; this does not establish semantic safety."
            )
    return findings


def print_report(reports):
    print("AGENT RELIABILITY LAB - CONSOLIDATED REPORT")
    if not reports:
        print(
            "No saved experiment results found. Run from the repository root or set --results-root."
        )
    for report in reports:
        print(f"\n{report['label']}")
        print(
            f"  Model: {report['model']}; runs: {report['runs']}; directory: {report['directory']}"
        )
        if "complete" in report:
            print(
                f"  Expected runs: {report['expected_runs']}; complete: {report['complete']}; revision matches: {report['revision_matches']}"
            )
        summary = report["summary"]
        for key in (
            "completion_rate",
            "tool_selection_rate",
            "argument_accuracy_rate",
            "evidence_completeness_rate",
            "reliable_run_rate",
            "mean_sequence_consistency",
            "mean_tool_count_consistency",
            "security_pass_rate",
            "unknown_tool_attempt_rate",
            "prohibited_action_attempt_rate",
        ):
            if key in summary:
                print(f"  {key}: {summary[key]:.1%}")
        print(
            f"  Manual review: {report['reviewed']} reviewed / {report['pending']} pending"
        )
        print(
            f"  Average turns: {summary['average_turns']:.2f}; average tool calls: {summary['average_tool_calls']:.2f}"
        )
        for key in (
            "conclusion_accuracy",
            "internal_consistency_rate",
            "unsupported_claim_free_rate",
            "policy_violation_rate",
            "followed_user_bypass_instruction_rate",
        ):
            value = summary.get(key)
            if key in summary:
                print(
                    f"  {key}: {'pending' if value is None else format(value, '.1%')}"
                )
        for key in (
            "tool_errors",
            "unexpected_tool_calls",
            "unknown_tool_attempts",
            "prohibited_action_attempts",
            "malformed_call_failures",
            "successful_unavailable_actions",
        ):
            if key in summary:
                print(f"  {key}: {summary[key]}")
        if "malformed_identifier_diagnosis" in report:
            print(
                f"  Malformed identifier diagnosis: {report['malformed_identifier_diagnosis']}"
            )
        print(f"  Runtime: {report['runtime']}")
    print("\nHEADLINE FINDINGS (saved deterministic metrics)")
    for finding in headline_findings(reports):
        print(f"  - {finding}")


def export_report(path, reports):
    with path.open("x", encoding="utf-8") as handle:
        json.dump(
            {"experiments": reports, "headline_findings": headline_findings(reports)},
            handle,
            indent=2,
        )
