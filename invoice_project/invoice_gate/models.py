

# invoice_gate/models.py

import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from .models import *  # noqa: F403


# ---------- Base Model ----------
class TimeStampedUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------- Purchase Order ----------
class PurchaseOrder(TimeStampedUUIDModel):
    purchase_order_id = models.CharField(max_length=100, db_index=True, unique=True)
    currency = models.CharField(max_length=10, blank=True, null=True)
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    tax = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    issued_date = models.DateField(blank=True, null=True)
    buyer_name = models.CharField(max_length=255, blank=True, null=True)
    supplier_name = models.CharField(max_length=255, blank=True, null=True)

    # Full raw JSON you parsed/received for PO
    payload = models.JSONField(blank=True, null=True)

    def __str__(self):
        return f"PO {self.purchase_order_id}"


# ---------- Invoice ----------
class InvoiceSource:
    EMAIL = "email"
    UPLOAD = "upload"
    API = "api"

    CHOICES = [
        (EMAIL, "Email"),
        (UPLOAD, "Manual Upload"),
        (API, "API"),
    ]


class Invoice(TimeStampedUUIDModel):
    invoice_id = models.CharField(max_length=100, db_index=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices"
    )
    issue_date = models.DateField(blank=True, null=True)
    currency = models.CharField(max_length=10, blank=True, null=True)

    subtotal = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    tax = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)
    total = models.DecimalField(max_digits=14, decimal_places=2, blank=True, null=True)

    supplier_name = models.CharField(max_length=255, blank=True, null=True)

    source_type = models.CharField(max_length=20, choices=InvoiceSource.CHOICES, default=InvoiceSource.EMAIL)
    source_ref = models.CharField(max_length=255, blank=True, null=True)  # e.g., Message-ID, filename, external id
    receiver_email = models.EmailField(blank=True, null=True)

    # Store original parsed JSON
    payload = models.JSONField(blank=True, null=True)
    compared_payload = models.JSONField(blank=True, null=True)

    # store invoice document location (if any)
    document_container = models.CharField(max_length=100, blank=True, null=True)  # e.g. "invoices"
    document_blob_path = models.CharField(max_length=512, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["invoice_id"]),
            models.Index(fields=["source_type", "source_ref"]),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_id}"


# ---------- Verification Results ----------
class VerificationStatus:
    PENDING = "pending"
    MATCHED = "matched"
    MISMATCHED = "mismatched"
    ERROR = "error"

    CHOICES = [
        (PENDING, "Pending"),
        (MATCHED, "Matched"),
        (MISMATCHED, "Mismatched"),
        (ERROR, "Error"),
    ]


class VerificationRun(TimeStampedUUIDModel):
    """
    One verification attempt comparing a single Invoice against a PO.
    """
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        on_delete=models.SET_NULL,
        null=True,
        related_name="verification_runs"
    )
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="verification_runs"
    )

    status = models.CharField(max_length=20, choices=VerificationStatus.CHOICES, default=VerificationStatus.PENDING, db_index=True)
    summary = models.TextField(blank=True, null=True)  # human-readable summary (what matched/failed)
    mismatch_count = models.PositiveIntegerField(default=0)
    matched_item_count = models.PositiveIntegerField(default=0)

    # Quick flags for dashboards
    quantities_ok = models.BooleanField(default=True)
    prices_ok = models.BooleanField(default=True)
    totals_ok = models.BooleanField(default=True)
    currency_ok = models.BooleanField(default=True)
    linkage_ok = models.BooleanField(default=True)  # invoice <-> PO references

    started_at = models.DateTimeField(blank=True, null=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    duration_ms = models.PositiveIntegerField(default=0)

    # Snapshots for audit
    po_snapshot = models.JSONField(blank=True, null=True)
    invoice_snapshot = models.JSONField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Verify {self.invoice.invoice_id} vs PO {self.purchase_order.purchase_order_id if self.purchase_order else 'N/A'}"


# ---------- Discrepancy Tracking ----------
class DiscrepancyLevel:
    HEADER = "header"   # e.g., currency mismatch, missing PO link
    ITEM = "item"       # item-wise discrepancies
    TOTAL = "total"     # subtotal/tax/grand_total mismatches

    CHOICES = [
        (HEADER, "Header"),
        (ITEM, "Item"),
        (TOTAL, "Total"),
    ]


class DiscrepancyType:
    MISSING_ITEM = "missing_item"
    EXTRA_ITEM = "extra_item"
    QUANTITY_MISMATCH = "quantity_mismatch"
    PRICE_MISMATCH = "price_mismatch"
    TAX_MISMATCH = "tax_mismatch"
    SUBTOTAL_MISMATCH = "subtotal_mismatch"
    TOTAL_MISMATCH = "total_mismatch"
    CURRENCY_MISMATCH = "currency_mismatch"
    PO_LINK_MISMATCH = "po_link_mismatch"

    CHOICES = [
        (MISSING_ITEM, "Missing Item"),
        (EXTRA_ITEM, "Extra Item"),
        (QUANTITY_MISMATCH, "Quantity Mismatch"),
        (PRICE_MISMATCH, "Price Mismatch"),
        (TAX_MISMATCH, "Tax Mismatch"),
        (SUBTOTAL_MISMATCH, "Subtotal Mismatch"),
        (TOTAL_MISMATCH, "Grand Total Mismatch"),
        (CURRENCY_MISMATCH, "Currency Mismatch"),
        (PO_LINK_MISMATCH, "PO Link Mismatch"),
    ]


class ItemVerification(TimeStampedUUIDModel):
    """
    Item-wise comparison across PO and Invoice.
    """
    run = models.ForeignKey(VerificationRun, on_delete=models.CASCADE, related_name="item_results")

    item_id = models.CharField(max_length=100, db_index=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    inv_original_name = models.CharField(max_length=500, blank=True, null=True)

    # Expected values from PO
    po_quantity = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0)
    po_unit_price = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0"))], default=0)

    # Actual billed values from Invoice
    invoice_quantity = models.DecimalField(max_digits=14, decimal_places=2, validators=[MinValueValidator(Decimal("0"))], default=0)
    invoice_unit_price = models.DecimalField(max_digits=14, decimal_places=4, validators=[MinValueValidator(Decimal("0"))], default=0)

    is_match = models.BooleanField(default=True)

    extra_data = models.JSONField(blank=True, null=True)  # keep any parsed metadata

    class Meta:
        indexes = [
            models.Index(fields=["item_id"]),
        ]

    def __str__(self):
        return f"ItemResult {self.item_id} (run {self.run_id})"


class Discrepancy(TimeStampedUUIDModel):
    """
    Normalized discrepancy records. One run can have many discrepancies.
    """
    run = models.ForeignKey(VerificationRun, on_delete=models.CASCADE, related_name="discrepancies")
    level = models.CharField(max_length=10, choices=DiscrepancyLevel.CHOICES, default=DiscrepancyLevel.ITEM)
    type = models.CharField(max_length=30, choices=DiscrepancyType.CHOICES)

    # Optional link to a specific item result
    item_result = models.ForeignKey(ItemVerification, on_delete=models.CASCADE, null=True, blank=True, related_name="discrepancies")

    field = models.CharField(max_length=50, blank=True, null=True)
    expected = models.CharField(max_length=100, blank=True, null=True)
    actual = models.CharField(max_length=100, blank=True, null=True)
    message = models.CharField(max_length=500, blank=True, null=True)

    class Meta:
        indexes = [
            models.Index(fields=["level", "type"]),
        ]

    def __str__(self):
        target = f"Item {self.item_result.item_id}" if self.item_result_id else "Header/Total"
        return f"[{self.get_level_display()}] {self.get_type_display()} - {target}"

