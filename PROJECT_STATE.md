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