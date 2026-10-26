import json
from itertools import count

import pytest

from agent_reliability_lab import cli
from agent_reliability_lab.agent.fake_model import ScriptedModel
from agent_reliability_lab.agent.model import ModelClientError
from agent_reliability_lab.agent.models import (
    AgentRunResult,
    AgentRunStatus,
    ModelResponse,
    ToolCall,
)
from agent_reliability_lab.agent.runner import AgentRunner
from agent_reliability_lab.evals.cases import (
    build_benchmark_cases,
    prepare_case_database,
)
from agent_reliability_lab.evals.security import (
    build_security_cases,
    score_security_run,
)
from agent_reliability_lab.experiments import (
    model_slug,
    result_directory,
    run_experiment,
)
from agent_reliability_lab.report import (
    collect_reports,
    headline_findings,
    runtime_summary,
)
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.synthetic.generator import generate_snapshot


def test_controlled_timing_on_success_and_tool_call(tmp_path):
    engine = create_database_engine(tmp_path / "timing.db")
    clock = count(0, 1).__next__
    model = ScriptedModel(
        [
            ModelResponse(
                tool_calls=[
                    ToolCall(call_id="unknown", name="unknown_tool", arguments={})
                ]
            ),
            ModelResponse(content="Done"),
        ]
    )
    try:
        result = AgentRunner(engine=engine, model=model, clock=clock).run("Task")
        assert result.runtime.duration_seconds == 7
        assert result.runtime.model_call_durations_seconds == [1, 1]
        assert result.runtime.tool_call_timings[0].duration_seconds == 1
        assert result.runtime.cost == "not_applicable/local"
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "message,expected",
    [
        ("Connection refused; token=SECRET", "connection"),
        ("model not found; api_key=SECRET", "not found"),
        ("HTTP failure credential=SECRET", "provider response"),
    ],
)
def test_error_details_are_classified_without_echoing_sensitive_text(
    tmp_path, message, expected
):
    class FailingModel:
        def generate(self, messages, tools):
            raise ModelClientError(message)

    engine = create_database_engine(tmp_path / "error.db")
    try:
        result = AgentRunner(
            engine=engine, model=FailingModel(), clock=count().__next__
        ).run("Task")
        assert result.status == AgentRunStatus.MODEL_ERROR
        assert expected in result.model_error.lower()
        assert "SECRET" not in result.model_dump_json()
        assert result.runtime.model_call_durations_seconds == [1]
        assert result.runtime.duration_seconds == 3
    finally:
        engine.dispose()


def test_historical_results_parse_without_runtime_fields():
    result = AgentRunResult.model_validate(
        {
            "status": "completed",
            "final_answer": "ok",
            "messages": [],
            "turns": 1,
            "tool_call_count": 0,
        }
    )
    assert result.runtime is None
    assert result.model_error is None
    assert (
        runtime_summary([{"trace": result.model_dump()}])["average_duration_seconds"]
        is None
    )


def test_model_paths_are_distinct_and_contained(tmp_path):
    assert model_slug("a:b") != model_slug("a/b")
    assert (
        result_directory("benchmark", "../../evil:model", tmp_path)
        .resolve()
        .is_relative_to(tmp_path.resolve())
    )
    assert "benchmark_v1_qa2" in str(result_directory("benchmark", "a"))


@pytest.mark.parametrize("command", ["benchmark", "security", "stability"])
def test_cli_dispatches_model_and_output_without_network(
    command, tmp_path, monkeypatch
):
    calls = []
    monkeypatch.setattr(
        cli, "run_experiment", lambda *args, **kwargs: calls.append((args, kwargs))
    )
    cli.main([command, "--model", "test:local", "--output-dir", str(tmp_path)])
    assert calls == [((command, tmp_path), {"model": "test:local"})]


def test_cli_summary_and_world_summary_do_not_call_models(tmp_path, capsys):
    cli.main(["world-summary"])
    assert "seed 42" in capsys.readouterr().out
    cli.main(
        [
            "summary",
            "--results-root",
            str(tmp_path / "empty"),
            "--json",
            str(tmp_path / "report.json"),
        ]
    )
    assert json.loads((tmp_path / "report.json").read_text())["experiments"] == []
    assert "No saved experiment" in capsys.readouterr().out


def test_parameterized_execution_persists_runtime_and_refuses_overwrite(
    tmp_path, monkeypatch
):
    case = build_benchmark_cases()[0]
    from agent_reliability_lab import experiments

    monkeypatch.setattr(experiments, "build_benchmark_cases", lambda world: [case])
    models = []

    def factory(*, model):
        models.append(model)
        return ScriptedModel([ModelResponse(content="Done")])

    output = tmp_path / "benchmark_v1_qa2" / model_slug("test:local")
    run_experiment("benchmark", output, factory, model="test:local")
    record = json.loads(next(output.glob("*.json")).read_text())
    assert models == ["test:local"]
    assert record["runtime"]["duration_seconds"] >= 0
    assert record["evaluation_revision"] == "benchmark_v1_qa2"
    assert record["case_definition_sha256"]
    original = next(output.glob("*.json")).read_bytes()
    with pytest.raises(FileExistsError):
        run_experiment("benchmark", output, factory, model="other:local")
    assert next(output.glob("*.json")).read_bytes() == original
    reports = collect_reports(tmp_path)
    assert reports[0]["model"] == "test:local"
    assert reports[0]["complete"] is False
    assert reports[0]["runtime"]["instrumented_runs"] == 1
    assert reports[0]["revision_matches"] is True
    record["case_definition_sha256"] = "outdated"
    next(output.glob("*.json")).write_text(json.dumps(record), encoding="utf-8")
    assert collect_reports(tmp_path)[0]["revision_matches"] is False


def test_malformed_cases_distinguish_avoidance_and_identifier_substitution(tmp_path):
    world = generate_snapshot(seed=42)
    cases = {case.security_case_id: case for case in build_security_cases(world)}
    engine = create_database_engine(tmp_path / "identifiers.db")
    try:
        order = cases["SEC_malformed_order"]
        prepare_case_database(engine, world, order)
        result = AgentRunner(
            engine=engine, model=ScriptedModel([ModelResponse(content="No lookup")])
        ).run(order.task)
        assert (
            score_security_run(result, order)["malformed_identifier_outcome"]
            == "lookup_not_attempted"
        )
        product = cases["SEC_malformed_product"]
        prepare_case_database(engine, world, product)
        result = AgentRunner(
            engine=engine,
            model=ScriptedModel(
                [
                    ModelResponse(
                        tool_calls=[
                            ToolCall(
                                call_id="changed",
                                name="get_product",
                                arguments={"product_id": "P1007"},
                            )
                        ]
                    ),
                    ModelResponse(content="Changed ID"),
                ]
            ),
        ).run(product.task)
        score = score_security_run(result, product)
        assert score["malformed_identifier_outcome"] == "identifier_substituted"
        assert score["reliable_run"] is False
    finally:
        engine.dispose()


def test_headlines_are_derived_from_metrics():
    reports = [
        {
            "namespace": "test",
            "suite": "stability",
            "model": "fake",
            "summary": {
                "completion_rate": 1.0,
                "evidence_completeness_rate": 0.5,
                "mean_sequence_consistency": 1.0,
                "reliable_run_rate": 0.5,
            },
        }
    ]
    findings = headline_findings(reports)
    assert len(findings) == 2
    assert all("50.0%" in item for item in findings)
