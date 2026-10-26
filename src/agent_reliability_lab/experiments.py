"""Shared local experiment execution; historical outputs are read-only inputs."""

import hashlib
import json
import re
from collections.abc import Callable
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_reliability_lab.agent.model import ModelClient
from agent_reliability_lab.agent.ollama_model import OllamaModelClient
from agent_reliability_lab.agent.runner import AgentRunner
from agent_reliability_lab.evals.benchmark import score_benchmark_run
from agent_reliability_lab.evals.cases import (
    build_benchmark_cases,
    prepare_case_database,
)
from agent_reliability_lab.evals.security import (
    build_security_cases,
    score_security_run,
)
from agent_reliability_lab.evals.shipping import score_shipping_run
from agent_reliability_lab.storage.database import create_database_engine
from agent_reliability_lab.storage.seeder import seed_database
from agent_reliability_lab.synthetic.generator import generate_snapshot

DEFAULT_MODEL = "qwen3:4b-instruct"
RESULT_NAMESPACES = {
    "benchmark": "benchmark_v1_qa2",
    "security": "security_v1_instrumented",
    "stability": "shipping_stability_v1_instrumented",
}
REVIEW_FIELDS = ("conclusion_correct", "internal_consistency", "unsupported_claims")


def model_slug(model: str) -> str:
    label = re.sub(r"[^a-zA-Z0-9_-]+", "-", model).strip("-")[:48] or "model"
    return f"{label}-{hashlib.sha256(model.encode()).hexdigest()[:12]}"


def definition_digest(metadata: dict[str, object]) -> str:
    return hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()


def result_directory(
    suite: str, model: str, root: Path = Path("experiments/results")
) -> Path:
    return root / RESULT_NAMESPACES[suite] / model_slug(model)


def manual_placeholder(security: bool = False) -> dict[str, object]:
    fields = (
        (*REVIEW_FIELDS, "policy_violation", "followed_user_bypass_instruction")
        if security
        else REVIEW_FIELDS
    )
    return {**dict.fromkeys(fields), "failure_types": [], "notes": None}


def _save(directory, filename, record):
    # Exclusive creation guards against overwrites even after the initial check.
    with (directory / filename).open("x", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)


def run_experiment(
    suite: str,
    output_directory: Path | None = None,
    model_factory: Callable[..., ModelClient] = OllamaModelClient,
    *,
    model: str = DEFAULT_MODEL,
    engine_factory=None,
) -> Path:
    directory = (
        output_directory
        if output_directory is not None
        else result_directory(suite, model)
    )
    directory.mkdir(parents=True, exist_ok=True)
    if any(directory.glob("*.json")):
        raise FileExistsError(
            f"Results already exist in {directory}. Choose a new --output-dir; archive traces and reviews together."
        )
    world = generate_snapshot(seed=42)
    cases = (
        build_security_cases(world)
        if suite == "security"
        else build_benchmark_cases(world)
    )
    if suite == "stability":
        cases = [case for case in cases if case.family == "S01"]
    repetitions = 5 if suite == "stability" else 1
    max_turns = 8 if suite == "stability" else 10
    print(
        f"Running {len(cases) * repetitions} {suite} agent runs with {model}; at most {len(cases) * repetitions * max_turns} model calls.",
        flush=True,
    )
    print(f"Results: {directory}", flush=True)
    with TemporaryDirectory(dir=directory) as temporary_directory:
        engine = (
            engine_factory()
            if engine_factory
            else create_database_engine(Path(temporary_directory) / "northstar.db")
        )
        try:
            if suite == "stability":
                seed_database(engine, world)
            for case in cases:
                if suite != "stability":
                    prepare_case_database(engine, world, case)
                for repetition in range(1, repetitions + 1):
                    status = case.ground_truth.get("shipment_status")
                    run_id = f"{status if suite == 'stability' else case.case_id}/run_{repetition:02d}"
                    print(f"Running {run_id}", flush=True)
                    runner = AgentRunner(
                        engine=engine,
                        model=model_factory(model=model),
                        max_turns=max_turns,
                    )
                    result = runner.run(case.task)
                    if suite == "stability":
                        score = score_shipping_run(
                            result,
                            expected_order_id=case.entity_ids["order_id"],
                            expected_shipment_status=status,
                        )
                    else:
                        score = (
                            score_security_run(result, case)
                            if suite == "security"
                            else score_benchmark_run(result, case)
                        )
                    metadata = case.model_dump(mode="json")
                    record = {
                        "run_id": run_id,
                        "case_id": case.case_id,
                        "family": case.family,
                        "model": model,
                        "seed": 42,
                        "task": case.task,
                        "suite": suite,
                        "evaluation_revision": RESULT_NAMESPACES[suite],
                        "case_definition_sha256": definition_digest(metadata),
                        "case_metadata": metadata,
                        "ground_truth": case.ground_truth,
                        "score": score,
                        "final_answer": result.final_answer,
                        "trace": result.model_dump(mode="json"),
                        "runtime": result.runtime.model_dump(mode="json"),
                        "model_error": result.model_error,
                        "manual_review": manual_placeholder(suite == "security"),
                    }
                    if suite == "security":
                        record.update(
                            security_case_id=case.security_case_id,
                            attack_category=case.attack_category,
                        )
                    if suite == "stability":
                        record.update(
                            case=status,
                            order_id=case.entity_ids["order_id"],
                            repetition=repetition,
                        )
                    filename = (
                        f"{status}_run_{repetition:02d}.json"
                        if suite == "stability"
                        else f"{case.case_id}.json"
                    )
                    _save(directory, filename, record)
                    if result.model_error:
                        print(f"  MODEL_ERROR: {result.model_error}", flush=True)
        finally:
            engine.dispose()
    return directory


def run_benchmark(
    output_directory=None, model_factory=OllamaModelClient, *, model=DEFAULT_MODEL
):
    return run_experiment("benchmark", output_directory, model_factory, model=model)


def run_security(
    output_directory=None, model_factory=OllamaModelClient, *, model=DEFAULT_MODEL
):
    return run_experiment("security", output_directory, model_factory, model=model)


def run_stability(
    output_directory=None,
    model_factory=OllamaModelClient,
    *,
    model=DEFAULT_MODEL,
    engine_factory=None,
):
    return run_experiment(
        "stability",
        output_directory,
        model_factory,
        model=model,
        engine_factory=engine_factory,
    )
