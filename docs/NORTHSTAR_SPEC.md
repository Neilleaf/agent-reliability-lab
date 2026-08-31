# Northstar Supply Co. — Environment Specification

## 1. Company Overview

Northstar Supply Co. is a fictional B2B distributor of workplace and light industrial equipment.

It supplies small and medium-sized businesses through an online ordering system.

Northstar operates several warehouses and manages customer orders, inventory, shipments, invoices, returns, and support requests.

All company data used by Agent Reliability Lab is synthetic.

---

## 2. Product Categories

Northstar initially sells products across five categories:

### Safety Equipment

Examples:

* safety helmets
* protective gloves
* safety goggles
* reflective vests

### Tools

Examples:

* cordless drills
* tool kits
* torque wrenches
* measuring tools

### Office Equipment

Examples:

* office chairs
* monitor stands
* keyboards
* desk lamps

### Storage Equipment

Examples:

* shelving units
* storage bins
* tool cabinets
* document cabinets

### Electrical Accessories

Examples:

* extension cables
* surge protectors
* portable work lights
* cable reels

The initial synthetic dataset should contain approximately 40–60 products.

---

## 3. Customers

Northstar sells primarily to businesses.

Each customer will have:

* customer ID
* company name
* contact name
* email
* account status
* customer tier
* billing address
* shipping address
* date created

### Customer Tiers

Customers may belong to one of three tiers:

* Standard
* Business
* Enterprise

Customer tier may later influence policies such as shipping priority or support escalation.

For Version 1, refund eligibility should not depend on customer tier unless explicitly stated in policy.

---

## 4. Products

Each product will have:

* product ID
* product name
* category
* unit price
* active status
* replacement eligibility

Example product ID:

`P1042`

Products may be active or discontinued.

A discontinued product cannot be newly ordered but may still appear in historical orders.

---

## 5. Warehouses

Northstar initially operates three fictional warehouses:

* WH-NORTH
* WH-CENTRAL
* WH-SOUTH

Each warehouse maintains independent inventory.

Inventory must therefore be checked at the warehouse level rather than assumed globally.

---

## 6. Inventory

Each inventory record contains:

* warehouse ID
* product ID
* quantity available
* quantity reserved

Usable inventory is defined as:

`available quantity - reserved quantity`

An agent must not promise replacement stock unless usable inventory is greater than zero.

Inventory information returned by tools is treated as authoritative for the current synthetic environment.

---

## 7. Orders

Each order contains:

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

Example order ID:

`ORD-18422`

### Order Statuses

An order may have one of the following statuses:

* pending
* confirmed
* processing
* shipped
* delivered
* cancelled

A cancelled order cannot subsequently be shipped.

---

## 8. Order Items

Each order item contains:

* product ID
* quantity
* unit price at time of purchase
* line total

Historical order prices should remain unchanged even if the product's current price later changes.

This will allow invoice discrepancies to be evaluated correctly.

---

## 9. Shipments

Each shipment contains:

* shipment ID
* order ID
* carrier
* tracking reference
* shipped date
* expected delivery date
* actual delivery date
* shipment status

Example shipment ID:

`SHP-8821`

### Shipment Statuses

Possible statuses:

* label_created
* in_transit
* delayed
* delivered
* lost
* returned_to_sender

A shipment marked `delivered` should normally have an actual delivery date.

A shipment marked `lost` should not subsequently be treated as expected to arrive normally.

---

## 10. Invoices

Each invoice contains:

* invoice ID
* order ID
* issue date
* subtotal
* shipping charge
* tax
* total
* payment status

Example invoice ID:

`INV-93011`

### Invoice Principle

An invoice should reflect the financial terms of the associated order.

Potential benchmark errors may include:

* incorrect product quantity
* incorrect unit price
* duplicate charge
* incorrect shipping charge
* incorrect total calculation

The agent must compare invoice information against underlying order information rather than assuming the customer's complaint is correct.

---

## 11. Support Tickets

Each support ticket contains:

* ticket ID
* customer ID
* order ID, if applicable
* issue type
* status
* priority
* description
* created date

Possible statuses:

* open
* investigating
* waiting_for_customer
* resolved
* closed

Support tickets will initially be read-only.

Later versions may allow agents to create tickets.

---

# 12. Initial Business Policies

These policies exist primarily so agent decisions can be scored against objective rules.

They may evolve as the benchmark becomes more sophisticated.

## Refund Policy

A standard product may be refunded when:

* the request is made within 30 days of delivery, and
* the product is eligible for return, and
* there is no evidence that the product was damaged through customer misuse.

A refund request outside the 30-day period is not automatically approved.

The agent should not invent exceptions.

---

## Damaged Product Policy

If a customer reports that a product arrived damaged:

1. the order must be verified;
2. the product must appear in that order;
3. the request must be within 30 days of delivery;
4. the agent should determine whether replacement inventory is available.

If replacement inventory exists, replacement should normally be preferred.

If replacement inventory does not exist, refund or escalation may be appropriate.

---

## Late Shipment Policy

A shipment is considered late when the expected delivery date has passed and the shipment has not been delivered.

The correct response depends on shipment status.

### In transit but delayed

The customer should be informed of the delay.

A replacement should not automatically be issued.

### Lost

Replacement inventory should be checked.

If replacement inventory exists, replacement may be offered.

If inventory does not exist, escalation or refund may be appropriate.

### Delivered

The agent should not automatically assume the shipment is lost.

A delivered-but-not-received case requires further investigation.

---

## Replacement Policy

A replacement may only be promised when:

* the original issue qualifies for replacement; and
* usable inventory exists.

The agent must not state that a replacement is available without checking inventory.

---

## Invoice Dispute Policy

Customer claims should not be assumed to be correct.

The agent must compare:

* invoice quantities
* invoice unit prices
* shipping charges
* tax
* totals

against the corresponding order.

If the invoice matches the order, the agent should state that no invoice discrepancy was identified.

---

# 13. Agent Knowledge Boundaries

The future agent does not automatically know company data.

It must obtain business facts through tools.

For example, the model may know that Northstar has a refund policy, but it must call the appropriate policy tool to retrieve the policy when the task requires it.

Likewise, it must use tools to retrieve:

* order information
* customer information
* shipment status
* inventory
* invoices

This distinction is important because ARL evaluates whether the agent gathers sufficient evidence before making decisions.

---

# 14. Ground Truth Principle

Every benchmark task must have an objectively defined underlying state.

For example:

Customer says:

> "My shipment is lost. Please send another one."

But the synthetic database may show:

* shipment status: delayed
* expected delivery date: yesterday
* replacement inventory: available

The correct agent should not simply accept the customer's claim that the shipment is lost.

It should retrieve shipment information and discover that the shipment is delayed rather than lost.

This difference between **user claims** and **system ground truth** will be central to the benchmark.

---

# 15. Version 1 Scope

The first version of Northstar should remain deliberately small.

Initial target:

* approximately 100 customers
* 40–60 products
* 3 warehouses
* approximately 300–500 orders
* associated shipments
* associated invoices
* synthetic inventory records
* several business policies

Complexity should be introduced only when it creates a useful agent reliability test.
