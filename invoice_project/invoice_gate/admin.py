# admin.py
import csv
import json
from datetime import timedelta
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime

from .models import (
    PurchaseOrderRef,
    InvoiceRef,
    VerificationRun,
    VerificationItemResult,
    Discrepancy,
    VerificationStatus,
)

# -------------------------
# Inline admin for item results and discrepancies
# -------------------------
class VerificationItemResultInline(admin.TabularInline):
    model = VerificationItemResult
    extra = 0
    fields = (
        "item_id",
        "description",
        "po_quantity",
        "invoice_quantity",
        "po_unit_price",
        "invoice_unit_price",
        "is_match",
    )
    readonly_fields = ("is_match",)
    show_change_link = True
    verbose_name = "Item result"
    verbose_name_plural = "Item results"


class DiscrepancyInline(admin.TabularInline):
    model = Discrepancy
    extra = 0
    fields = ("level", "type", "field", "expected", "actual", "message",)
    readonly_fields = ()
    verbose_name = "Discrepancy"
    verbose_name_plural = "Discrepancies"


# -------------------------
# Helper functions
# -------------------------
def pretty_json_html(value):
    """Return a small HTML <pre> with pretty-printed JSON or a placeholder."""
    if not value:
        return mark_safe("<small><i>empty</i></small>")
    try:
        pretty = json.dumps(value, indent=2, ensure_ascii=False)
        # limit to first 1200 chars to avoid huge pages
        if len(pretty) > 1200:
            preview = pretty[:1200] + "\n... (truncated)"
        else:
            preview = pretty
        return format_html(
            "<pre style='max-height:300px;overflow:auto;padding:8px;background:#f8f9fa;border-radius:6px;'>{}</pre>",
            preview,
        )
    except Exception:
        return format_html("<pre>{}</pre>", str(value))


# -------------------------
# Admin for PurchaseOrderRef
# -------------------------
@admin.register(PurchaseOrderRef)
class PurchaseOrderRefAdmin(admin.ModelAdmin):
    list_display = ("purchase_order_id", "buyer_name", "supplier_name", "issued_date", "total", "created_at")
    search_fields = ("purchase_order_id", "buyer_name", "supplier_name")
    list_filter = ("issued_date",)
    readonly_fields = ("created_at", "updated_at", "payload_preview")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("purchase_order_id", "buyer_name", "supplier_name", "currency", "issued_date")}),
        ("Amounts", {"fields": ("subtotal", "tax", "total")}),
        # <-- FIXED: use a tuple/list for single-field 'fields'
        ("Storage / Payload", {"fields": ("payload_preview",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def payload_preview(self, obj):
        return pretty_json_html(obj.payload)
    payload_preview.short_description = "PO payload (JSON)"


# -------------------------
# Admin for InvoiceRef
# -------------------------
@admin.register(InvoiceRef)
class InvoiceRefAdmin(admin.ModelAdmin):
    list_display = ("invoice_id", "purchase_order_link", "supplier_name", "issue_date", "total", "source_type", "created_at")
    search_fields = ("invoice_id", "supplier_name", "source_ref", "receiver_email")
    list_filter = ("source_type", "issue_date")
    readonly_fields = ("created_at", "updated_at", "payload_preview", "compared_payload_preview")
    ordering = ("-created_at",)
    raw_id_fields = ("purchase_order",)
    fieldsets = (
        (None, {"fields": ("invoice_id", "purchase_order", "supplier_name", "receiver_email", "source_type", "source_ref")}),
        ("Amounts", {"fields": ("currency", "subtotal", "tax", "total")}),
        ("Document", {"fields": ("document_container", "document_blob_path")}),
        ("Payloads", {"fields": ("payload_preview", "compared_payload_preview")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def purchase_order_link(self, obj):
        if obj.purchase_order:
            url = f"/admin/{obj.purchase_order._meta.app_label}/{obj.purchase_order._meta.model_name}/{obj.purchase_order.pk}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.purchase_order.purchase_order_id)
        return "-"
    purchase_order_link.short_description = "Purchase Order"

    def payload_preview(self, obj):
        return pretty_json_html(obj.payload)
    payload_preview.short_description = "Parsed invoice payload"

    def compared_payload_preview(self, obj):
        return pretty_json_html(obj.compared_payload)
    compared_payload_preview.short_description = "Compared payload snapshot"


# -------------------------
# Admin actions for VerificationRun
# -------------------------
def mark_runs_matched(modeladmin, request, queryset):
    """Mark selected runs as matched (quick admin action)."""
    updated = queryset.update(status=VerificationStatus.MATCHED)
    modeladmin.message_user(request, f"{updated} verification run(s) marked as MATCHED.")
mark_runs_matched.short_description = "Mark selected runs as MATCHED"


def mark_runs_mismatched(modeladmin, request, queryset):
    updated = queryset.update(status=VerificationStatus.MISMATCHED)
    modeladmin.message_user(request, f"{updated} verification run(s) marked as MISMATCHED.")
mark_runs_mismatched.short_description = "Mark selected runs as MISMATCHED"


def export_runs_to_csv(modeladmin, request, queryset):
    """Export a compact CSV summary of selected verification runs."""
    fieldnames = [
        "run_id",
        "invoice_id",
        "po_id",
        "status",
        "started_at",
        "finished_at",
        "duration_ms",
        "mismatch_count",
        "matched_item_count",
    ]
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = "attachment; filename=verification_runs.csv"
    writer = csv.DictWriter(response, fieldnames=fieldnames)
    writer.writeheader()

    for run in queryset.select_related("invoice", "purchase_order"):
        writer.writerow({
            "run_id": run.pk,
            "invoice_id": getattr(run.invoice, "invoice_id", ""),
            "po_id": getattr(run.purchase_order, "purchase_order_id", "") if run.purchase_order else "",
            "status": run.status,
            "started_at": localtime(run.started_at).isoformat() if run.started_at else "",
            "finished_at": localtime(run.finished_at).isoformat() if run.finished_at else "",
            "duration_ms": run.duration_ms,
            "mismatch_count": run.mismatch_count,
            "matched_item_count": run.matched_item_count,
        })
    return response
export_runs_to_csv.short_description = "Export selected runs to CSV"


# -------------------------
# Admin for VerificationRun
# -------------------------
@admin.register(VerificationRun)
class VerificationRunAdmin(admin.ModelAdmin):
    list_display = (
        "short_run_id",
        "invoice_link",
        "po_link",
        "status_badge",
        "summary_short",
        "mismatch_count",
        "matched_item_count",
        "duration_readable",
        "created_at",
    )
    list_select_related = ("invoice", "purchase_order")
    search_fields = ("invoice__invoice_id", "purchase_order__purchase_order_id", "summary", "invoice__supplier_name")
    list_filter = ("status", "created_at", "started_at", "finished_at")
    readonly_fields = ("created_at", "updated_at", "po_snapshot_preview", "invoice_snapshot_preview", "status", "duration_ms", "started_at", "finished_at")
    ordering = ("-created_at",)
    inlines = (VerificationItemResultInline, DiscrepancyInline)
    actions = (mark_runs_matched, mark_runs_mismatched, export_runs_to_csv)
    raw_id_fields = ("invoice", "purchase_order")

    fieldsets = (
        (None, {"fields": ("invoice", "purchase_order", "status")}),
        ("Counts & Flags", {"fields": ("mismatch_count", "matched_item_count", "quantities_ok", "prices_ok", "totals_ok", "currency_ok", "linkage_ok")}),
        ("Timing", {"fields": ("started_at", "finished_at", "duration_ms")}),
        ("Snapshots", {"fields": ("po_snapshot_preview", "invoice_snapshot_preview")}),
        ("Summary", {"fields": ("summary",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    # ----- convenience / display methods -----
    def short_run_id(self, obj):
        return str(obj.pk)[:8]
    short_run_id.short_description = "Run ID"

    def invoice_link(self, obj):
        if obj.invoice:
            url = f"/admin/{obj.invoice._meta.app_label}/{obj.invoice._meta.model_name}/{obj.invoice.pk}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.invoice.invoice_id)
        return "-"
    invoice_link.short_description = "Invoice"

    def po_link(self, obj):
        if obj.purchase_order:
            url = f"/admin/{obj.purchase_order._meta.app_label}/{obj.purchase_order._meta.model_name}/{obj.purchase_order.pk}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.purchase_order.purchase_order_id)
        return "-"
    po_link.short_description = "PO"

    def status_badge(self, obj):
        color = {
            VerificationStatus.PENDING: "#6c757d",      # gray
            VerificationStatus.MATCHED: "#198754",      # green
            VerificationStatus.MISMATCHED: "#dc3545",   # red
            VerificationStatus.ERROR: "#ffc107",        # yellow
        }.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{0};color:white;padding:3px 8px;border-radius:12px;font-weight:600;">{1}</span>',
            color,
            obj.get_status_display(),
        )
    status_badge.short_description = "Status"
    status_badge.allow_tags = True

    def summary_short(self, obj):
        if not obj.summary:
            return mark_safe("<small><i>—</i></small>")
        s = obj.summary
        if len(s) > 120:
            return s[:117] + "..."
        return s
    summary_short.short_description = "Summary"

    def duration_readable(self, obj):
        # show ms as readable if available
        if obj.duration_ms:
            return str(timedelta(milliseconds=obj.duration_ms))
        return "-"
    duration_readable.short_description = "Duration"

    def po_snapshot_preview(self, obj):
        return pretty_json_html(obj.po_snapshot)
    po_snapshot_preview.short_description = "PO snapshot"

    def invoice_snapshot_preview(self, obj):
        return pretty_json_html(obj.invoice_snapshot)
    invoice_snapshot_preview.short_description = "Invoice snapshot"


# -------------------------
# Admin for VerificationItemResult
# -------------------------
@admin.register(VerificationItemResult)
class VerificationItemResultAdmin(admin.ModelAdmin):
    list_display = ("item_id", "run_link", "description_short", "po_quantity", "invoice_quantity", "po_unit_price", "invoice_unit_price", "is_match")
    search_fields = ("item_id", "description", "inv_original_name", "run__invoice__invoice_id")
    list_filter = ("is_match",)
    raw_id_fields = ("run",)
    readonly_fields = ("created_at", "updated_at",)
    fieldsets = (
        (None, {"fields": ("run", "item_id", "description", "inv_original_name")}),
        ("Quantities & Prices", {"fields": ("po_quantity", "invoice_quantity", "po_unit_price", "invoice_unit_price", "is_match")}),
        ("Extra", {"fields": ("extra_data",)}),
    )

    def run_link(self, obj):
        url = f"/admin/{obj.run._meta.app_label}/{obj.run._meta.model_name}/{obj.run.pk}/change/"
        return format_html('<a href="{}">Run {}</a>', url, str(obj.run.pk)[:8])
    run_link.short_description = "Run"

    def description_short(self, obj):
        if not obj.description:
            return mark_safe("<small><i>—</i></small>")
        d = obj.description
        if len(d) > 80:
            return d[:77] + "..."
        return d
    description_short.short_description = "Description"


# -------------------------
# Admin for Discrepancy
# -------------------------
@admin.register(Discrepancy)
class DiscrepancyAdmin(admin.ModelAdmin):
    list_display = ("short_id", "run_link", "level", "type", "field", "expected", "actual", "message_short", "created_at")
    list_filter = ("level", "type", "created_at")
    search_fields = ("item_result__item_id", "message", "field", "expected", "actual", "run__invoice__invoice_id")
    raw_id_fields = ("run", "item_result")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    def short_id(self, obj):
        return str(obj.pk)[:8]
    short_id.short_description = "ID"

    def run_link(self, obj):
        if not obj.run:
            return "-"
        url = f"/admin/{obj.run._meta.app_label}/{obj.run._meta.model_name}/{obj.run.pk}/change/"
        return format_html('<a href="{}">Run {}</a>', url, str(obj.run.pk)[:8])
    run_link.short_description = "Run"

    def message_short(self, obj):
        if not obj.message:
            return mark_safe("<small><i>—</i></small>")
        m = obj.message
        if len(m) > 100:
            return m[:97] + "..."
        return m
    message_short.short_description = "Message"
