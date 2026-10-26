# Reproduce ARL locally (Windows PowerShell)

Use Python 3.12+ and uv, and run commands from the repository root. The dependency lock is uv.lock. All Northstar business data is synthetic. Live runs need a running Ollama server and an installed model; tests, generation, and reporting do not.

## Setup and offline checks

```powershell
uv sync
uv run ruff format .
uv run ruff check .
uv run python -m pytest
uv run ruff format --check .
uv run arl world-summary
uv run arl seed
uv run arl summary
```

The seed command resets only the synthetic local SQLite world. DB files are ignored by Git. Benchmark/security runs seed private isolated fixture databases; stability uses the same seed-42 world for every fresh client/runner. The snapshot assessment date is fixed at 2026-08-31. These choices make data/cases reproducible, not stochastic model responses or elapsed time.

## Ollama prerequisite

Start `ollama serve` in another PowerShell window unless the Ollama service is already running. Then:

```powershell
ollama pull qwen3:4b-instruct
ollama list
```

A stopped server produces MODEL_ERROR with a safe connection category in new traces. Model-not-found and provider errors have separate safe categories. Raw provider messages, URLs, credentials, environment values, and stack traces are not persisted in model_error.

## Saved QA2 results and optional reproduction runs

1. **Optional reproduction of the now-saved current QA2 benchmark:**

```powershell
uv run arl benchmark --model qwen3:4b-instruct
```

The current QA2 run is already saved: 20 cases, 100% completion and argument accuracy, and 30% tool selection/evidence completeness/reliable runs, with semantic review pending. The older 25% result remains historical pre-QA. This command would execute another 20 cases, up to 200 model calls, but its default output folder now exists and is protected. For an intentional reproduction, use a fresh --output-dir as shown below; a new run is not needed merely to report the saved QA2 result.

2. **Optional to obtain current timing and tool-set stability:**

```powershell
uv run arl stability --model qwen3:4b-instruct
```

This executes 20 runs, up to 160 model calls. Its expanded registry differs from the earlier shipping-only stability baseline. Compare within the same contract/tool environment.

3. **Optional to obtain security timing with the unchanged V1 boundary policy:**

```powershell
uv run arl security --model qwen3:4b-instruct
```

This executes 16 cases, up to 160 model calls. No ID-format hardening occurred, so Security V2 is not required. Existing 43.8% Security V1 results remain a valid saved baseline.

4. **Read-only report:**

```powershell
uv run arl summary
uv run arl summary --json report.json
```

The console entry point is installed by uv sync; `uv run python -m agent_reliability_lab.cli summary` is equivalent. The existing run_benchmark_v1.py, run_security_v1.py, and run_shipping_stability.py scripts delegate to the same packaged runners and accept --model / --output-dir.

## Results, fingerprints, and repeat runs

Defaults are experiments/results/<namespace>/<model-label-and-hash>/*.json. Namespaces:

- benchmark_v1_qa2: corrected requirements, 20 cases.
- security_v1_instrumented: unchanged V1 evidence/security contract, 16 cases.
- shipping_stability_v1_instrumented: 20 repetitions with current tools/timing.

All files contain model, seed, task, trace, automatic score, null human placeholder, evaluation revision, and case-definition SHA-256. New runtime captures agent duration, individual model-call durations (including model failures), tool-call durations, turns, call count, and local cost classification. Durations use perf_counter and do not represent CPU/GPU utilization, tokens, hosted cost, or throughput benchmarks.

Existing JSON causes a refusal before any model call. To intentionally repeat, keep the namespace and choose a new result-folder name:

```powershell
uv run arl benchmark --model qwen3:4b-instruct --output-dir experiments/results/benchmark_v1_qa2/qwen-repeat-02
```

The consolidated report discovers model groups under known namespaces, checks revision/fingerprint compatibility, and labels partial datasets. Custom output directories outside that structure are valid runner destinations but are not auto-discovered by the report. Use --results-root to relocate the overall results tree, not a single case folder. JSON report export also refuses overwrite. No default command overwrites historical result namespaces.

## Human reviews

For a result folder named <folder>, place an external object at experiments/reviews/<namespace>/<folder>.json. Match its entries to run_id, not case/order IDs alone. Fill only reviewed labels. For example:

```json
{
  "S02_valid_refund/run_01": {
    "conclusion_correct": null,
    "internal_consistency": null,
    "unsupported_claims": null,
    "failure_types": [],
    "notes": null
  }
}
```

Security adds policy_violation and followed_user_bypass_instruction. Three boolean labels are needed for a business reviewed count, five for security. Individual rates use available boolean labels independently. Historical flat review paths remain supported. Archive traces and reviews together; deterministic IDs do not imply identical model answers on a rerun.

The older summarize_* scripts still inspect their historical flat directories. Use arl summary for new model-specific datasets. No live experiment is part of pytest or was executed during this polish sprint.
