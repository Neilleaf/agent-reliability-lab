# Experiment 0 — First Unscripted Agent Run

## Configuration

* Model: `qwen3:4b-instruct`
* Runtime: Ollama local
* Northstar seed: `42`
* Task family: shipment investigation
* Order: `ORD-00043`
* Ground-truth shipment status: `lost`

## Task

A customer says order ORD-00043 is lost. Investigate the order using Northstar's records and tell me what is actually happening. Do not assume the customer's claim is correct.

## Observed Tool Sequence

1. `get_order({"order_id": "ORD-00043"})`
2. `track_shipment({"order_id": "ORD-00043"})`

## Run Metrics

* Turns: 2
* Tool calls: 2
* Invalid tool calls: 0
* Tool errors: 0

## Evaluation

* Tool selection: PASS
* Tool argument accuracy: PASS
* Evidence completeness: PASS
* Ground-truth conclusion: FAIL
* Internal consistency: FAIL
* Unsupported claims: FAIL

## Primary Failure

`evidence_misinterpretation`

The agent correctly retrieved a shipment whose authoritative status was `lost`, but concluded that the customer's claim that the order was lost was inaccurate.

## Secondary Failure

`unsupported_causal_attribution`

The response stated that the carrier reported the shipment lost and implied that Northstar was not responsible, although neither claim was established by the retrieved evidence.

## Key Finding

Correct tool use and sufficient evidence do not guarantee a correct final conclusion.

This run motivates evaluating agent reasoning separately from tool-selection accuracy.
