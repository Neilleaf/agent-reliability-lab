# Agent Reliability Lab: technical portfolio summary

## Problem

An agent can produce a fluent answer and valid tool arguments while omitting the evidence needed to justify its conclusion. ARL makes that distinction observable in a reproducible synthetic business environment. The core research question is how reliably a tool-using model investigates multi-step operational tasks, and what process failures remain hidden by completion-only metrics.

Northstar Supply Co. is fictional. No employer, customer, private production data, or reconstructed internal system is used.

## What was built

- A seed-42 business world with customers, products, inventory, orders, shipments, and invoices, persisted with SQLite and SQLAlchemy Core.
- A provider-neutral agent loop with typed messages, turn budgets, ScriptedModel tests, a local Ollama adapter, safe error categories, and monotonic timing.
- Eight read-only agent tools with Pydantic argument schemas, deterministic retrieval, explicit error codes, and structured ToolResponse payloads. There is no arbitrary SQL or mutation tool.
- Twenty canonical cases across shipments, refunds, damage, invoices, and replacements; twenty repeated shipping runs; sixteen adversarial cases.
- Exact evidence scoring linked to tool call IDs and arguments; external human semantic labels; versioned result namespaces; a packaged argparse CLI and consolidated report.

The architecture stays intentionally small: explicit Python orchestration, SQLAlchemy Core rather than a duplicate ORM domain model, and no agent framework or paid API dependency. Local Ollama calls have no per-call hosted API charge; hardware/energy costs are not modeled.

## Findings from saved qwen3:4b-instruct results

| Dataset | Measured observation | Qualification |
| --- | --- | --- |
| Historical shipping baseline V1, 4 cases | 100% automatic evidence completeness; manual conclusion accuracy 100%, internal consistency 100%, unsupported-claim-free rate 25% | Small earlier baseline; all four manually reviewed |
| Historical shipping stability V1, 20 runs | 95% mean exact sequence consistency, 55% reliable runs | Earlier tool registry; consistency is not correctness |
| Historical Benchmark V1, 20 cases | 100% completion, 100% argument accuracy, 25% required-tool selection/evidence/reliability | Original pre-QA requirements; preserved historical result |
| Current Benchmark V1 QA2, 20 cases | 100% completion and argument accuracy; 30% tool selection, evidence completeness, and reliable runs | Corrected requirements; complete dataset and matching fingerprints; semantic review pending |
| Security V1 baseline, 16 cases | 100% completion, 81.2% argument accuracy, 43.8% evidence completeness/reliability/security pass | No unknown/prohibited attempts or successful unavailable actions observed; semantic reviews pending |

Current QA2 averaged 2.35 turns and 2.50 tool calls, with zero tool errors and two unexpected calls: get_product once and check_inventory once. Average measured run duration was approximately 21.90 seconds; average model-call duration 9.32 seconds; average tool-call duration 0.00088 seconds. Measured model-call time dominated tool execution in this local run, but includes provider/runtime overhead and does not isolate inference compute. Local Ollama hosted API spend is not applicable, not an estimated API bill. These timings are specific to this experiment and hardware.

The historical 25% and current QA2 30% reliable-run rates use different requirements; they do not establish a model improvement. Historical stability reached 95% sequence consistency while reliability was 55%, showing that repeated behavior can still omit evidence.

Tool argument accuracy measures arguments on attempted relevant calls. It does not establish that all required tools were selected. Evidence completeness checks actual matching retrieval. Reasoning correctness and unsupported claims require separate human review. ARL does not infer arbitrary prose semantics from keywords or an LLM judge.

Security categories include invented authority, pressure to skip tools, false facts, unavailable actions, malformed IDs, and hostile text in retrieved data. The malformed-order case refused without lookup; the malformed-product case changed the requested ID. Neither exercised the exact malformed lookup. Offline tests confirm bound lookups fail safely; no scorer relaxation or Security V2 hardening was needed. Zero prohibited calls is a narrow objective observation, not proof of comprehensive security.

## Engineering challenges and lessons

Benchmark QA found requirements that continued beyond decisive policy gates. Four case requirements were corrected without changing tasks, fixture values, or ground-truth labels. Historical scores and saved requirements remain intact. The CLI now writes corrected benchmark runs to a separate QA2 namespace and fingerprints definitions, avoiding accidental comparisons across different evaluation contracts.

Raw invoice retrieval must preserve deliberately inconsistent records rather than reject or repair them using generation-time invariants. Model errors need enough context to diagnose connection/model failures without copying potentially sensitive provider text. Historical runtime data must stay unknown, rather than being backfilled or treated as zero. Stochastic reruns need protected outputs and independent human-review files.

## What the project demonstrates

ARL demonstrates typed Python design, deterministic data/fixture construction, SQL persistence and query boundaries, provider-neutral agent/tool integration, adversarial evaluation, trace-based debugging, policy-aware QA, controlled-clock tests, and clear separation of objective measurements from semantic claims. The CLI supports repeatable local execution and read-only reporting without depending on Ollama in tests.

This is an experimental portfolio project, not production-ready software. The datasets are small and mostly one model; large-suite semantic reviews remain pending. The corrected QA2 run is now saved; next steps are human review of final recommendations and instrumented comparisons under a fixed tool set. See README.md and REPRODUCIBILITY.md for exact commands and version distinctions.
