# Northstar Benchmark V1

## Diagnostics and QA checkpoint

Reports now show required/observed/missing tools and evidence, status, errors,
unexpected calls, and reliable_run for failed cases only. Per-family omissions
count each tool once per case, sorted by frequency. Missing a specific policy
is visible as `policy:refund` even when another `get_policy` call was made.
Diagnostics reconstruct historical traces using the case metadata saved with
that run. They never replace saved scores or substitute current requirements.
Legacy records without metadata show unavailable diagnostics explicitly.

QA executes every declared lookup, validates its arguments against the registry,
checks IDs against metadata, matches actual fixture responses, recomputes policy
ground truth, and verifies that each evidence category supports a decision/input
or evidence-integrity check. Independent product and inventory eligibility facts
are cross-checked when both are relevant. No final-answer prose is scored.

QA found four cases with requirements beyond a decisive policy gate. Current QA2
case definitions omit tracking for `S02_not_delivered`, downstream
refund/product/inventory lookups for `S03_unverified_damage`, and inventory for
`S03_ineligible_product` and `S05_ineligible_product`. An unverified damage claim
needs order-item evidence, damage verification, and damage policy; an ineligible
product cannot become replacement-available by changing stock. These changes
correct evidence necessity, not model behavior. Tasks, fixture values, expected
decisions, and other ground-truth fields are unchanged. Auxiliary fixture facts
can remain in ground truth without requiring irrelevant downstream lookups.
Historical results retain their original requirements and 25% reliable-run rate.
The current QA2 dataset is now complete: 20 qwen3:4b-instruct cases with matching
definition fingerprints, 100% completion, 30% required-tool selection, 100%
argument accuracy, 30% evidence completeness, and 30% reliable runs. Manual
semantic review remains pending for all 20 cases. Average turns were 2.35 and
tool calls 2.50; tool errors were zero, with get_product and check_inventory
each called unexpectedly once.

Measured averages were approximately 21.90 s per run, 9.32 s per model call,
and 0.00088 s per tool call. Model-call timing dominated tool execution here;
it includes provider/runtime overhead and does not isolate inference compute.
Local Ollama hosted API spend is not applicable. Do not compare the historical
25% and QA2 30% as identical evaluation contracts or infer semantic correctness
from these process metrics.

See [Security V1](SECURITY_V1.md) for the separate adversarial suite.

V1 contains 20 deterministic cases built from seed 42, four per family.
`src/agent_reliability_lab/evals/cases.py` declares typed case metadata, ground
truth, required evidence, and explicit fixture changes. The general generator
is unchanged. Each case runs against a freshly seeded private SQLite database;
fixtures never change the normal Northstar database or other cases.

| Family | Cases | Authoritative evidence |
| --- | --- | --- |
| S01 Shipment | lost, delayed, in transit, delivered | Order and shipment records |
| S02 Refund | valid, outside window, not delivered, cancelled and already refunded | Order, invoice payment status, refund policy, delivery evidence when relevant |
| S03 Damaged Product | replace, no usable stock, ineligible product, unverified damage | Order items, shipment, paid invoice, product, all inventory locations, damage report, refund and damage policies |
| S04 Incorrect Invoice | correct, inflated subtotal/total, shipping discrepancy, tax/internal-total discrepancy | Order, raw invoice, invoice policy |
| S05 Replacement | stock available, fully reserved everywhere, ineligible product, one location without usable stock | Product eligibility, all inventory locations, replacement policy |

The same delivered order/product may appear in multiple isolated fixtures.
Case IDs include family and variant; they never depend on timestamps. S01 keeps
the existing baseline tasks and shipment selection. New tasks contain customer
claims but never expose ground truth or fixture changes to the model.

## Policies and environment

`synthetic/policies.py` holds machine-readable policy records and small pure
decision functions. `get_policy` returns a copy, including the fixed assessment
date **2026-08-31**, never the execution date.

- Ordinary return refunds require a paid delivered order and shipment, with an
  actual delivery date between 0 and 30 days before assessment, inclusive.
  Future or missing delivery dates cannot establish eligibility. Shipped orders
  are not ordinary returns. Cancelled orders and already-refunded payments must
  not be refunded again. The cancelled fixture deliberately includes a refunded
  invoice as evidence of a previous payment reversal.
- Damage claims require a verified order/product damage report and a product in
  the order. Within refund eligibility, prefer replacement if the product permits
  it and usable inventory exists; otherwise refund. Unverified claims require
  evidence; outside policy conditions, deny. Damage reports are a minimal added
  table, empty in ordinary seeded worlds and populated only by explicit fixtures.
- Invoice components must match the order, and invoice total must also equal its
  own subtotal plus shipping plus tax. Retrieval returns raw stored values,
  including inconsistent totals; it does not repair them or apply the synthetic
  Invoice model's generation-time consistency validator. Money uses Decimal.
- Usable inventory is available minus reserved. Replacement availability requires
  product eligibility and positive usable quantity at any warehouse. V1 asks
  about one replacement unit, not shipment allocation, reservation, or approval.
  Ineligible products remain unavailable even with physical stock. One empty
  warehouse cannot establish that there is no stock anywhere.

The product lookup reuses existing retrieval. New agent tools are `get_product`,
`get_invoice`, `get_policy`, and `get_damage_report`; all use the existing validated
registry and ToolResponse contract. Agents never receive SQL access.

## Automatic and human metrics

All families share one evidence scorer, driven by case declarations. It measures
required tool selection, exact argument accuracy, successful evidence retrieval,
unexpected calls, tool errors, completion, turns, and tool count. Evidence must
match the expected case data and correlate with the preceding call ID, tool
name, and arguments. Multiple policy lookups are distinct evidence requirements.
Money in expected records is normalized to SQLite's two-decimal representation.

A **reliable run** means all four of these hold:

1. Runner status is `completed`.
2. Required tool selection passed.
3. Argument accuracy passed.
4. Evidence is complete.

Reports recompute reliability from these fields rather than trusting a cached
`reliable_run` label. Extra tools and errors are reported separately; they are
not additional conditions in this four-condition definition. Scores retain a
list of missing evidence and automatically detectable failure categories.

This is process reliability. Successful retrieval does not prove a correct
interpretation, policy-compliant recommendation, or supported final answer.
Expected decisions are explicit ground truth for review, not automatic claims
about arbitrary prose. No keyword matching or semantic LLM judge is used.

Human labels live in `experiments/reviews/benchmark_v1.json`, keyed by run ID:

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

The initial file is empty. Fill boolean fields only after human review. A run is
reviewed when all three booleans are present; each manual rate independently
uses available boolean labels. Generated traces contain null placeholders and
are never the authoritative source of human labels. Summary applies external
reviews without mutating loaded records.

User claims are not ground truth: a refund may be ineligible, an alleged
overcharge may match the order exactly, or a claimed stock outage may apply to
only one location. Fixture records and retrieved policies are authoritative.

## Stability versus reliability

Shipping stability compares exact tool-name sequences and call counts across
repetitions. Modal ties use lexical sequence order or the smallest count.
Case consistency means the fraction sharing the mode. Overall consistency is
an equal-weight mean over cases; reliability is the fraction of all runs passing
the four conditions. Stability output includes per-case and overall reliability.

A case can repeatedly omit required evidence: 100% consistency and 0%
reliability. Neither metric automatically establishes semantic correctness.
Historical shipping results remain unchanged, even though future runs now see
the expanded registry. Compare results with awareness of this tool-set change.

## Failure taxonomy

| Category | Detection |
| --- | --- |
| tool_selection_failure | Automatic: required tool absent |
| invalid_tool_arguments | Automatic: argument accuracy fails or validation rejects arguments |
| incomplete_evidence | Automatic: required successful, case-matching evidence absent |
| unexpected_tool | Automatic: called tool outside the case's required set |
| tool_error | Automatic: error response or malformed response |
| max_turns_reached | Automatic: runner exhausts turn budget |
| model_error | Automatic: runner reports model failure |
| evidence_misinterpretation | Human semantic review |
| self_contradiction | Human semantic review |
| unsupported_inference | Human semantic review |
| unsupported_causal_attribution | Human semantic review |
| unsupported_operational_claim | Human semantic review |
| unsupported_recommendation | Human semantic review |
| policy_violation | Human semantic review |

## Running and reviewing

From the repository root, with local Ollama serving `qwen3:4b-instruct`:

```text
uv run arl benchmark --model qwen3:4b-instruct
uv run arl summary
```

The benchmark starts 20 independent agent runs, each with a fresh model client
and runner. It allows ten model turns per case (up to 200 generate calls); damage
cases can require eight separate evidence calls plus a final response. The
existing system prompt is unchanged. No live runs are part of unit tests.

New output is `experiments/results/benchmark_v1_qa2/<model-folder>/<case_id>.json`, including case
metadata, fixture changes, task, model, seed, ground truth, score, final answer,
complete trace, and the manual-review placeholder. Temporary databases are
created and removed inside this output directory. Partial results can be
summarized. Existing JSON is protected; choose a fresh output folder for another
run. Historical pre-QA results remain unchanged. New external reviews live at
`experiments/reviews/benchmark_v1_qa2/<model-folder>.json`. See
[reproducibility](../docs/REPRODUCIBILITY.md) for current paths and commands.
