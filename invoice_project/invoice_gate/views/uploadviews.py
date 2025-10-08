import os
import re
import logging
from decimal import Decimal, InvalidOperation
from django.utils.dateparse import parse_date as django_parse_date
from django.core.files.storage import default_storage
from django.db import IntegrityError
from django.utils.dateparse import parse_date

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_yasg.utils import swagger_auto_schema
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from ..models import PurchaseOrder, Invoice, VerificationRun, VerificationStatus
from ..serializers.uploadserializers import (
    POUploadSerializer, 
    InvoiceUploadSerializer,
)
from ..ocr_utils import file_to_text, extract_structured_fields
from ..compare import compare_one_pair, persist_verification, normalize_compared_payload


MAX_FILES_PER_TYPE = 3

# helper: save uploaded file and return fullpath + saved name
def save_upload_and_get_path(uploaded_file, subdir="uploads"):
    saved_name = default_storage.save(f"{subdir}/{uploaded_file.name}", uploaded_file)
    # compute full path that our file_to_text expects
    fullpath = default_storage.path(saved_name) if hasattr(default_storage, "path") else os.path.join(default_storage.location, saved_name)
    return saved_name, fullpath

# ---------- PO Upload API ----------
@method_decorator(csrf_exempt, name='dispatch')
class PurchaseOrderUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)
   
    @swagger_auto_schema(request_body=POUploadSerializer, responses={201: "PO created", 400: "error"})
    def post(self, request):
        serializer = POUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]
        filename_override = serializer.validated_data.get("filename")

        # Simple single file enforcement
        if not f:
            return Response({"error": "File is required"}, status=status.HTTP_400_BAD_REQUEST)

        saved_name, fullpath = save_upload_and_get_path(f, subdir="po_uploads")
        text = file_to_text(fullpath)

        if not text.strip():
            return Response({"error": "OCR / text extraction failed or empty"}, status=status.HTTP_400_BAD_REQUEST)

        # Use extract_structured_fields with PO hint
        parsed = extract_structured_fields(text, doc_type_hint="po")

        # Normalize dates if possible (best-effort)
        issued_date = None
        if parsed.get("date"):
            try:
                # leave as string in payload, but try parse for model field
                issued_date = parse_date(parsed.get("date"))
            except:  # noqa: E722
                issued_date = None

        try:
            po_obj = PurchaseOrder.objects.create(
                purchase_order_id=parsed.get("id") or (filename_override or f.name),
                currency=parsed.get("currency") or None,
                subtotal=parsed.get("subtotal"),
                tax=parsed.get("tax"),
                total=parsed.get("total"),
                issued_date=issued_date,
                buyer_name=parsed.get("buyer") or parsed.get("requested_by") or None,
                supplier_name=parsed.get("vendor") or None,
                payload=parsed
            )

            # attach file path in payload / or separate field if you prefer
            po_obj.payload = po_obj.payload or {}
            po_obj.payload.setdefault("_storage", {})["document_blob_path"] = saved_name
            po_obj.save(update_fields=["payload"])

            return Response({
                "po_id": po_obj.purchase_order_id,
                "uuid": str(po_obj.id),
                "supplier": po_obj.supplier_name,
                "total": po_obj.total,
                "parsed": parsed
            }, status=status.HTTP_201_CREATED)
        except IntegrityError:
            return Response({"error": f"Already exists: {po_obj.purchase_order_id}"}, status=status.HTTP_400_BAD_REQUEST)


# ---------- Invoice Upload + Verify API ----------

# ---------- helpers ----------
def safe_decimal(value):
    """
    Convert a value to Decimal or return None.
    Accepts numbers, numeric-strings, or objects like {'VAT_amount': 123.0}.
    """
    if value is None:
        return None
    # If it's already a Decimal
    if isinstance(value, Decimal):
        return value
    # If it's a dict like {'VAT_amount': 10725.0}
    if isinstance(value, dict):
        # prefer common keys
        for key in ("amount", "value", "VAT_amount", "vat_amount", "total", "amount_due"):
            if key in value:
                return safe_decimal(value[key])
        # otherwise try to find a numeric-like item
        for v in value.values():
            if isinstance(v, (int, float, str, Decimal)):
                dec = safe_decimal(v)
                if dec is not None:
                    return dec
        return None
    # If numeric types
    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    # If string: strip non-numeric except dot and minus
    if isinstance(value, str):
        s = value.strip()
        # remove currency symbols and grouping commas
        s = re.sub(r"[^\d\.\-]", "", s)
        if not s:
            return None
        try:
            return Decimal(s)
        except (InvalidOperation, ValueError):
            return None
    # fallback
    return None


def extract_vendor_name(vendor_field):
    """
    vendor_field may be a string or dict (like {'name': 'Foo', ...}).
    Return a concise string or None.
    """
    if not vendor_field:
        return None
    if isinstance(vendor_field, str):
        return vendor_field.strip()[:255] or None
    if isinstance(vendor_field, dict):
        # prefer "name" then "vendor" then attempt join of address/name
        for key in ("name", "vendor", "supplier", "supplier_name"):
            if key in vendor_field and vendor_field[key]:
                return str(vendor_field[key]).strip()[:255]
        # fallback to concatenating first few values
        vals = [str(v).strip() for v in vendor_field.values() if v and isinstance(v, (str, int, float))]
        if vals:
            joined = " | ".join(vals)[:255]
            return joined
    # other types
    try:
        return str(vendor_field)[:255]
    except:  # noqa: E722
        return None


def dnormalize_compared_payload(obj):
    """
    Convert Decimal values to floats/strings so JSONField will not choke on Decimals
    (Django's JSONField serializes Decimal but to be safe convert to float where possible).
    Recursively process dicts/lists.
    """
    if isinstance(obj, Decimal):
        # convert to float if safe
        try:
            return float(obj)
        except Exception:
            return str(obj)
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            out[k] = dnormalize_compared_payload(v)
        return out
    if isinstance(obj, list):
        return [dnormalize_compared_payload(x) for x in obj]
    return obj


logger = logging.getLogger(__name__)

# ---------- patched view.post ----------
@method_decorator(csrf_exempt, name='dispatch')
class InvoiceUploadAndVerifyView(APIView):
    """
    Upload an invoice file, run OCR / structured extraction, attempt to match with a PO,
    compare (either local comparator or via Mistral if enabled), persist results, and return a summary.
    """
    parser_classes = (MultiPartParser, FormParser)

    @swagger_auto_schema(request_body=InvoiceUploadSerializer, responses={200: "Verification result", 400: "error"})
    def post(self, request):
        serializer = InvoiceUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        f = serializer.validated_data["file"]
        filename_override = serializer.validated_data.get("filename")
        explicit_po_id = serializer.validated_data.get("purchase_order_id")
        print("*"*50)
        print(explicit_po_id)
        print("*"*50)

        if not f:
            return Response({"error": "File is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Save uploaded file and convert to text
        try:
            saved_name, fullpath = save_upload_and_get_path(f, subdir="invoice_uploads")
        except Exception as exc:
            logger.exception("Failed to save uploaded file")
            return Response({"error": "Failed to save uploaded file", "detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        text = file_to_text(fullpath)
        if not text.strip():
            return Response({"error": "OCR / text extraction failed - empty text"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract structured fields (this function should return a dict)
        parsed = extract_structured_fields(text, doc_type_hint="invoice") or {}

        # Normalize / sanitize parsed fields
        def _safe_decimal_local(value):
            if value is None:
                return None
            if isinstance(value, Decimal):
                return value
            if isinstance(value, dict):
                # common keys
                for key in ("amount", "value", "VAT_amount", "vat_amount", "total", "amount_due"):
                    if key in value:
                        return _safe_decimal_local(value[key])
                # try values
                for v in value.values():
                    if isinstance(v, (int, float, str, Decimal)):
                        dec = _safe_decimal_local(v)
                        if dec is not None:
                            return dec
                return None
            if isinstance(value, (int, float)):
                try:
                    return Decimal(str(value))
                except (InvalidOperation, ValueError):
                    return None
            if isinstance(value, str):
                s = re.sub(r"[^\d\.\-]", "", value.strip())
                if not s:
                    return None
                try:
                    return Decimal(s)
                except (InvalidOperation, ValueError):
                    return None
            return None

        def _extract_vendor_name_local(vendor_field):
            if not vendor_field:
                return None
            if isinstance(vendor_field, str):
                return vendor_field.strip()[:255] or None
            if isinstance(vendor_field, dict):
                for key in ("name", "vendor", "supplier", "supplier_name"):
                    if key in vendor_field and vendor_field[key]:
                        return str(vendor_field[key]).strip()[:255]
                vals = [str(v).strip() for v in vendor_field.values() if v and isinstance(v, (str, int, float))]
                if vals:
                    return " | ".join(vals)[:255]
            try:
                return str(vendor_field)[:255]
            except Exception:
                return None

        # Issue date
        issue_date = None
        parsed_date = parsed.get("date")
        if parsed_date:
            try:
                issue_date = django_parse_date(parsed_date) or None
            except Exception:
                issue_date = None

        supplier_name = _extract_vendor_name_local(parsed.get("vendor"))

        # Monetary fields converted to Decimal or None
        subtotal_dec = _safe_decimal_local(parsed.get("subtotal"))
        tax_dec = _safe_decimal_local(parsed.get("tax"))
        total_dec = _safe_decimal_local(parsed.get("total"))

        # Create InvoiceRef (purchase_order left null for now)
        invoice_identifier = parsed.get("id") or (filename_override or f.name)
        try:
            default_source = Invoice._meta.get_field("source_type").default
        except Exception:
            default_source = "upload"

        try:
            invoice_obj = Invoice.objects.create(
                invoice_id=invoice_identifier,
                issue_date=issue_date,
                currency=parsed.get("currency") or None,
                subtotal=subtotal_dec,
                tax=tax_dec,
                total=total_dec,
                supplier_name=supplier_name,
                source_type=default_source,
                source_ref=saved_name,
                payload=parsed,
                document_blob_path=saved_name
            )
        except Exception as exc:
            logger.exception("Failed to create InvoiceRef")
            return Response({"error": "Failed to persist invoice", "detail": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Attempt linking to a PO (several heuristics)
        matched_po = None
        try:
            if explicit_po_id:
                matched_po = PurchaseOrder.objects.filter(id=explicit_po_id).first()
        except Exception:
            matched_po = None

        if not matched_po and parsed.get("po_number"):
            try:
                matched_po = PurchaseOrder.objects.filter(purchase_order_id__iexact=parsed.get("po_number")).first()
            except Exception:
                matched_po = None

        if not matched_po:
            vendor = (supplier_name or "").strip()
            total_val = total_dec
            if vendor and total_val is not None:
                try:
                    matched_po = PurchaseOrder.objects.filter(
                        supplier_name__icontains=vendor[:50],
                        total=total_val
                    ).order_by("-created_at").first()
                except Exception:
                    matched_po = None

        if not matched_po:
            inv_id = parsed.get("id")
            if inv_id:
                try:
                    matched_po = PurchaseOrder.objects.filter(purchase_order_id__iexact=inv_id).first()
                except Exception:
                    matched_po = None

        if matched_po:
            try:
                invoice_obj.purchase_order = matched_po
                invoice_obj.save(update_fields=["purchase_order"])
            except Exception:
                logger.exception("Failed to link invoice to matched PO")

        # Prepare parsed PO payload for comparison
        po_parsed = matched_po.payload if matched_po and isinstance(matched_po.payload, dict) else {}

        try:
            status_str, summary, reasons, details = compare_one_pair(parsed, po_parsed)
        except Exception as exc:
            logger.exception("Comparator failed")
            status_str = "NEEDS REVIEW"
            summary = f"Comparator error: {str(exc)}"
            reasons = [f"Comparator exception: {str(exc)}"]
            details = {
                "invoice_total": parsed.get("total"),
                "po_total": po_parsed.get("total"),
                "items": []
            }

        # Persist verification results (creates VerificationRun, ItemResults, Discrepancies)
        try:
            run = persist_verification(invoice_obj, matched_po, status_str, summary, reasons, details)
        except Exception:
            logger.exception("persist_verification failed; creating fallback run")
            # fallback minimal run to keep response shape
            try:
                run = VerificationRun.objects.create(
                    purchase_order=matched_po,
                    invoice=invoice_obj,
                    status=(VerificationStatus.MATCHED if status_str == "MATCHED" else VerificationStatus.MISMATCHED),
                    summary=summary,
                    mismatch_count=(len(reasons) if isinstance(reasons, (list, tuple)) else (1 if reasons else 0)),
                    matched_item_count=details.get("matched_items", 0) if isinstance(details, dict) else 0,
                    quantities_ok=details.get("quantities_ok", True) if isinstance(details, dict) else True,
                    prices_ok=details.get("prices_ok", True) if isinstance(details, dict) else True,
                    totals_ok=(status_str == "MATCHED"),
                    currency_ok=details.get("currency_ok", True) if isinstance(details, dict) else True,
                    linkage_ok=(matched_po is not None),
                    started_at=None,
                    finished_at=None,
                    duration_ms=0,
                    po_snapshot=po_parsed,
                    invoice_snapshot=parsed
                )
            except Exception as exc2:
                logger.exception("Failed to create fallback VerificationRun")
                return Response({"error": "Failed to persist verification run", "detail": str(exc2)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Save compared payload normalized (so JSONField is safe)
        compared = {
            "verification": {
                "status": run.status,
                "summary": run.summary,
                "reasons": reasons,
                "details": details
            }
        }
        try:
            invoice_obj.compared_payload = normalize_compared_payload(compared)
            invoice_obj.save(update_fields=["compared_payload"])
        except Exception:
            logger.exception("Failed to save compared_payload (non-fatal)")

        # Build response
        response_payload = {
            "invoice": {
                "uuid": str(invoice_obj.id),
                "invoice_id": invoice_obj.invoice_id,
                "supplier": invoice_obj.supplier_name,
                "total": float(invoice_obj.total) if invoice_obj.total is not None else None,
            },
            "matched_po": {
                "uuid": str(matched_po.id) if matched_po else None,
                "po_id": matched_po.purchase_order_id if matched_po else None,
            },
            "verification": {
                "run_id": str(run.id),
                "status": run.status,
                "summary": run.summary,
                "mismatch_count": run.mismatch_count,
                "reasons": reasons,
                "details": details
            }
        }

        return Response(response_payload, status=status.HTTP_200_OK)
    



