from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ARLModel(BaseModel):
    """Base model for Agent Reliability Lab synthetic data."""

    model_config = ConfigDict(extra="forbid")


class CustomerTier(StrEnum):
    STANDARD = "standard"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"


class AccountStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


class ProductCategory(StrEnum):
    SAFETY_EQUIPMENT = "safety_equipment"
    TOOLS = "tools"
    OFFICE_EQUIPMENT = "office_equipment"
    STORAGE_EQUIPMENT = "storage_equipment"
    ELECTRICAL_ACCESSORIES = "electrical_accessories"


class OrderStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class ShipmentStatus(StrEnum):
    LABEL_CREATED = "label_created"
    IN_TRANSIT = "in_transit"
    DELAYED = "delayed"
    DELIVERED = "delivered"
    LOST = "lost"
    RETURNED_TO_SENDER = "returned_to_sender"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"
    DISPUTED = "disputed"


class TicketStatus(StrEnum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    WAITING_FOR_CUSTOMER = "waiting_for_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class IssueType(StrEnum):
    SHIPMENT = "shipment"
    REFUND = "refund"
    DAMAGED_PRODUCT = "damaged_product"
    INVOICE = "invoice"
    INVENTORY = "inventory"
    OTHER = "other"


class Address(ARLModel):
    line1: str = Field(min_length=1)
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    postal_code: str = Field(min_length=1)
    country: str = Field(min_length=1)


class Customer(ARLModel):
    customer_id: str = Field(pattern=r"^CUS-\d{5}$")
    company_name: str = Field(min_length=1)
    contact_name: str = Field(min_length=1)
    email: str = Field(min_length=3)
    account_status: AccountStatus
    customer_tier: CustomerTier
    billing_address: Address
    shipping_address: Address
    date_created: date


class Product(ARLModel):
    product_id: str = Field(pattern=r"^P\d{4}$")
    product_name: str = Field(min_length=1)
    category: ProductCategory
    unit_price: Decimal = Field(gt=0)
    active: bool
    replacement_eligible: bool


class Warehouse(ARLModel):
    warehouse_id: str = Field(pattern=r"^WH-(NORTH|CENTRAL|SOUTH)$")
    warehouse_name: str = Field(min_length=1)


class InventoryRecord(ARLModel):
    warehouse_id: str
    product_id: str
    quantity_available: int = Field(ge=0)
    quantity_reserved: int = Field(ge=0)

    @model_validator(mode="after")
    def reserved_inventory_cannot_exceed_available(self) -> Self:
        if self.quantity_reserved > self.quantity_available:
            raise ValueError("quantity_reserved cannot exceed quantity_available")

        return self


class OrderItem(ARLModel):
    product_id: str
    quantity: int = Field(ge=1)
    unit_price: Decimal = Field(gt=0)
    line_total: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def line_total_must_match_quantity_and_price(self) -> Self:
        expected_total = self.unit_price * self.quantity

        if self.line_total != expected_total:
            raise ValueError("line_total must equal unit_price multiplied by quantity")

        return self


class Order(ARLModel):
    order_id: str = Field(pattern=r"^ORD-\d{5}$")
    customer_id: str
    order_date: date
    order_status: OrderStatus
    shipping_address: Address
    billing_address: Address
    order_items: list[OrderItem] = Field(min_length=1)
    subtotal: Decimal = Field(ge=0)
    shipping_charge: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    total_amount: Decimal = Field(ge=0)

    @model_validator(mode="after")
    def order_totals_must_be_consistent(self) -> Self:
        expected_subtotal = sum(
            (item.line_total for item in self.order_items),
            start=Decimal("0.00"),
        )
        expected_total = self.subtotal + self.shipping_charge + self.tax

        if self.subtotal != expected_subtotal:
            raise ValueError("subtotal does not match order items")

        if self.total_amount != expected_total:
            raise ValueError("total_amount must equal subtotal + shipping_charge + tax")

        return self


class Shipment(ARLModel):
    shipment_id: str = Field(pattern=r"^SHP-\d{5}$")
    order_id: str
    carrier: str = Field(min_length=1)
    tracking_reference: str = Field(min_length=1)
    shipped_date: date | None
    expected_delivery_date: date | None
    actual_delivery_date: date | None
    shipment_status: ShipmentStatus

    @model_validator(mode="after")
    def shipment_dates_must_match_status(self) -> Self:
        if (
            self.shipment_status == ShipmentStatus.DELIVERED
            and self.actual_delivery_date is None
        ):
            raise ValueError("delivered shipments require an actual_delivery_date")

        if (
            self.shipment_status == ShipmentStatus.LOST
            and self.actual_delivery_date is not None
        ):
            raise ValueError("lost shipments cannot have an actual_delivery_date")

        return self


class Invoice(ARLModel):
    invoice_id: str = Field(pattern=r"^INV-\d{5}$")
    order_id: str
    issue_date: date
    subtotal: Decimal = Field(ge=0)
    shipping_charge: Decimal = Field(ge=0)
    tax: Decimal = Field(ge=0)
    total: Decimal = Field(ge=0)
    payment_status: PaymentStatus

    @model_validator(mode="after")
    def invoice_total_must_be_consistent(self) -> Self:
        expected_total = self.subtotal + self.shipping_charge + self.tax

        if self.total != expected_total:
            raise ValueError(
                "invoice total must equal subtotal + shipping_charge + tax"
            )

        return self


class SupportTicket(ARLModel):
    ticket_id: str = Field(pattern=r"^TKT-\d{5}$")
    customer_id: str
    order_id: str | None
    issue_type: IssueType
    status: TicketStatus
    priority: TicketPriority
    description: str = Field(min_length=1)
    created_date: date


class NorthstarSnapshot(ARLModel):
    customers: list[Customer]
    products: list[Product]
    warehouses: list[Warehouse]
    inventory: list[InventoryRecord]
    orders: list[Order]
    shipments: list[Shipment]
    invoices: list[Invoice]
    support_tickets: list[SupportTicket]


class NorthstarBaseWorld(ARLModel):
    customers: list[Customer]
    products: list[Product]
    warehouses: list[Warehouse]
    inventory: list[InventoryRecord]
