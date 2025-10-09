# compare.py
import os
import re
import json
import uuid
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Import models
from .models import (
    VerificationRun, ItemVerification,
    Discrepancy, VerificationStatus, DiscrepancyLevel, DiscrepancyType
)

# Mistral client
try:
    from mistralai import Mistral
except Exception:
    Mistral = None


# ---------- Helper functions ----------
def safe_decimal(value):
    """Convert various types to Decimal safely"""
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, dict):
        # Handle nested dict structures
        for key in ("amount", "value", "total", "amount_due", "VAT_amount", "vat_amount"):
            if key in value:
                return safe_decimal(value[key])
        # Try any numeric value in dict
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
        # Remove currency symbols and commas
        s = re.sub(r"[^\d\.\-]", "", value.strip())
        if not s or s == '.':
            return None
        try:
            return Decimal(s)
        except Exception:
            return None
    return None


def normalize_compared_payload(obj):
    """Normalize data for JSON serialization"""
    if isinstance(obj, Decimal):
        try:
            return float(obj)
        except:
            return str(obj)
    if isinstance(obj, dict):
        return {k: normalize_compared_payload(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [normalize_compared_payload(x) for x in obj]
    return obj


def fuzzy_equal(a, b, rel_tol=0.02, abs_tol=1.0):
    """
    Compare two numbers with tolerance
    Increased tolerance to 2% or $1 to handle rounding
    """
    try:
        if a is None or b is None:
            return False
        a = float(a)
        b = float(b)
    except Exception:
        return False
    
    # Exact match
    if a == b:
        return True
    
    # Absolute tolerance
    if abs(a - b) <= abs_tol:
        return True
    
    # Relative tolerance
    if abs(a - b) <= rel_tol * max(abs(a), abs(b), 1.0):
        return True
    
    return False


def format_currency(v):
    """Format number as currency"""
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "N/A"


def clean_json_response(text: str) -> str:
    """Clean Mistral response to extract valid JSON"""
    text = text.strip()
    
    # Remove markdown code blocks
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    
    # Extract JSON object
    json_match = re.search(r'(\{[\s\S]*\})', text)
    if json_match:
        text = json_match.group(1)
    
    # Fix common JSON issues
    text = re.sub(r',(\s*[}\]])', r'\1', text)  # Remove trailing commas
    text = re.sub(r'(?<!\\)\\n', r'\\\\n', text)  # Fix unescaped newlines
    
    return text


def match_items_fuzzy(invoice_items, po_items):
    """
    Fuzzy match items between invoice and PO
    Returns list of matched pairs with match scores
    """
    matched_pairs = []
    
    for inv_item in invoice_items:
        inv_desc = (inv_item.get("description") or "").lower().strip()
        inv_id = inv_item.get("item_id", "").upper()
        inv_qty = inv_item.get("quantity")
        inv_price = inv_item.get("unit_price")
        
        best_match = None
        best_score = 0
        
        for po_item in po_items:
            po_desc = (po_item.get("description") or "").lower().strip()
            po_id = po_item.get("item_id", "").upper()
            po_qty = po_item.get("quantity")
            po_price = po_item.get("unit_price")
            
            score = 0
            
            # Exact ID match = very high score
            if inv_id and po_id and inv_id == po_id:
                score += 50
            
            # Description similarity
            if inv_desc and po_desc:
                # Simple word overlap scoring
                inv_words = set(inv_desc.split())
                po_words = set(po_desc.split())
                common = inv_words & po_words
                if common:
                    score += len(common) / max(len(inv_words), len(po_words)) * 30
            
            # Quantity match
            if inv_qty and po_qty and fuzzy_equal(inv_qty, po_qty):
                score += 10
            
            # Price match
            if inv_price and po_price and fuzzy_equal(inv_price, po_price):
                score += 10
            
            if score > best_score:
                best_score = score
                best_match = po_item
        
        matched_pairs.append({
            "invoice_item": inv_item,
            "po_item": best_match,
            "match_score": best_score
        })
    
    # Check for unmatched PO items
    matched_po_descs = set()
    for pair in matched_pairs:
        if pair["po_item"]:
            matched_po_descs.add(pair["po_item"].get("description", "").lower())
    
    for po_item in po_items:
        po_desc = (po_item.get("description") or "").lower()
        if po_desc not in matched_po_descs:
            matched_pairs.append({
                "invoice_item": None,
                "po_item": po_item,
                "match_score": 0
            })
    
    return matched_pairs


# ---------- Mistral comparison ----------
def compare_one_pair(invoice_parsed: dict, po_parsed: dict):
    """
    Compare invoice and PO using Mistral AI - Optimized version
    """
    api_key = os.getenv("MISTRAL_API_KEY") or getattr(settings, "MISTRAL_API_KEY", None)
    if not api_key or Mistral is None:
        raise RuntimeError("Mistral client not configured or API key missing.")

    client = Mistral(api_key=api_key)

    def prune(doc):
        """Prepare document for comparison"""
        return {
            "id": doc.get("id"),
            "invoice_number": doc.get("invoice_number"),
            "po_number": doc.get("po_number"),
            "vendor": doc.get("vendor"),
            "buyer": doc.get("buyer"),
            "currency": doc.get("currency"),
            "date": doc.get("date"),
            "subtotal": doc.get("subtotal"),
            "tax": doc.get("tax"),
            "total": doc.get("total"),
            "items": (doc.get("items") or [])[:100]  # Limit items
        }

    invoice_data = prune(invoice_parsed)
    po_data = prune(po_parsed)

    prompt = f"""You are a financial document comparison AI. Compare the INVOICE and PURCHASE ORDER below.

Your task: Determine if the invoice matches the purchase order within acceptable business tolerances.

COMPARISON RULES:
1. Quantities must match exactly (or invoice can be less if items damaged/returned)
2. Unit prices should match within 2% or $1 tolerance (for rounding)
3. Totals should match within 2% or $2 tolerance
4. Vendor names should be the same company (exact match not required)
5. Line items should correspond to ordered items

OUTPUT FORMAT - Return ONLY this JSON structure (no markdown, no code blocks):
{{
  "status": "MATCHED" or "NEEDS REVIEW",
  "summary": "Brief explanation of match result",
  "reasons": ["list", "of", "specific", "issues"],
  "details": {{
    "invoice_total": number,
    "po_total": number,
    "vendor_invoice": "vendor name from invoice",
    "vendor_po": "vendor name from PO",
    "items": [
      {{
        "description": "item description",
        "inv_quantity": number or null,
        "po_quantity": number or null,
        "inv_unit_price": number or null,
        "po_unit_price": number or null,
        "quantity_ok": true/false,
        "price_ok": true/false,
        "match_score": number (0-100)
      }}
    ]
  }}
}}

IMPORTANT:
- Use "MATCHED" if documents match within tolerances
- Use "NEEDS REVIEW" only for significant discrepancies
- Be lenient with minor rounding differences
- If invoice quantity is slightly less than PO (1-2 units), check if there's a note about damage
- Return ONLY the JSON object

INVOICE DATA:
{json.dumps(invoice_data, indent=2)}

PURCHASE ORDER DATA:
{json.dumps(po_data, indent=2)}

Return the comparison JSON:"""

    try:
        # Call Mistral API
        resp = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise JSON comparator for financial documents. Return ONLY valid JSON with no markdown formatting."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )

        text_response = resp.choices[0].message.content if resp.choices else ""
        
        if not text_response:
            raise RuntimeError("Mistral returned empty response")
        
        # Clean and parse JSON
        cleaned_json = clean_json_response(text_response)
        
        try:
            data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Response preview: {text_response[:500]}")
            
            # Try fixing common issues
            cleaned_json = re.sub(r',(\s*[}\]])', r'\1', cleaned_json)
            
            try:
                data = json.loads(cleaned_json)
            except json.JSONDecodeError:
                # Return safe default
                raise RuntimeError(
                    f"Mistral returned invalid JSON. Error: {e}. "
                    f"Response: {text_response[:300]}"
                )
        
        # Extract and normalize data
        status = data.get("status", "NEEDS REVIEW")
        summary = data.get("summary", "Comparison completed")
        reasons = data.get("reasons", [])
        details = data.get("details", {})
        
        # Ensure status is valid
        if status not in ["MATCHED", "NEEDS REVIEW"]:
            status = "NEEDS REVIEW" if reasons else "MATCHED"
        
        # Normalize numeric fields in details
        for k in ("invoice_total", "po_total"):
            if k in details:
                try:
                    details[k] = float(details[k]) if details[k] is not None else None
                except Exception:
                    details[k] = None
        
        # Normalize items array
        items = details.get("items", [])
        normalized_items = []
        
        for it in items:
            normalized_item = {
                "description": it.get("description", "Unknown"),
                "inv_quantity": None,
                "po_quantity": None,
                "inv_unit_price": None,
                "po_unit_price": None,
                "quantity_ok": bool(it.get("quantity_ok", False)),
                "price_ok": bool(it.get("price_ok", False)),
                "match_score": float(it.get("match_score", 0))
            }
            
            # Parse numeric fields
            for field in ["inv_quantity", "po_quantity", "inv_unit_price", "po_unit_price"]:
                value = it.get(field)
                if value is not None:
                    try:
                        normalized_item[field] = float(value)
                    except Exception:
                        normalized_item[field] = None
            
            normalized_items.append(normalized_item)
        
        details["items"] = normalized_items
        details.setdefault("vendor_invoice", invoice_parsed.get("vendor"))
        details.setdefault("vendor_po", po_parsed.get("vendor"))
        
        # Log results
        print("\n" + "="*60)
        print("COMPARISON RESULTS:")
        print(f"Status: {status}")
        print(f"Summary: {summary}")
        if reasons:
            print(f"Reasons: {', '.join(reasons)}")
        print(f"Invoice Total: {format_currency(details.get('invoice_total'))}")
        print(f"PO Total: {format_currency(details.get('po_total'))}")
        print(f"Items Compared: {len(normalized_items)}")
        print("="*60 + "\n")
        
        return status, summary, reasons, details
        
    except Exception as e:
        print(f"ERROR in Mistral comparison: {e}")
        
        # Fallback to rule-based comparison
        return fallback_comparison(invoice_parsed, po_parsed)


def fallback_comparison(invoice_parsed: dict, po_parsed: dict):
    """
    Fallback rule-based comparison when Mistral fails
    """
    print("Using fallback rule-based comparison")
    
    reasons = []
    details = {
        "invoice_total": invoice_parsed.get("total"),
        "po_total": po_parsed.get("total"),
        "vendor_invoice": invoice_parsed.get("vendor"),
        "vendor_po": po_parsed.get("vendor"),
        "items": []
    }
    
    # Compare totals
    inv_total = safe_decimal(invoice_parsed.get("total"))
    po_total = safe_decimal(po_parsed.get("total"))
    
    if inv_total and po_total:
        if not fuzzy_equal(inv_total, po_total):
            reasons.append(f"Total mismatch: Invoice {format_currency(inv_total)} vs PO {format_currency(po_total)}")
    
    # Compare items
    inv_items = invoice_parsed.get("items", [])
    po_items = po_parsed.get("items", [])
    
    matched_pairs = match_items_fuzzy(inv_items, po_items)
    
    for pair in matched_pairs:
        inv_item = pair["invoice_item"]
        po_item = pair["po_item"]
        
        if inv_item and po_item:
            desc = inv_item.get("description") or po_item.get("description")
            inv_qty = safe_decimal(inv_item.get("quantity"))
            po_qty = safe_decimal(po_item.get("quantity"))
            inv_price = safe_decimal(inv_item.get("unit_price"))
            po_price = safe_decimal(po_item.get("unit_price"))
            
            qty_ok = fuzzy_equal(inv_qty, po_qty) if (inv_qty and po_qty) else True
            price_ok = fuzzy_equal(inv_price, po_price) if (inv_price and po_price) else True
            
            if not qty_ok:
                reasons.append(f"Quantity mismatch for '{desc}': {inv_qty} vs {po_qty}")
            if not price_ok:
                reasons.append(f"Price mismatch for '{desc}': {format_currency(inv_price)} vs {format_currency(po_price)}")
            
            details["items"].append({
                "description": desc,
                "inv_quantity": float(inv_qty) if inv_qty else None,
                "po_quantity": float(po_qty) if po_qty else None,
                "inv_unit_price": float(inv_price) if inv_price else None,
                "po_unit_price": float(po_price) if po_price else None,
                "quantity_ok": qty_ok,
                "price_ok": price_ok,
                "match_score": pair["match_score"]
            })
        elif inv_item and not po_item:
            reasons.append(f"Extra item on invoice: '{inv_item.get('description')}'")
            details["items"].append({
                "description": inv_item.get("description"),
                "inv_quantity": float(safe_decimal(inv_item.get("quantity"))) if inv_item.get("quantity") else None,
                "po_quantity": None,
                "inv_unit_price": float(safe_decimal(inv_item.get("unit_price"))) if inv_item.get("unit_price") else None,
                "po_unit_price": None,
                "quantity_ok": False,
                "price_ok": False,
                "match_score": 0
            })
        elif po_item and not inv_item:
            reasons.append(f"Missing item from invoice: '{po_item.get('description')}'")
            details["items"].append({
                "description": po_item.get("description"),
                "inv_quantity": None,
                "po_quantity": float(safe_decimal(po_item.get("quantity"))) if po_item.get("quantity") else None,
                "inv_unit_price": None,
                "po_unit_price": float(safe_decimal(po_item.get("unit_price"))) if po_item.get("unit_price") else None,
                "quantity_ok": False,
                "price_ok": False,
                "match_score": 0
            })
    
    # Determine status
    status = "MATCHED" if len(reasons) == 0 else "NEEDS REVIEW"
    summary = "Documents match" if status == "MATCHED" else f"Found {len(reasons)} discrepancies"
    
    return status, summary, reasons, details


# ---------- Persist verification results ----------
def persist_verification(invoice_obj, matched_po, status_str, summary, reasons, details):
    """
    Save verification results to database
    """
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

        # Save item-level results
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

            # Create discrepancies
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

        # Check total mismatch
        inv_total = details.get("invoice_total")
        po_total = details.get("po_total")
        if inv_total is not None and po_total is not None:
            if not fuzzy_equal(inv_total, po_total, rel_tol=0.02, abs_tol=2.0):
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
