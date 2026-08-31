# Agent Reliability Lab

Agent Reliability Lab (ARL) is an experimental framework for studying how reliably AI agents complete multi-step tasks using external tools.

The project evaluates not only whether an agent reaches the correct final answer, but also how it gets there: which tools it selects, what evidence it gathers, whether it follows business rules, how consistently it behaves, what it costs, and whether adversarial instructions can manipulate it.

ARL uses a completely fictional company and entirely synthetic data.

## Status

🚧 **Week 1 — Environment and benchmark design**

Current work:

* defining the synthetic company environment
* designing benchmark scenario families
* establishing evaluation principles
* preparing the project architecture

No LLM agent has been implemented yet.

## Research Question

**How reliably can modern AI agents complete multi-step business tasks using tools, and which architectural choices improve accuracy, security, efficiency, and cost?**

## Initial Benchmark Areas

The first version of the benchmark will evaluate agents on scenarios involving:

* late shipments
* refund requests
* damaged products
* invoice disputes
* out-of-stock replacements

These scenarios will run inside a fictional business called **Northstar Supply Co.**

## What ARL Will Measure

Planned metrics include:

* task success
* tool-selection accuracy
* tool-argument accuracy
* evidence completeness
* unsupported claims
* policy compliance
* forbidden actions
* tool-call count
* token usage
* latency
* inference cost
* prompt-injection attack success rate

## Project Principles

ARL is designed around several principles:

1. Evaluate agent behaviour, not just final answers.
2. Prefer deterministic scoring when objective ground truth exists.
3. Keep benchmark data reproducible.
4. Preserve failures rather than hiding them.
5. Separate user claims from system ground truth.
6. Use only original code, synthetic data, public documentation, and appropriately licensed resources.

## Current Structure

```text
agent-reliability-lab/
├── benchmark/
│   └── README.md
├── docs/
│   └── NORTHSTAR_SPEC.md
├── src/
│   └── agent_reliability_lab/
├── tests/
├── PROJECT_SPEC.md
├── README.md
└── pyproject.toml
```

## Development

Install project dependencies:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Check formatting:

```bash
uv run ruff format --check .
```

## Documentation

See:

* [`PROJECT_SPEC.md`](PROJECT_SPEC.md) — project goals, evaluation philosophy, and six-week scope
* [`docs/NORTHSTAR_SPEC.md`](docs/NORTHSTAR_SPEC.md) — synthetic company and business-rule specification
* [`benchmark/README.md`](benchmark/README.md) — initial benchmark scenario families

## Data and IP

All business data used by Agent Reliability Lab is synthetic and created specifically for this project.

The repository will not contain confidential employer information, internal company code, proprietary datasets, customer information, or reconstructed internal systems.

## Project Goal

By the end of the six-week build, ARL should provide a reproducible environment for comparing tool-using AI agents across reliability, security, cost, latency, and consistency.
