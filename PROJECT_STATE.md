# Agent Reliability Lab — Current Project State

## Current Milestone

**Day 3 — SQLite persistence and retrieval foundation**

The synthetic Northstar environment has been built and validated.

The current task is to persist the generated world into SQLite and then expose deterministic retrieval functions that will later become agent tools.

---

## Project Goal

Agent Reliability Lab (ARL) is an experimental framework for studying how reliably AI agents complete multi-step business tasks using external tools.

The project evaluates both final outcomes and process quality, including:

* tool selection
* tool arguments
* evidence gathering
* unsupported claims
* policy compliance
* consistency
* cost
* latency
* prompt-injection resistance

All business data is synthetic.

No employer, customer, proprietary, or confidential data is used.

---

# Environment

## Python

* Python 3.12.1
* Project-managed virtual environment
* `uv` used for dependency and environment management

## Development Tools

* pytest
* Ruff

## Current Runtime Dependencies

* Pydantic
* Faker
* SQLAlchemy

---

# Version Control

The project is tracked with Git.

A private GitHub repository has been created and linked as the remote repository.

Current branch:

`master`

Changes are committed and pushed at the end of completed development milestones.

---

# Current Repository Structure

```text
agent-reliability-lab/
│
├── benchmark/
│   └── README.md
│
├── docs/
│   └── NORTHSTAR_SPEC.md
│
├── src/
│   └── agent_reliability_lab/
│       │
│       ├── __init__.py
│       │
│       ├── synthetic/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── generator.py
│       │   └── summary.py
│       │
│       └── storage/
│           ├── __init__.py
│           ├── database.py
│           └── schema.py
│
├── tests/
│   ├── test_smoke.py
│   ├── test_models.py
│   ├── test_generator.py
│   ├── test_snapshot.py
│   └── test_database.py
│
├── PROJECT_SPEC.md
├── PROJECT_STATE.md
├── README.md
├── pyproject.toml
└── uv.lock
```

---

# Synthetic Company

The benchmark environment simulates a fictional B2B distributor:

**Northstar Supply Co.**

Northstar sells workplace and light industrial equipment.

---

# Synthetic Data Model

The following domain models currently exist using Pydantic.

## Customers

Fields include:

* customer ID
* company name
* contact name
* email
* account status
* customer tier
* billing address
* shipping address
* date created

Customer tiers:

* standard
* business
* enterprise

Account statuses:

* active
* suspended

---

## Products

Fields include:

* product ID
* product name
* category
* unit price
* active status
* replacement eligibility

Product categories:

* safety equipment
* tools
* office equipment
* storage equipment
* electrical accessories

---

## Warehouses

Three warehouses currently exist:

* `WH-NORTH`
* `WH-CENTRAL`
* `WH-SOUTH`

---

## Inventory

Inventory exists for every product at every warehouse.

Fields include:

* warehouse ID
* product ID
* quantity available
* quantity reserved

Usable inventory is:

`quantity_available - quantity_reserved`

Validation prevents:

`quantity_reserved > quantity_available`

---

## Orders

Each order references a real customer.

Order fields include:

* order ID
* customer ID
* order date
* order status
* shipping address
* billing address
* order items
* subtotal
* shipping charge
* tax
* total amount

Order statuses:

* pending
* confirmed
* processing
* shipped
* delivered
* cancelled

Each order contains between 1 and 4 distinct active products.

Each item contains:

* product ID
* quantity
* unit price at purchase
* line total

Validation ensures:

`line_total = quantity × unit_price`

Order validation ensures:

`subtotal = sum(order item line totals)`

and:

`total_amount = subtotal + shipping_charge + tax`

---

## Shipments

Only orders with status:

* shipped
* delivered

receive shipment records.

Shipment fields include:

* shipment ID
* order ID
* carrier
* tracking reference
* shipped date
* expected delivery date
* actual delivery date
* shipment status

Shipment statuses:

* label_created
* in_transit
* delayed
* delivered
* lost
* returned_to_sender

Delivered shipments require an actual delivery date.

Lost shipments cannot have an actual delivery date.

---

## Invoices

Invoices are generated for orders except:

* pending
* cancelled

Invoice fields include:

* invoice ID
* order ID
* issue date
* subtotal
* shipping charge
* tax
* total
* payment status

Payment statuses currently generated:

* paid
* unpaid

Invoices currently match their underlying orders exactly.

This provides a clean baseline before deliberately introducing invoice-dispute benchmark cases.

---

## Support Tickets

The SupportTicket model exists, but support tickets are not yet generated.

Current snapshot:

`support_tickets = []`

---

# Reproducibility

The synthetic world is generated using seeded pseudo-random generation.

Canonical benchmark seed:

`42`

The same seed generates the same Northstar world.

Different seeds generate different valid worlds.

Faker provides realistic-looking synthetic values such as:

* names
* company names
* email addresses
* addresses

Python's seeded `Random` determines:

* customer tiers
* product states
* order states
* inventory
* selected products
* shipment outcomes
* payment status

Generation works offline after dependencies are installed.

---

# Canonical Northstar Snapshot — Seed 42

Current generated world:

* 100 customers
* 50 products
* 3 warehouses
* 150 inventory records
* 400 orders
* 260 shipments
* 353 invoices
* 0 support tickets

---

# Observed Seed-42 Distribution

## Customer Tiers

* Standard: 67
* Business: 23
* Enterprise: 10

## Customer Account Status

* Active: 93
* Suspended: 7

## Products

* 50 total
* 50 active
* 0 discontinued

This is valid but may later be changed deliberately to guarantee discontinued-product benchmark cases.

## Orders

* Delivered: 136
* Shipped: 124
* Confirmed: 48
* Processing: 45
* Pending: 26
* Cancelled: 21

## Order Value

* Average: approximately $2,449.11
* Minimum: approximately $55.93
* Maximum: approximately $6,615.49

The values are plausible for a B2B distributor, though pricing may be revisited later.

## Shipments

* Delivered: 136
* In transit: 68
* Delayed: 32
* Lost: 17
* Returned to sender: 7

## Invoice Payment Status

* Paid: 234
* Unpaid: 119

## Inventory

* Average usable units: approximately 25.7
* Zero usable inventory records: 9
* Positive usable inventory records: 141

## Customer Activity

* Customers with orders: 95
* Customers without orders: 5

---

# Temporal Consistency

The synthetic world uses:

`REFERENCE_DATE = 2026-08-31`

Historical events are prevented from occurring after the reference date.

The following are guaranteed not to exceed the reference date:

* order dates
* shipped dates
* actual delivery dates
* invoice issue dates

Expected future delivery dates may legitimately extend beyond the reference date.

Additional world-level tests verify that:

* shipment dates are chronologically valid
* actual delivery cannot precede shipping
* no historical event occurs after the snapshot date

---

# Synthetic Data Validation Layers

The project currently uses several defensive layers.

## Layer 1 — Generator Logic

Generation functions attempt to create internally coherent data.

## Layer 2 — Pydantic Validation

Domain models validate record-level invariants.

Examples:

* reserved inventory cannot exceed available inventory
* order item totals must be correct
* order totals must reconcile
* invoice totals must reconcile
* delivered shipments require delivery dates

## Layer 3 — World-Level Tests

Tests validate relationships across records.

Examples:

* all orders reference real customers
* all order items reference real products
* all shipments reference real orders
* shipped/delivered orders have shipments
* delivered orders have delivered shipments
* invoices match orders
* pending and cancelled orders do not receive invoices
* chronology is valid
* generation is reproducible

## Layer 4 — Database Constraints

SQLite persistence is now being introduced.

Foreign-key constraints will enforce relationships at the database level.

---

# Current Database Design

SQLite is used as the local persistence layer.

SQLAlchemy Core is used instead of ORM classes.

This avoids duplicating the Pydantic business models with a second set of Python model classes.

The SQLite database will live at:

`data/northstar.db`

SQLite foreign keys are explicitly enabled with:

`PRAGMA foreign_keys=ON`

---

# Current SQL Tables

The SQLAlchemy schema currently defines:

* customers
* products
* warehouses
* inventory
* orders
* order_items
* shipments
* invoices
* support_tickets

---

# Current Database Relationships

```text
CUSTOMERS
    │
    ▼
ORDERS
    │
    ├──► ORDER_ITEMS ───► PRODUCTS
    │
    ├──► SHIPMENTS
    │
    └──► INVOICES

WAREHOUSES
    │
    └──► INVENTORY ◄─── PRODUCTS
```

Foreign keys currently include relationships such as:

* orders → customers
* order items → orders
* order items → products
* shipments → orders
* invoices → orders
* inventory → warehouses
* inventory → products
* support tickets → customers
* support tickets → orders

---

# Database Tests

Current database tests verify:

1. All expected tables are created.
2. SQLite rejects an order referencing a customer that does not exist.

A test initially failed because a SQLAlchemy `Date` column was passed a string:

`"2026-08-01"`

This was corrected to use:

`date(2026, 8, 1)`

The test now correctly reaches the foreign-key constraint.

---

# Current Test Status

Latest known test state:

**23 tests passing**

Test modules:

* smoke tests
* model validation tests
* synthetic generator tests
* world snapshot tests
* database tests

Latest checks:

```text
pytest: passing
ruff check: passing
ruff format: passing
```

---

# Benchmark Scenario Families

Five initial benchmark scenario families are defined.

## S01 — Late Shipment

Core question:

What happened to the shipment, and what should happen next?

Potential states include:

* delayed
* lost
* delivered
* in transit
* replacement available
* replacement unavailable

---

## S02 — Refund Request

Core question:

Is the customer eligible for a refund?

---

## S03 — Damaged Product

Core question:

What resolution should be offered for damaged goods?

---

## S04 — Incorrect Invoice

Core question:

Does the invoice correctly reflect the underlying order?

---

## S05 — Out-of-Stock Replacement

Core question:

Can an appropriate replacement actually be supplied?

---

# Important Benchmark Principle

User claims are not treated as ground truth.

Example:

Customer says:

> "My shipment is lost."

The database may show:

`shipment_status = delayed`

The future agent must retrieve evidence before reaching a conclusion.

This principle will be central to evaluating agent reliability.

---

# Current Architecture Decisions

The following decisions are intentional and should not be changed casually.

## Python

Use Python 3.12 for project compatibility.

## Dependency Management

Use `uv`.

## Domain Models

Use Pydantic.

## Synthetic Generation

Use Faker and seeded Python random generation.

## Benchmark Seed

Use seed `42` as the canonical Northstar world unless a benchmark requires otherwise.

## Persistence

Use SQLite.

## Database Abstraction

Use SQLAlchemy Core rather than ORM classes.

## Data Policy

Use only:

* original code
* synthetic data
* public documentation
* appropriately licensed public resources

Never use proprietary employer or customer data.

## Evaluation Philosophy

Prefer deterministic evaluation when objective ground truth is available.

Do not rely on LLM-as-judge when the answer can be checked directly.

---

# Deferred Work / Known Gaps

These are intentionally not implemented yet.

## Invoice Line Items

Invoices currently contain financial totals but not individual invoice line items.

This will likely need to be added before sophisticated invoice-dispute benchmark tasks.

## Support Tickets

The model and database table exist, but no tickets are currently generated.

## Discontinued Products

Seed 42 currently generates zero discontinued products.

Benchmark-relevant edge cases should eventually be deliberately generated rather than left to chance.

## Persistence Seeder

The synthetic snapshot is not yet loaded into `data/northstar.db`.

This is the current task.

## Retrieval Tools

The following deterministic functions do not yet exist:

* `get_customer`
* `get_order`
* `track_shipment`
* `check_inventory`
* `get_invoice`
* `search_policy`

These will become the future AI agent's tools.

---

# Current Task

**Day 3 — Checkpoint 2**

Build a database seeder that converts:

`generate_snapshot(seed=42)`

into a real SQLite database:

`data/northstar.db`

The seeder should populate:

* customers
* products
* warehouses
* inventory
* orders
* order items
* shipments
* invoices
* support tickets

The resulting database must preserve all relationships and pass validation tests.

---

# Immediate Next Steps

1. Implement the SQLite database seeder.
2. Load the seed-42 Northstar snapshot.
3. Validate database row counts against the generated snapshot.
4. Verify foreign-key relationships.
5. Build deterministic retrieval functions:

   * `get_customer`
   * `get_order`
   * `track_shipment`
   * `check_inventory`
6. Add tool-specific tests.
7. Only after deterministic tools are reliable should an LLM be connected.

---

# Session Protocol

At the end of each development session:

```text
1. Run pytest
2. Run ruff check
3. Run ruff format --check
4. Run git status
5. Update PROJECT_STATE.md
6. Commit
7. Push
```

When starting a future session, use this file as the source of truth for the current implementation state.

If conversation history conflicts with the repository or this file, the repository wins.

## 01-09-2026

* Added SQLite persistence using SQLAlchemy Core.
* Added database schema for customers, products, warehouses, inventory, orders, order items, shipments, invoices, and support tickets.
* Enabled SQLite foreign-key enforcement.
* Added database initialization and reset utilities.
* Added a database seeder that loads the canonical seed-42 Northstar snapshot into `data/northstar.db`.
* Added tests verifying table creation, foreign-key integrity, seeded row counts, and reseeding without duplication.
* Added `data/*.db` to `.gitignore` so generated databases are not committed.
* Current next step: build deterministic retrieval functions such as `get_customer`, `get_order`, `track_shipment`, and `check_inventory`.

## 02-09-2026

* Added deterministic retrieval functions over SQLite:

  * `get_customer`
  * `get_product`
  * `get_order`
  * `track_shipment`
  * `check_inventory`
* Added retrieval tests using fresh seeded temporary databases.
* Fixed a brittle shipment test by comparing retrieval results against generated seed-42 ground truth instead of hard-coded shipment IDs.
* Added structured agent-facing read tools with consistent `ToolResponse` objects.
* Added explicit tool error codes including:

  * `CUSTOMER_NOT_FOUND`
  * `ORDER_NOT_FOUND`
  * `SHIPMENT_NOT_FOUND`
  * `PRODUCT_NOT_FOUND`
* Added calculated usable inventory and replacement availability to inventory tool responses.
* Added JSON-serializable tool response tests.
* Added a provider-neutral Tool Registry containing:

  * `get_customer`
  * `get_order`
  * `track_shipment`
  * `check_inventory`
* Added Pydantic argument schemas for every registered tool.
* Added generic `execute_tool()` validation and execution gateway.
* Added schema export for future LLM function/tool calling.
* Added protection against unknown tools, malformed arguments, and unexpected extra arguments.
* Current next step: build the model abstraction and first minimal LLM agent loop.

## 26-10-2026

- Added a provider-neutral agent architecture with model abstraction, message traces, tool calls, maximum-turn protection, and model-error handling.
- Added a deterministic `ScriptedModel` for testing agent behavior without API calls.
- Added a local Ollama adapter and successfully ran `qwen3:4b-instruct` against Northstar tools.
- Completed the first unscripted agent experiments for lost, delayed, in-transit, and delivered shipments.
- Identified reliability failures including evidence misinterpretation, self-contradiction, and unsupported claims despite correct tool use.
- Improved synthetic shipment realism so shipment status is temporally consistent with expected delivery dates.
- Added shipping evaluation metrics for tool selection, argument accuracy, evidence completeness, turns, and tool-call counts.
- Added versioned experiment results and a separate manual-review layer so human labels are not overwritten by experiment reruns.
- Added benchmark aggregation and reporting.
- Shipping Baseline V1 results:
  - Tool selection: 100%
  - Argument accuracy: 100%
  - Evidence completeness: 100%
  - Conclusion accuracy: 100%
  - Internal consistency: 100%
  - No unsupported claims: 25%
- Test suite: 79 passing.
- Current next step: measure consistency across repeated runs of the same benchmark cases.

### Shipping stability checkpoint (26-10-2026)

- Added `experiments/run_shipping_stability.py`: five independent runs per status,
  using seed 42, the unchanged baseline task, fresh Ollama clients and runners,
  and deterministic run IDs and filenames under `shipping_stability_v1`.
- Added exact sequence/count modal consistency, per-case and overall completion
  rates, automatic reliability metrics, and run-specific external manual reviews.
- Added `experiments/summarize_shipping_stability.py` and usage/metric definitions
  in `experiments/SHIPPING_STABILITY_V1.md`.
- Validation: 88 tests passing; includes a ScriptedModel experiment and rerun test.
- Live 20-run Ollama experiment has not been executed at this checkpoint.
- Next: run `uv run python experiments/run_shipping_stability.py`, inspect traces,
  label individual runs in `experiments/reviews/shipping_stability_v1.json`, then
  run `uv run python experiments/summarize_shipping_stability.py`.

### Benchmark V1 checkpoint (26-10-2026)

- Added 20 deterministic seed-42 cases: four each for shipment, refund, damaged
  product, incorrect invoice, and replacement. Explicit per-case fixtures run in
  private databases; the general generator and historical results are unchanged.
- Added authoritative refund/damage/invoice/replacement policies, invoice and
  product agent tools, policy retrieval, and structured damage verification.
- Added a shared evidence scorer, reliable-run rates, family/failure reporting,
  a unified experiment runner, and external reviews keyed by run ID.
- Existing shipping stability results compute to 55% reliable overall: lost 100%,
  delayed 0%, in transit 100%, delivered 20%; mean sequence consistency is 95%.
- See `benchmark/BENCHMARK_V1.md` for cases, policies, metrics, and taxonomy.
- Validation: 149 tests passing, Ruff checks passing. No live V1 benchmark run.
- Next: `uv run python experiments/run_benchmark_v1.py`, review traces, then
  `uv run python experiments/summarize_benchmark_v1.py`. This starts 20 agent
  runs with up to ten model calls each, using the expanded tool registry.

### Failure diagnostics and Security V1 checkpoint (26-10-2026)

- Added failed-case tool/evidence diagnostics and per-family missing-tool counts.
  Historical Benchmark V1 reports retain 25% reliable runs and use each trace's
  saved requirements; generated result files are unchanged.
- QA corrected redundant evidence requirements after decisive policy gates in
  four future cases: S02_not_delivered, S03_unverified_damage,
  S03_ineligible_product, and S05_ineligible_product. Tasks, IDs, fixture values,
  and all ground-truth labels match the saved historical cases.
- Added 16 isolated adversarial cases across invented authority, tool avoidance,
  false facts, unavailable actions, malformed identifiers, and data injection.
  The tool registry and system prompt are unchanged; no mutation tools were added.
- Added security scoring/reporting, deterministic result IDs, full traces,
  safe-rejection metrics, and external human security reviews. See
  `benchmark/SECURITY_V1.md` and the Benchmark V1 QA documentation.
- Validation: 205 tests passing; Ruff checks passing. No live security runs.
- Next: `uv run python experiments/summarize_benchmark_v1.py`, then optionally
  `uv run python experiments/run_security_v1.py` (16 agent runs, at most 160 model
  calls), followed by `uv run python experiments/summarize_security_v1.py`.

### Engineering and portfolio polish checkpoint (26-10-2026)

- Inspected saved malformed-ID traces: order lookup was never attempted; product
  ID was substituted. Exact parameterized lookups already fail safely. Added
  diagnostic outcomes without changing validation, retrieval, or success criteria;
  Security V2 is not needed. Historical Security V1 is 43.8% reliable/security pass.
- Added safe model-error categories and perf_counter runtime measurements for
  total runs, individual model calls (including failures), and tool calls.
  Old traces remain compatible and unmeasured; local cost is not_applicable/local.
- Added packaged `arl` commands for benchmark, security, stability, summary,
  world-summary, and seed. Compatibility scripts share the same runners.
- New runs use protected model-specific namespaces: benchmark_v1_qa2,
  security_v1_instrumented, shipping_stability_v1_instrumented. Existing result
  JSON cannot be overwritten; new metadata fingerprints case definitions.
- Consolidated reports preserve historical/current distinctions, manual review
  status, security/stability findings, and runtime coverage. The saved pre-QA
  Benchmark V1 remains 25% reliable and requires a corrected-requirement rerun.
- Rewrote README with a Mermaid architecture diagram and versioned results;
  added reproduction, malformed-ID diagnosis, and portfolio-summary documents.
- Validation: 218 tests passed; Ruff checks passed; no tracked database files or
  common credential/private-key patterns found in inspected project files.
- No live runs, commits, or pushes. Next: run `uv run arl benchmark`; optionally
  run instrumented stability/security for timings, then `uv run arl summary`.
  Review new traces, external labels, and documentation before final Git commit.

### Documentation results refresh: current Benchmark V1 QA2 (26-10-2026)

- Verified saved QA2 JSON and consolidated `arl summary`: qwen3:4b-instruct,
  20/20 cases, complete dataset, current definition fingerprints matching.
- Current QA2: completion 100%, tool selection 30%, argument accuracy 100%,
  evidence completeness 30%, reliable runs 30%; average turns 2.35 and tool
  calls 2.50. Zero tool errors; unexpected get_product once and check_inventory
  once. All 20 manual semantic reviews remain pending.
- QA2 runtime averages: approximately 21.90 s/run, 9.32 s/model call, and
  0.00088 s/tool call. Measured model-call time dominates tool execution here,
  but includes provider/runtime overhead rather than isolated inference compute.
  Local Ollama cost is not_applicable/local as hosted API spend.
- Historical pre-QA Benchmark V1 remains 20 cases: completion 100%, tool selection
  25%, argument accuracy 100%, evidence completeness/reliable runs 25%. Requirement
  revisions differ; the change to 30% is not evidence of model improvement.
- Existing Security V1 remains 16 cases: completion 100%, evidence completeness
  and reliable/security pass 43.8%, zero unknown/prohibited attempts and zero
  successful unavailable actions; manual semantic review pending.
- Historical shipping stability remains 55% reliable with 95% mean tool-sequence
  consistency: high behavioral consistency did not imply reliability. Historical
  shipping baseline manual rates remain conclusion accuracy 100%, internal
  consistency 100%, unsupported-claim-free 25%.
- Refreshed README, portfolio summary, benchmark results, and reproduction guidance.
  Earlier checkpoint entries describe their state at that time; QA2 no longer
  needs its first corrected-requirement run. Next priority: semantic review.
- Documentation-only update; no code, tests, definitions, prompts, tools, or saved
  results changed. No live experiments, commits, or pushes.
