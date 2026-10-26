# ARL Benchmark

The Agent Reliability Lab benchmark evaluates AI agents on synthetic business tasks with known ground truth.

See [Benchmark V1](BENCHMARK_V1.md) for the implemented 20-case suite, policies,
evidence requirements, metrics, failure taxonomy, and run commands.

See [Security V1](SECURITY_V1.md) for the 16-case adversarial suite and threat model.

## Scenario Families

| ID  | Scenario                 | Core Question                                               |
| --- | ------------------------ | ----------------------------------------------------------- |
| S01 | Late Shipment            | What happened to the shipment, and what should happen next? |
| S02 | Refund Request           | Is the customer eligible for a refund?                      |
| S03 | Damaged Product          | What resolution should be offered for damaged goods?        |
| S04 | Incorrect Invoice        | Does the invoice correctly reflect the underlying order?    |
| S05 | Out-of-Stock Replacement | Can an appropriate replacement actually be supplied?        |

## Scenario vs Task

A scenario family describes a type of business problem.

A benchmark task is one specific instance of that problem.

For example, the **Late Shipment** family may eventually generate tasks such as:

* shipment delayed but still in transit
* shipment marked delivered but customer disputes receipt
* shipment lost in transit
* replacement inventory available
* replacement inventory unavailable
* customer supplied an invalid order number

This allows a small number of scenario families to produce many distinct evaluation cases.
