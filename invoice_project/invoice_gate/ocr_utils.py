import os
import re
import io
import json
import logging
from django.conf import settings
import fitz
from PIL import Image, ImageEnhance
import pytesseract

# New Mistral SDK
from mistralai import Mistral

# Setup logging
logger = logging.getLogger(__name__)

# Configuration constants
MAX_TEXT_LENGTH = 15000  # Maximum characters to send to Mistral API
MISTRAL_TIMEOUT = 90  # Seconds for Mistral API timeout
USE_FAST_MODEL = True  # Use mistral-small for faster processing
MAX_PDF_PAGES = 3  # Only process first N pages of PDF

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
    """Logging helper"""
    logger.info(f"[OCR] {msg} {' '.join(map(str, args))}")


def classify_document_type(text):
    """
    Classify document as 'invoice', 'po', or 'unknown' based on keyword patterns
    """
    text_lower = text.lower()
    invoice_score = sum(1 for p in _invoice_indicators if re.search(p, text_lower))
    po_score = sum(1 for p in _po_indicators if re.search(p, text_lower))
    
    if invoice_score > po_score:
        return "invoice"
    elif po_score > invoice_score:
        return "po"
    return "unknown"


def run_local_ocr(image: Image.Image) -> str:
    """
    Run Tesseract OCR on a PIL Image
    """
    log("Running local OCR with pytesseract")
    try:
        config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=config)
        log(f"OCR extracted {len(text)} characters")
        return text
    except Exception as e:
        logger.error(f"pytesseract failed: {e}")
        return ""


def preprocess_image(image: Image.Image) -> Image.Image:
    """
    Preprocess image for better OCR results
    """
    try:
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        return image
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image


def file_to_text(filepath: str) -> str:
    """
    Convert PDF or image file to text using OCR
    Optimized for large files - only processes first few pages
    """
    log("Processing file:", filepath)
    ext = os.path.splitext(filepath)[1].lower()
    
    try:
        if ext == ".pdf":
            log("PDF detected, converting pages to images using PyMuPDF")
            doc = fitz.open(filepath)
            all_text = []
            
            total_pages = len(doc)
            pages_to_process = min(total_pages, MAX_PDF_PAGES)
            log(f"PDF has {total_pages} pages, processing first {pages_to_process}")
            
            for i in range(pages_to_process):
                try:
                    log(f"Processing page {i+1}/{pages_to_process}")
                    page = doc[i]
                    
                    # Convert page to image at 300 DPI
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Preprocess and OCR
                    processed_image = preprocess_image(image)
                    page_text = run_local_ocr(processed_image)
                    
                    if page_text.strip():
                        all_text.append(page_text)
                    
                    # Clean up
                    del pix, image, processed_image
                    
                except Exception as page_error:
                    logger.error(f"Error processing page {i+1}: {page_error}")
                    continue
            
            doc.close()
            final_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
            log(f"PDF processing complete. Total text length: {len(final_text)}")
            return final_text
            
        else:
            # Image file
            log("Image file detected")
            image = Image.open(filepath)
            processed_image = preprocess_image(image)
            text = run_local_ocr(processed_image)
            log(f"Image processing complete. Text length: {len(text)}")
            return text
            
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        return ""


def truncate_text_smart(text: str, max_length: int) -> str:
    """
    Smart text truncation - keeps beginning and end of document
    """
    if len(text) <= max_length:
        return text
    
    # Keep 70% from start, 30% from end
    keep_start = int(max_length * 0.7)
    keep_end = max_length - keep_start
    
    truncated = text[:keep_start] + "\n\n[... MIDDLE SECTION TRUNCATED ...]\n\n" + text[-keep_end:]
    
    log(f"Text truncated from {len(text)} to {len(truncated)} characters")
    return truncated


def run_mistral_extraction(ocr_text: str, api_key: str, doc_type_hint: str = None) -> dict:
    """
    Extract structured data using Mistral AI API
    Optimized with timeout handling and text truncation
    """
    if not ocr_text or not api_key:
        return {"raw_text": ocr_text, "doc_type": "unknown"}

    try:
        # Truncate text if too long
        original_length = len(ocr_text)
        if len(ocr_text) > MAX_TEXT_LENGTH:
            ocr_text = truncate_text_smart(ocr_text, MAX_TEXT_LENGTH)
            log(f"Text truncated from {original_length} to {len(ocr_text)} chars for Mistral API")
        
        # Choose model based on configuration
        model = "mistral-small-latest" if USE_FAST_MODEL else "mistral-large-latest"
        log(f"Calling Mistral API with model: {model}")
        
        client = Mistral(api_key=api_key)

        # Build document-type specific prompt
        if doc_type_hint == "po":
            doc_instruction = "This is a Purchase Order document."
            expected_fields = """
            "po_number": "PO identifier",
            "order_date": "date when order was placed",
            "requested_by": "person/department who requested",
            """
        else:
            doc_instruction = "This is an Invoice document."
            expected_fields = """
            "invoice_number": "invoice identifier",
            "invoice_date": "date of invoice",
            "po_number": "referenced PO number if any",
            """

        prompt = f"""You are a precise document parser. {doc_instruction}

Extract ALL available fields into JSON with this exact structure:

{{
  "doc_type": "invoice" or "po",
  "id": "document number",
  {expected_fields}
  "vendor": "vendor/supplier name",
  "currency": "currency code (USD, EUR, INR, etc.)",
  "date": "date in YYYY-MM-DD format if possible",
  "subtotal": numeric value or null,
  "tax": numeric value or null,
  "total": numeric value or null,
  "items": [
    {{
      "description": "item description",
      "quantity": numeric value,
      "unit_price": numeric value,
      "line_total": numeric value
    }}
  ]
}}

IMPORTANT RULES:
1. Return ONLY valid JSON, no markdown or explanations
2. Extract ALL numeric values as numbers, not strings
3. Use null for missing fields
4. Extract as many line items as you can find
5. If you find a PO reference in an invoice, include it as "po_number"

OCR TEXT:
{ocr_text}
"""

        # Call Mistral API with timeout
        response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a JSON extractor for financial documents. Return ONLY valid JSON with no markdown formatting."
                },
                {
                    "role": "user", 
                    "content": prompt
                },
            ],
            temperature=0.1,
            max_tokens=2500,
            response_format={"type": "json_object"}  # Force JSON response
        )

        # Extract response text
        text_response = response.choices[0].message.content if response.choices else ""
        
        if not text_response:
            log("Mistral returned empty response")
            return {"raw_text": ocr_text, "doc_type": "unknown", "extraction_method": "mistral_failed"}

        log(f"Mistral response received ({len(text_response)} chars)")

        # Parse JSON response
        try:
            # Try direct JSON parse first
            data = json.loads(text_response)
        except json.JSONDecodeError:
            # Fallback: extract JSON from markdown code blocks
            json_match = re.search(r"```json\s*(\{[\s\S]*?\})\s*```", text_response)
            if not json_match:
                json_match = re.search(r"(\{[\s\S]*\})", text_response)
            
            if json_match:
                json_text = json_match.group(1)
                try:
                    data = json.loads(json_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from Mistral: {e}")
                    logger.debug(f"Response was: {text_response[:500]}")
                    return {"raw_text": ocr_text, "doc_type": "unknown", "extraction_method": "mistral_parse_failed"}
            else:
                logger.error("No JSON found in Mistral response")
                return {"raw_text": ocr_text, "doc_type": "unknown", "extraction_method": "mistral_no_json"}

        # Normalize numeric fields
        for field in ["subtotal", "tax", "total"]:
            if isinstance(data.get(field), str):
                try:
                    # Remove non-numeric characters except decimal point
                    cleaned = re.sub(r"[^\d.]", "", data[field])
                    data[field] = float(cleaned) if cleaned else None
                except Exception:
                    data[field] = None

        # Normalize items array
        if "items" not in data or not isinstance(data["items"], list):
            data["items"] = []
        
        for item in data["items"]:
            for field in ["quantity", "unit_price", "line_total"]:
                if isinstance(item.get(field), str):
                    try:
                        cleaned = re.sub(r"[^\d.]", "", item[field])
                        item[field] = float(cleaned) if cleaned else None
                    except Exception:
                        item[field] = None

        # Add metadata
        data["raw_text"] = ocr_text[:1000]  # Store only first 1000 chars
        data["extraction_method"] = "mistral"

        # Log summary
        log("Mistral Extraction Summary:")
        log(f"  Document Type: {data.get('doc_type')}")
        log(f"  Document ID: {data.get('id')}")
        log(f"  Vendor: {data.get('vendor')}")
        log(f"  Currency: {data.get('currency')}")
        log(f"  Date: {data.get('date')}")
        log(f"  Total: {data.get('total')}")
        log(f"  Items Count: {len(data.get('items', []))}")
        log("-" * 50)

        return data

    except Exception as e:
        logger.error(f"Mistral extraction failed: {e}", exc_info=True)
        return {
            "raw_text": ocr_text, 
            "doc_type": "unknown", 
            "extraction_method": "mistral_exception",
            "error": str(e)
        }


def parse_items_from_text(text: str) -> list:
    """
    Fallback: Parse line items using regex patterns
    """
    items = []
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Pattern 1: Description Qty Price Total
    item_pattern = re.compile(r"(.+?)\s+(\d+)\s+([$₹€£\d\.,]+)\s+([$₹€£\d\.,]+)$", re.I)
    
    for line in lines:
        match = item_pattern.search(line)
        if match:
            desc, qty, price, total = match.groups()
            try:
                quantity = int(qty)
                unit_price = float(re.sub(r"[^\d.]", "", price))
                line_total = float(re.sub(r"[^\d.]", "", total))
                
                items.append({
                    "description": desc.strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total
                })
                continue
            except Exception:
                pass
        
        # Pattern 2: Any line with monetary values
        money_matches = list(_money_rx.finditer(line))
        if len(money_matches) >= 1:
            # Try to extract quantity
            quantity = 1
            qty_match = re.search(r"\b(\d+)\s*(?:x|@|\*|qty|quantity)\b", line, re.I)
            if qty_match:
                try:
                    quantity = int(qty_match.group(1))
                except Exception:
                    quantity = 1
            
            # Last monetary value is likely the line total or unit price
            last_price = money_matches[-1].group(1).replace(",", "")
            try:
                price = float(last_price)
            except Exception:
                price = None
            
            # Extract description (everything before monetary values)
            desc = re.sub(r"[\$₹€£\d\.,]+\s*$", "", line).strip("•- \t")
            
            if desc and len(desc) > 3:
                items.append({
                    "description": desc,
                    "quantity": quantity,
                    "unit_price": price,
                    "line_total": round(quantity * price, 2) if price is not None else None
                })
    
    log(f"Regex parsed {len(items)} line items")
    return items


def extract_with_regex(text: str, doc_type: str = None) -> dict:
    """
    Fallback extraction using regex patterns when Mistral fails
    """
    log("Using regex-based extraction")
    
    result = {
        "doc_type": doc_type or "unknown",
        "id": None,
        "vendor": None,
        "currency": None,
        "date": None,
        "items": [],
        "subtotal": None,
        "tax": None,
        "total": None,
        "raw_text": text[:1000],
        "extraction_method": "regex"
    }

    # Extract ID based on document type
    if doc_type == "invoice":
        mi = _invoice_rx.search(text)
        if mi:
            result["id"] = mi.group(2).strip()
    elif doc_type == "po":
        mpo = _po_rx.search(text)
        if mpo:
            result["id"] = mpo.group(2).strip()
    
    # Fallback: try both patterns
    if not result["id"]:
        mi = _invoice_rx.search(text) or _po_rx.search(text)
        if mi:
            result["id"] = mi.group(2).strip()

    # Extract vendor
    mv = _vendor_rx.search(text)
    if mv:
        result["vendor"] = mv.group(2).strip().split("\n")[0].strip()[:100]

    # Extract date
    md = _date_rx.search(text)
    if md:
        result["date"] = md.group(2).strip()

    # Extract currency
    currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD|JPY|CNY|Rs|₹|\$|€|£)\b', text, re.IGNORECASE)
    if currency_match:
        result["currency"] = currency_match.group(1)

    # Extract total
    total_patterns = [
        r"(grand\s*total|total\s*amount|amount\s*due|invoice\s*total|total\s*due|balance\s*due)[^\d]*([$₹€£\d\.,]+)",
        r"total[^\d]*([$₹€£\d\.,]+)",
    ]
    
    for pattern in total_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            try:
                total_str = match.group(2 if match.lastindex == 2 else 1)
                result["total"] = float(re.sub(r"[^\d.]", "", total_str))
                break
            except Exception:
                continue
        if result["total"] is not None:
            break
    
    # Fallback: use last monetary value as total
    if result["total"] is None:
        all_money = list(_money_rx.finditer(text))
        if all_money:
            try:
                last_val = all_money[-1].group(1).replace(",", "")
                result["total"] = float(last_val)
            except Exception:
                pass

    # Extract subtotal
    subtotal_match = re.search(r"(sub[\s\-]?total)[^\d]*([$₹€£\d\.,]+)", text, re.IGNORECASE)
    if subtotal_match:
        try:
            result["subtotal"] = float(re.sub(r"[^\d.]", "", subtotal_match.group(2)))
        except Exception:
            pass

    # Extract tax
    tax_patterns = [
        r"(tax|vat|gst)[^\d]*([$₹€£\d\.,]+)",
        r"(tax\s*amount|vat\s*amount)[^\d]*([$₹€£\d\.,]+)"
    ]
    for pattern in tax_patterns:
        tax_match = re.search(pattern, text, re.IGNORECASE)
        if tax_match:
            try:
                result["tax"] = float(re.sub(r"[^\d.]", "", tax_match.group(2)))
                break
            except Exception:
                continue

    # Parse items
    result["items"] = parse_items_from_text(text)
    
    log("Regex extraction complete:", {
        "doc_type": result["doc_type"],
        "id": result["id"],
        "vendor": result["vendor"],
        "total": result["total"],
        "items_count": len(result["items"])
    })
    
    return result


def extract_structured_fields(text: str, doc_type_hint: str = None) -> dict:
    """
    Main extraction function - tries Mistral first, falls back to regex
    
    Args:
        text: OCR extracted text
        doc_type_hint: Optional hint about document type ('invoice', 'po')
    
    Returns:
        Dictionary with structured document data
    """
    log("Starting structured field extraction")
    log(f"Text length: {len(text)} characters")
    
    # Classify document type
    doc_type = classify_document_type(text)
    if doc_type_hint:
        doc_type = doc_type_hint
    log(f"Document classified as: {doc_type}")

    # Get Mistral API key
    api_key = os.getenv("MISTRAL_API_KEY") or getattr(settings, "MISTRAL_API_KEY", None)

    # Try Mistral extraction first
    if api_key and api_key.strip():
        log("Mistral API key found, attempting AI extraction")
        mistral_data = run_mistral_extraction(text, api_key, doc_type_hint=doc_type)
        
        # Check if Mistral extraction was successful
        if (mistral_data.get("extraction_method") == "mistral" and 
            (mistral_data.get("total") is not None or 
             mistral_data.get("vendor") or 
             len(mistral_data.get("items", [])) > 0)):
            
            log("Mistral extraction successful, using AI results")
            
            # Override doc_type if Mistral determined it
            if mistral_data.get("doc_type") and mistral_data["doc_type"] != "unknown":
                doc_type = mistral_data["doc_type"]
            
            return {
                "doc_type": doc_type,
                "id": mistral_data.get("id") or mistral_data.get("invoice_number") or mistral_data.get("po_number"),
                "vendor": mistral_data.get("vendor"),
                "currency": mistral_data.get("currency"),
                "date": mistral_data.get("date") or mistral_data.get("invoice_date") or mistral_data.get("order_date"),
                "items": mistral_data.get("items", []),
                "subtotal": mistral_data.get("subtotal"),
                "tax": mistral_data.get("tax"),
                "total": mistral_data.get("total"),
                "raw_text": text[:1000],
                "extraction_method": "mistral",
                "po_number": mistral_data.get("po_number"),  # For invoices referencing POs
                "requested_by": mistral_data.get("requested_by"),  # For POs
                "buyer": mistral_data.get("buyer"),  # For POs
            }
        else:
            log(f"Mistral extraction failed or incomplete: {mistral_data.get('extraction_method')}")
    else:
        log("No Mistral API key found, skipping AI extraction")

    # Fallback to regex extraction
    log("Using regex fallback extraction")
    return extract_with_regex(text, doc_type)














