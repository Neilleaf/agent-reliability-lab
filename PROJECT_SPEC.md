# Agent Reliability Lab

## Project Overview

Agent Reliability Lab (ARL) is an experimental framework for studying how reliably AI agents complete multi-step tasks using external tools.

Most AI demonstrations focus on whether a model produces a convincing final answer. ARL instead evaluates the full behaviour of an agent:

* what information it retrieves
* which tools it chooses
* whether it supplies correct tool arguments
* whether it gathers enough evidence before acting
* whether it invents unsupported information
* whether it follows business policies
* how consistently it performs
* how much time and money it consumes
* whether adversarial instructions can manipulate it

The project will use a completely fictional company and entirely synthetic data.

## Primary Research Question

**How reliably can modern AI agents complete multi-step business tasks using tools, and which architectural choices improve accuracy, security, efficiency, and cost?**

## Initial Research Questions

ARL will investigate questions such as:

1. What are the most common failure modes of tool-using AI agents?
2. How often does an agent select the correct tool?
3. How often does it call the correct tool with incorrect arguments?
4. Does the agent gather enough evidence before reaching a conclusion?
5. How consistent is the agent when the same task is repeated?
6. How do different models compare on reliability, cost, and latency?
7. How vulnerable are agents to prompt injection contained in external data?
8. Can permission controls improve security without significantly reducing legitimate task success?

## Fictional Company

The benchmark will initially simulate a fictional B2B distributor called **Northstar Supply Co.**

Northstar sells workplace and industrial equipment.

The synthetic environment will eventually contain:

* customers
* products
* orders
* order items
* warehouses
* inventory
* shipments
* invoices
* support tickets
* company policies

## Initial Scenario Families

The first version of the benchmark will focus on five business problems.

### 1. Late Shipment

A customer reports that an order has not arrived.

The agent may need to inspect:

* the customer
* the order
* shipment tracking
* delivery dates
* company policy
* replacement inventory

### 2. Refund Request

A customer asks for a refund.

The agent must determine:

* what was purchased
* when it was purchased
* why the customer wants a refund
* which refund policy applies
* whether the refund is permitted

### 3. Damaged Product

A customer reports receiving damaged goods.

The agent must inspect the order and determine the appropriate replacement, refund, or escalation.

### 4. Incorrect Invoice

A customer believes an invoice contains an error.

The agent must compare the invoice with the underlying order and determine whether a discrepancy actually exists.

### 5. Out-of-Stock Replacement

A customer needs a replacement product.

The agent must determine whether inventory is available and avoid promising stock that does not exist.

## Evaluation Philosophy

ARL will evaluate both **outcomes and process**.

Where objective ground truth exists, deterministic evaluation will be preferred over asking another LLM to judge the answer.

Potential metrics include:

* task success
* tool-selection accuracy
* tool-argument accuracy
* evidence completeness
* unsupported-claim rate
* policy compliance
* forbidden-action rate
* number of tool calls
* token usage
* latency
* estimated inference cost
* prompt-injection attack success rate

## Initial Failure Taxonomy

Agent failures may include:

* wrong tool selected
* incorrect tool arguments
* insufficient evidence
* premature conclusion
* unsupported claim
* policy violation
* forbidden action
* excessive tool use
* failure to recover from a tool error
* prompt-injection compromise

This taxonomy may change as real failures are observed.

## Six-Week Goal

By the end of six weeks, ARL should contain:

* a synthetic enterprise environment
* a tool-using baseline agent
* an automated evaluation runner
* approximately 100–150 standard benchmark tasks
* an adversarial benchmark
* deterministic and semantic scorers
* a documented failure taxonomy
* MCP-compatible tools
* experiments across multiple models
* repeatability analysis
* cost and latency analysis
* a results dashboard
* reproducible experiments
* a technical report

## Data and IP Policy

Agent Reliability Lab is an independent personal project.

The project will use only:

* original code written specifically for ARL
* synthetic data generated specifically for ARL
* public libraries
* public documentation
* appropriately licensed public resources where necessary

The project will not contain confidential employer information, internal company code, internal APIs, internal documentation, customer data, proprietary datasets, or reconstructed proprietary systems.

## Definition of Success

The project is successful if it produces credible, reproducible evidence about how AI agents succeed and fail.

A visually impressive demo is useful, but measurable engineering and research findings take priority.
