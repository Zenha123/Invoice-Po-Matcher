import os
import re
import json
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# import models
from .models import (
    VerificationRun, ItemVerification,
    Discrepancy, VerificationStatus, DiscrepancyLevel, DiscrepancyType
)

# ---------- Mistral client ----------
try:
    from mistralai import Mistral
except Exception:
    Mistral = None


# ---------- helpers ----------
def safe_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, dict):
        for key in ("amount", "value", "VAT_amount", "vat_amount", "total", "amount_due"):
            if key in value:
                return safe_decimal(value[key])
        for v in value.values():
            if isinstance(v, (int, float, str, Decimal)):
                dec = safe_decimal(v)
                if dec is not None:
                    return dec
        return None
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except Exception:
            return None
    if isinstance(value, str):
        s = re.sub(r"[^\d\.\-]", "", value.strip())
        if not s:
            return None
        try:
            return Decimal(s)
        except Exception:
            return None
    return None


def normalize_compared_payload(obj):
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except:  # noqa: E722
            return str(obj)
    if isinstance(obj, dict):
        return {k: normalize_compared_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_compared_payload(x) for x in obj]
    return obj


def fuzzy_equal(a, b, rel_tol=0.01, abs_tol=0.5):
    try:
        if a is None or b is None:
            return False
        a = float(a)
        b = float(b)
    except Exception:
        return False
    if abs(a - b) <= abs_tol:
        return True
    if abs(a - b) <= rel_tol * max(abs(a), abs(b), 1.0):
        return True
    return False


def format_currency(v):
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "N/A"


# ---------- Mistral comparator ----------
def compare_one_pair(invoice_parsed: dict, po_parsed: dict):
    api_key = os.getenv("MISTRAL_API_KEY") or getattr(settings, "MISTRAL_API_KEY", None)
    if not api_key or Mistral is None:
        raise RuntimeError("Mistral client not configured or API key missing.")

    client = Mistral(api_key=api_key)

    def prune(doc):
        return {
            "id": doc.get("id"),
            "vendor": doc.get("vendor"),
            "currency": doc.get("currency"),
            "date": doc.get("date"),
            "subtotal": doc.get("subtotal"),
            "tax": doc.get("tax"),
            "total": doc.get("total"),
            "items": (doc.get("items") or [])[:80]
        }

    prompt = f"""
You are a strict JSON-only comparator. Compare the INVOICE and PO JSON below and output a single JSON object with keys:
- status: "MATCHED" or "NEEDS REVIEW"
- summary: short human summary
- reasons: array of strings
- details: {{ invoice_total, po_total, items: [{{description, inv_quantity, po_quantity, inv_unit_price, po_unit_price, quantity_ok, price_ok, match_score}}], vendor_invoice, vendor_po }}

CRITICAL: Return ONLY valid JSON. No markdown, no code blocks, no explanations. Just the JSON object.

Be conservative (choose NEEDS REVIEW on ambiguity).

INVOICE:
{json.dumps(prune(invoice_parsed))}

PO:
{json.dumps(prune(po_parsed))}
"""

    resp = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {"role": "system", "content": "You are a JSON comparator. Output ONLY valid JSON. Do not include any markdown formatting or code blocks."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0,
        max_tokens=2000
    )

    text_response = resp.choices[0].message.content if resp.choices else ""
    
    # Clean the response - remove markdown code blocks if present
    text_response = text_response.strip()
    if text_response.startswith("```json"):
        text_response = text_response[7:]
    if text_response.startswith("```"):
        text_response = text_response[3:]
    if text_response.endswith("```"):
        text_response = text_response[:-3]
    text_response = text_response.strip()
    
    # Extract JSON
    m = re.search(r"(\{[\s\S]*\})", text_response)
    json_text = m.group(1) if m else text_response.strip()
    
    # Try to parse JSON with error handling
    try:
        data = json.loads(json_text)
    except json.JSONDecodeError as e:
        # Log the error for debugging
        print(f"JSON Parse Error: {e}")
        print(f"Problematic JSON (first 500 chars): {json_text[:500]}")
        
        # Try to fix common issues
        # Remove trailing commas before closing braces/brackets
        json_text_fixed = re.sub(r',(\s*[}\]])', r'\1', json_text)
        
        try:
            data = json.loads(json_text_fixed)
        except json.JSONDecodeError:
            # If still fails, return a safe default
            raise RuntimeError(
                f"Mistral returned invalid JSON. Error: {e}. "
                f"Response preview: {text_response[:200]}"
            )

    status = data.get("status") or ("MATCHED" if not data.get("reasons") else "NEEDS REVIEW")
    summary = data.get("summary") or (data.get("reasons", [None])[0] or "Comparison produced results")
    reasons = data.get("reasons") or []
    details = data.get("details") or {}

    for k in ("invoice_total", "po_total"):
        if k in details:
            try:
                details[k] = float(details[k]) if details[k] is not None else None
            except Exception:
                details[k] = None

    items = details.get("items", [])
    normalized_items = []
    for it in items:
        normalized_items.append({
            "description": it.get("description"),
            "inv_quantity": (float(it["inv_quantity"]) if it.get("inv_quantity") is not None else None),
            "po_quantity": (float(it["po_quantity"]) if it.get("po_quantity") is not None else None),
            "inv_unit_price": (float(it["inv_unit_price"]) if it.get("inv_unit_price") is not None else None),
            "po_unit_price": (float(it["po_unit_price"]) if it.get("po_unit_price") is not None else None),
            "quantity_ok": bool(it.get("quantity_ok")),
            "price_ok": bool(it.get("price_ok")),
            "match_score": float(it.get("match_score") or 0)
        })

    details["items"] = normalized_items
    details.setdefault("vendor_invoice", invoice_parsed.get("vendor"))
    details.setdefault("vendor_po", po_parsed.get("vendor"))
    return status, summary, reasons, details


# ---------- Persisting results ----------
def persist_verification(invoice_obj, matched_po, status_str, summary, reasons, details):
    def to_decimal_safe(v):
        if v is None:
            return None
        try:
            return Decimal(str(v))
        except Exception:
            return None

    with transaction.atomic():
        run = VerificationRun.objects.create(
            purchase_order=matched_po,
            invoice=invoice_obj,
            status=(VerificationStatus.MATCHED if status_str == "MATCHED" else VerificationStatus.MISMATCHED),
            summary=summary,
            mismatch_count=len(reasons) if isinstance(reasons, (list, tuple)) else (1 if reasons else 0),
            matched_item_count=sum(1 for it in (details.get("items") or []) if it.get("quantity_ok") and it.get("price_ok")),
            quantities_ok=all(it.get("quantity_ok", True) for it in (details.get("items") or [])),
            prices_ok=all(it.get("price_ok", True) for it in (details.get("items") or [])),
            totals_ok=(status_str == "MATCHED"),
            currency_ok=True,
            linkage_ok=(matched_po is not None),
            started_at=timezone.now(),
            finished_at=timezone.now(),
            duration_ms=0,
            po_snapshot=(matched_po.payload if matched_po else None),
            invoice_snapshot=invoice_obj.payload or None
        )

        for idx, item in enumerate(details.get("items", [])):
            desc = item.get("description") or f"item-{idx}"
            inv_qty = to_decimal_safe(item.get("inv_quantity"))
            po_qty = to_decimal_safe(item.get("po_quantity"))
            inv_price = to_decimal_safe(item.get("inv_unit_price"))
            po_price = to_decimal_safe(item.get("po_unit_price"))

            item_result = ItemVerification.objects.create(
                run=run,
                item_id=str(uuid.uuid4())[:36],
                description=str(desc)[:500],
                inv_original_name=str(desc)[:500],
                po_quantity=(po_qty or Decimal("0")),
                po_unit_price=(po_price or Decimal("0")),
                invoice_quantity=(inv_qty or Decimal("0")),
                invoice_unit_price=(inv_price or Decimal("0")),
                is_match=(bool(item.get("quantity_ok")) and bool(item.get("price_ok"))),
                extra_data=item
            )

            if not item.get("quantity_ok", True):
                Discrepancy.objects.create(
                    run=run,
                    level=DiscrepancyLevel.ITEM,
                    type=DiscrepancyType.QUANTITY_MISMATCH,
                    item_result=item_result,
                    field="quantity",
                    expected=str(po_qty) if po_qty is not None else "",
                    actual=str(inv_qty) if inv_qty is not None else "",
                    message=f"Quantity mismatch for '{desc}': Invoice {inv_qty} vs PO {po_qty}"
                )

            if not item.get("price_ok", True):
                Discrepancy.objects.create(
                    run=run,
                    level=DiscrepancyLevel.ITEM,
                    type=DiscrepancyType.PRICE_MISMATCH,
                    item_result=item_result,
                    field="unit_price",
                    expected=str(po_price) if po_price is not None else "",
                    actual=str(inv_price) if inv_price is not None else "",
                    message=f"Price mismatch for '{desc}': Invoice {format_currency(inv_price)} vs PO {format_currency(po_price)}"
                )

            if (item.get("po_quantity") is None) and (item.get("inv_quantity") is not None):
                Discrepancy.objects.create(
                    run=run,
                    level=DiscrepancyLevel.ITEM,
                    type=DiscrepancyType.EXTRA_ITEM,
                    item_result=item_result,
                    field="description",
                    expected="",
                    actual=str(desc),
                    message=f"Extra item in invoice: '{desc}'"
                )

            if (item.get("inv_quantity") is None) and (item.get("po_quantity") is not None):
                Discrepancy.objects.create(
                    run=run,
                    level=DiscrepancyLevel.ITEM,
                    type=DiscrepancyType.MISSING_ITEM,
                    item_result=item_result,
                    field="description",
                    expected=str(desc),
                    actual="",
                    message=f"Item missing on invoice: '{desc}'"
                )

        inv_total = details.get("invoice_total")
        po_total = details.get("po_total")
        if inv_total is not None and po_total is not None:
            if not fuzzy_equal(inv_total, po_total, rel_tol=0.01, abs_tol=0.5):
                Discrepancy.objects.create(
                    run=run,
                    level=DiscrepancyLevel.TOTAL,
                    type=DiscrepancyType.TOTAL_MISMATCH,
                    field="total",
                    expected=str(po_total),
                    actual=str(inv_total),
                    message=f"Total mismatch: Invoice {format_currency(inv_total)} vs PO {format_currency(po_total)}"
                )

        return run