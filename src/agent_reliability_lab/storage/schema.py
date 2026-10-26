from sqlalchemy import (
    Boolean,
    Column,
    Date,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    Text,
)

metadata = MetaData()


customers = Table(
    "customers",
    metadata,
    Column("customer_id", String, primary_key=True),
    Column("company_name", String, nullable=False),
    Column("contact_name", String, nullable=False),
    Column("email", String, nullable=False),
    Column("account_status", String, nullable=False),
    Column("customer_tier", String, nullable=False),
    Column("billing_line1", String, nullable=False),
    Column("billing_city", String, nullable=False),
    Column("billing_state", String, nullable=False),
    Column("billing_postal_code", String, nullable=False),
    Column("billing_country", String, nullable=False),
    Column("shipping_line1", String, nullable=False),
    Column("shipping_city", String, nullable=False),
    Column("shipping_state", String, nullable=False),
    Column("shipping_postal_code", String, nullable=False),
    Column("shipping_country", String, nullable=False),
    Column("date_created", Date, nullable=False),
)


products = Table(
    "products",
    metadata,
    Column("product_id", String, primary_key=True),
    Column("product_name", String, nullable=False),
    Column("category", String, nullable=False),
    Column("unit_price", Numeric(10, 2), nullable=False),
    Column("active", Boolean, nullable=False),
    Column("replacement_eligible", Boolean, nullable=False),
)


warehouses = Table(
    "warehouses",
    metadata,
    Column("warehouse_id", String, primary_key=True),
    Column("warehouse_name", String, nullable=False),
)


inventory = Table(
    "inventory",
    metadata,
    Column(
        "warehouse_id",
        String,
        ForeignKey("warehouses.warehouse_id"),
        primary_key=True,
    ),
    Column(
        "product_id",
        String,
        ForeignKey("products.product_id"),
        primary_key=True,
    ),
    Column("quantity_available", Integer, nullable=False),
    Column("quantity_reserved", Integer, nullable=False),
)


orders = Table(
    "orders",
    metadata,
    Column("order_id", String, primary_key=True),
    Column(
        "customer_id",
        String,
        ForeignKey("customers.customer_id"),
        nullable=False,
    ),
    Column("order_date", Date, nullable=False),
    Column("order_status", String, nullable=False),
    Column("shipping_line1", String, nullable=False),
    Column("shipping_city", String, nullable=False),
    Column("shipping_state", String, nullable=False),
    Column("shipping_postal_code", String, nullable=False),
    Column("shipping_country", String, nullable=False),
    Column("billing_line1", String, nullable=False),
    Column("billing_city", String, nullable=False),
    Column("billing_state", String, nullable=False),
    Column("billing_postal_code", String, nullable=False),
    Column("billing_country", String, nullable=False),
    Column("subtotal", Numeric(10, 2), nullable=False),
    Column("shipping_charge", Numeric(10, 2), nullable=False),
    Column("tax", Numeric(10, 2), nullable=False),
    Column("total_amount", Numeric(10, 2), nullable=False),
)


order_items = Table(
    "order_items",
    metadata,
    Column("order_item_id", Integer, primary_key=True),
    Column(
        "order_id",
        String,
        ForeignKey("orders.order_id"),
        nullable=False,
    ),
    Column(
        "product_id",
        String,
        ForeignKey("products.product_id"),
        nullable=False,
    ),
    Column("quantity", Integer, nullable=False),
    Column("unit_price", Numeric(10, 2), nullable=False),
    Column("line_total", Numeric(10, 2), nullable=False),
)


shipments = Table(
    "shipments",
    metadata,
    Column("shipment_id", String, primary_key=True),
    Column(
        "order_id",
        String,
        ForeignKey("orders.order_id"),
        nullable=False,
    ),
    Column("carrier", String, nullable=False),
    Column("tracking_reference", String, nullable=False),
    Column("shipped_date", Date),
    Column("expected_delivery_date", Date),
    Column("actual_delivery_date", Date),
    Column("shipment_status", String, nullable=False),
)


invoices = Table(
    "invoices",
    metadata,
    Column("invoice_id", String, primary_key=True),
    Column(
        "order_id",
        String,
        ForeignKey("orders.order_id"),
        nullable=False,
    ),
    Column("issue_date", Date, nullable=False),
    Column("subtotal", Numeric(10, 2), nullable=False),
    Column("shipping_charge", Numeric(10, 2), nullable=False),
    Column("tax", Numeric(10, 2), nullable=False),
    Column("total", Numeric(10, 2), nullable=False),
    Column("payment_status", String, nullable=False),
)


support_tickets = Table(
    "support_tickets",
    metadata,
    Column("ticket_id", String, primary_key=True),
    Column(
        "customer_id",
        String,
        ForeignKey("customers.customer_id"),
        nullable=False,
    ),
    Column(
        "order_id",
        String,
        ForeignKey("orders.order_id"),
    ),
    Column("issue_type", String, nullable=False),
    Column("status", String, nullable=False),
    Column("priority", String, nullable=False),
    Column("description", Text, nullable=False),
    Column("created_date", Date, nullable=False),
)


damage_reports = Table(
    "damage_reports",
    metadata,
    Column("order_id", String, ForeignKey("orders.order_id"), primary_key=True),
    Column("product_id", String, ForeignKey("products.product_id"), primary_key=True),
    Column("verified", Boolean, nullable=False),
    Column("reported_date", Date, nullable=False),
)
