import os
import re
import io
import json
from django.conf import settings
import fitz
from PIL import Image, ImageEnhance
import pytesseract

# New Mistral SDK
from mistralai import Mistral

# -------- Regex patterns --------
_money_rx = re.compile(r"[$₹€£]?\s*([0-9]+[0-9\.,]*)")
_invoice_rx = re.compile(r"(Invoice\s*#|Invoice\s*:|Invoice\:|\bINV\b|\bBill\b)\s*([A-Z0-9\-\_]+)", re.I)
_po_rx = re.compile(r"(PO\s*#|PO\s*:|Purchase Order\s*#|\bP\.O\.\b)\s*([A-Z0-9\-\_]+)", re.I)
_vendor_rx = re.compile(r"(Vendor|Supplier|From|Sold By|Billed From)\s*[:\-]?\s*([A-Za-z0-9&\.\,\-\s]+)", re.I)
_date_rx = re.compile(r"(Date|Dated|Invoice Date)\s*[:\-]?\s*([A-Za-z0-9\,\-\s\/]+)", re.I)

_invoice_indicators = [
    r"invoice\s*#", r"tax\s*invoice", r"bill\s*to", r"amount\s*due", 
    r"subtotal", r"total\s*due", r"balance\s*due", r"invoice\s*date",
    r"tax\s*amount", r"grand\s*total", r"invoice\s*total"
]
_po_indicators = [
    r"purchase\s*order", r"po\s*#", r"ordered\s*by", r"supplier",
    r"ship\s*to", r"delivery\s*date", r"order\s*date", r"p\.o\.\s*number"
]

def log(msg, *args):
    print("[OCR LOG]", msg, *args)

def classify_document_type(text):
    text_lower = text.lower()
    invoice_score = sum(1 for p in _invoice_indicators if re.search(p, text_lower))
    po_score = sum(1 for p in _po_indicators if re.search(p, text_lower))
    if invoice_score > po_score:
        return "invoice"
    elif po_score > invoice_score:
        return "po"
    return "unknown"

def run_local_ocr(image: Image.Image) -> str:
    log("Running local OCR with pytesseract")
    try:
        config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789$.,()/-: '
        return pytesseract.image_to_string(image, config=config)
    except Exception as e:
        log("pytesseract failed:", e)
        return ""

def preprocess_image(image: Image.Image) -> Image.Image:
    try:
        if image.mode != 'L':
            image = image.convert('L')
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(2.0)
    except Exception as e:
        log("Image preprocessing failed:", e)
        return image

def file_to_text(filepath: str) -> str:
    log("Processing file:", filepath)
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".pdf":
            log("PDF detected, converting pages to images using PyMuPDF")
            doc = fitz.open(filepath)
            all_text = []
            for i, page in enumerate(doc):
                if i >= 3:  # only first 3 pages
                    break
                log(f"Processing page {i+1}")
                pix = page.get_pixmap(dpi=300)
                img_data = pix.tobytes("png")
                image = Image.open(io.BytesIO(img_data))
                processed_image = preprocess_image(image)
                page_text = run_local_ocr(processed_image)
                if page_text.strip():
                    all_text.append(page_text)
            return "\n".join(all_text)
        else:
            log("Image file detected")
            image = Image.open(filepath)
            processed_image = preprocess_image(image)
            return run_local_ocr(processed_image)
    except Exception as e:
        log("Error processing file:", e)
        return ""


def run_mistral_extraction(ocr_text: str, api_key: str) -> dict:
    if not ocr_text or not api_key:
        return {"raw_text": ocr_text, "doc_type": "unknown"}

    try:
        log("Calling Mistral for structured extraction (new SDK)...")
        client = Mistral(api_key=api_key)

        prompt = f"""You are a precise document parser. Analyze the OCR text and determine if it's an Invoice or Purchase Order.
        Then extract ALL available fields into JSON with this structure:

        {{
        "doc_type": "invoice" or "po",
        "id": "document number or null",
        "vendor": "vendor/supplier name or null",
        "currency": "ISO3 or symbol or null (e.g. INR, USD, Rs, $)",
        "date": "date string or null",
        "subtotal": number or null,
        "tax": number or null,
        "total": number or null,
        "items": [
            {{
            "description": "item description",
            "quantity": number or null,
            "unit_price": number or null,
            "line_total": number or null
            }}
        ],
        "raw_text": "original OCR text"
        }}

        OCR TEXT:
        {ocr_text[:8000]}
        """

        # ✅ Use new method here
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[
                {"role": "system", "content": "You are a JSON extractor for financial documents. Return ONLY valid JSON."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
            max_tokens=2048
        )

        text_response = response.choices[0].message.content if response.choices else ""
        if not text_response:
            log("Mistral returned empty response")
            return {"raw_text": ocr_text, "doc_type": "unknown"}

        json_match = re.search(r"(\{[\s\S]*\})", text_response)
        json_text = json_match.group(1) if json_match else text_response.strip()
        try:
            data = json.loads(json_text)
            log("Mistral parsed JSON successfully")

            for field in ["subtotal", "tax", "total"]:
                if isinstance(data.get(field), str):
                    try:
                        data[field] = float(re.sub(r"[^\d.]", "", data[field]))
                    except:  # noqa: E722
                        data[field] = None

            if "items" not in data or not isinstance(data["items"], list):
                data["items"] = []
            for item in data["items"]:
                for field in ["quantity", "unit_price", "line_total"]:
                    if isinstance(item.get(field), str):
                        try:
                            item[field] = float(re.sub(r"[^\d.]", "", item[field]))
                        except:  # noqa: E722
                            item[field] = None

            data["raw_text"] = ocr_text

            log("Mistral Extraction Summary:")
            log(f"  Document Type: {data.get('doc_type')}")
            log(f"  Document ID: {data.get('id')}")
            log(f"  Vendor: {data.get('vendor')}")
            log(f" Currency: {data.get('currency')}")
            log(f"  Date: {data.get('date')}")
            log(f"  Total: {data.get('total')}")
            log(f"  Items Count: {len(data.get('items', []))}")
            log("-" * 50)

            return data
        except Exception as e:
            log("Failed to parse JSON from Mistral response:", e)
            log("Response was:", text_response[:500])
            return {"raw_text": ocr_text, "doc_type": "unknown"}

    except Exception as e:
        log("Mistral extraction failed:", e)
        return {"raw_text": ocr_text, "doc_type": "unknown"}


# -------- Fallback regex item parsing --------
def parse_items_from_text(text):
    items = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]  # noqa: E741
    item_pattern = re.compile(r"(.+?)\s+(\d+)\s+([$\d\.,]+)\s+([$\d\.,]+)$", re.I)

    for line in lines:
        match = item_pattern.search(line)
        if match:
            desc, qty, price, total = match.groups()
            try:
                quantity = int(qty)
                unit_price = float(price.replace('$', '').replace(',', ''))
                items.append({
                    "description": desc.strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": unit_price * quantity
                })
                continue
            except:  # noqa: E722
                pass
        money_matches = list(_money_rx.finditer(line))
        if len(money_matches) >= 1:
            quantity = 1
            qty_match = re.search(r"\b(\d+)\s*(?:x|@|\*)\b", line, re.I)
            if qty_match:
                quantity = int(qty_match.group(1))
            last_price = money_matches[-1].group(1).replace(",", "")
            try:
                price = float(last_price)
            except:  # noqa: E722
                price = None
            desc = re.sub(r"[\$\d\.,]+\s*$", "", line).strip("•- \t")
            if desc and len(desc) > 3:
                items.append({
                    "description": desc,
                    "quantity": quantity,
                    "unit_price": price,
                    "line_total": round(quantity * price, 2) if price is not None else None
                })
    log(f"Parsed {len(items)} line items")
    return items

# -------- Main structured extraction --------
def extract_structured_fields(text, doc_type_hint=None):
    log("Extracting structured fields from OCR text")
    api_key = os.getenv("MISTRAL_API_KEY") or getattr(settings, "MISTRAL_API_KEY", None)

    doc_type = classify_document_type(text)
    log(f"Document classified as: {doc_type}")

    mistral_data = {}
    if api_key:
        mistral_data = run_mistral_extraction(text, api_key)
        if mistral_data and (mistral_data.get("total") is not None or mistral_data.get("vendor") or mistral_data.get("items")):
            if mistral_data.get("doc_type") and mistral_data["doc_type"] != "unknown":
                doc_type = mistral_data["doc_type"]
            return {
                "doc_type": doc_type,
                "id": mistral_data.get("id"),
                "vendor": mistral_data.get("vendor"),
                "currency": mistral_data.get("currency"),
                "date": mistral_data.get("date"),
                "items": mistral_data.get("items") or [],
                "subtotal": mistral_data.get("subtotal"),
                "tax": mistral_data.get("tax"),
                "total": mistral_data.get("total"),
                "raw_text": mistral_data.get("raw_text") or text,
                "extraction_method": "mistral"
            }

    # Regex fallback
    result = {
        "doc_type": doc_type,
        "id": None,
        "vendor": None,
        "currency": None,
        "date": None,
        "items": [],
        "subtotal": None,
        "tax": None,
        "total": None,
        "raw_text": text,
        "extraction_method": "regex"
    }

    # ID detection
    if doc_type == "invoice" or doc_type_hint == "invoice":
        mi = _invoice_rx.search(text)
        if mi:
            result["id"] = mi.group(2).strip()
    elif doc_type == "po" or doc_type_hint in ("po", "purchase_order"):
        mpo = _po_rx.search(text)
        if mpo:
            result["id"] = mpo.group(2).strip()
    if not result["id"]:
        mi = _invoice_rx.search(text) or _po_rx.search(text)
        if mi:
            result["id"] = mi.group(2).strip()

    mv = _vendor_rx.search(text)
    if mv:
        result["vendor"] = mv.group(2).strip().split("\n")[0].strip()[:100]

    md = _date_rx.search(text)
    if md:
        result["date"] = md.group(2).strip()

    # Total detection
    total_patterns = [
        r"(grand\s*total|total\s*amount|amount\s*due|invoice\s*total|total\s*due|balance\s*due)[^\d]*([$\d\.,]+)",
        r"total[^\d]*([$\d\.,]+)",
    ]
    for pattern in total_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            if match.group(2 if match.lastindex == 2 else 1):
                try:
                    total_val = match.group(2 if match.lastindex == 2 else 1)
                    result["total"] = float(total_val.replace('$', '').replace(',', ''))
                    break
                except:  # noqa: E722
                    continue
        if result["total"] is not None:
            break
    if result["total"] is None:
        all_money = list(_money_rx.finditer(text))
        if all_money:
            try:
                last_val = all_money[-1].group(1).replace(",", "")
                result["total"] = float(last_val)
            except:  # noqa: E722
                result["total"] = None

    result["items"] = parse_items_from_text(text)
    log("Structured fields extraction complete:", {
        "doc_type": result["doc_type"],
        "id": result["id"],
        "currency": result["currency"],
        "vendor": result["vendor"],
        "total": result["total"],
        "items_count": len(result["items"])
    })
    return result
