# Shipping Stability V1

Run from the repository root:

```text
uv run arl stability --model qwen3:4b-instruct
uv run arl summary
```

The experiment uses seed 42, qwen3:4b-instruct, the unchanged baseline task,
and the existing runner with max_turns=8. Each of four statuses has five runs,
with a fresh model client and runner each time. The seeded world is shared;
the current tools only read it. Model randomness is left at adapter defaults.

Historical files remain in experiments/results/shipping_stability_v1. New timed
runs use shipping_stability_v1_instrumented/<model-folder> as lost_run_01.json,
etc. IDs remain lost/run_01. Existing JSON is protected; use a fresh folder for a repeat. Model errors and exhausted turns remain recorded and count as
incomplete. Completion means runner status completed, not semantic correctness.

Historical reviews use experiments/reviews/shipping_stability_v1.json. New reviews
use experiments/reviews/shipping_stability_v1_instrumented/<model-folder>.json:

```json
{
  "lost/run_01": {
    "conclusion_correct": null,
    "internal_consistency": null,
    "unsupported_claims": null,
    "failure_types": [],
    "notes": null
  }
}
```

Replace null boolean fields only after human review. The initial review file is
empty. A run counts as reviewed when all three boolean fields are filled;
individual manual rates use available boolean labels, as in the baseline.
Reviews match run_id, never order_id. Rerunning does not modify this file:
archive or clear old labels before rerunning so they do not label new traces.

Sequence consistency is the fraction sharing the exact modal ordered tool-name
sequence (including repeated or failed calls). Count consistency is the fraction
sharing the modal tool-call count. Ties choose the lexicographically smallest
sequence or smallest count. Overall stability is the unweighted mean of case
consistencies; reliability and completion rates use all runs as the denominator.
Reports display actual runs per case, including partial experiments.
No semantic correctness is inferred from keywords or completion.
