# ocr_utils.py
import os
import re
import io
import json
import logging
from django.conf import settings
import fitz
from PIL import Image, ImageEnhance
import pytesseract

# Mistral SDK (latest version)
from mistralai import Mistral

# Setup logging
logger = logging.getLogger(__name__)

# Configuration constants
MAX_TEXT_LENGTH = 20000  # Increased limit
MISTRAL_TIMEOUT = 120  # Increased timeout
USE_FAST_MODEL = False  # Use mistral-large for better accuracy
MAX_PDF_PAGES = 5  # Process more pages

# -------- Regex patterns --------
_money_rx = re.compile(r"[$₹€£]?\s*([0-9]+[0-9\.,]*)")
_invoice_rx = re.compile(r"(Invoice\s*#|Invoice\s*ID|Invoice\s*:|Invoice\:|\bINV\b|\bBill\b)\s*[:\-]?\s*([A-Z0-9\-\_]+)", re.I)
_po_rx = re.compile(r"(PO\s*#|PO\s*:|Purchase\s+Order\s*ID|Purchase Order\s*#|\bP\.O\.\b)\s*[:\-]?\s*([A-Z0-9\-\_]+)", re.I)
_vendor_rx = re.compile(r"(Vendor|Supplier|From|Sold By|Billed From)\s*[:\-]?\s*([A-Za-z0-9&\.\,\-\s]+)", re.I)
_date_rx = re.compile(r"(Date|Dated|Invoice Date|Order Date)\s*[:\-]?\s*([0-9]{4}\-[0-9]{2}\-[0-9]{2}|[0-9]{2}\/[0-9]{2}\/[0-9]{4}|[A-Za-z0-9\,\-\s\/]+)", re.I)

_invoice_indicators = [
    r"invoice\s*#", r"invoice\s*id", r"tax\s*invoice", r"bill\s*to", r"amount\s*due", 
    r"subtotal", r"total\s*due", r"balance\s*due", r"invoice\s*date",
    r"tax\s*amount", r"grand\s*total", r"invoice\s*total"
]
_po_indicators = [
    r"purchase\s*order", r"po\s*#", r"po\s*id", r"ordered\s*by", r"supplier",
    r"ship\s*to", r"delivery\s*date", r"order\s*date", r"p\.o\.\s*number",
    r"purchase\s*order\s*id"
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
    
    log(f"Classification scores - Invoice: {invoice_score}, PO: {po_score}")
    
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
        # Use better config for tables and structured data
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
        
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.5)
        
        return image
    except Exception as e:
        logger.warning(f"Image preprocessing failed: {e}")
        return image


def file_to_text(filepath: str) -> str:
    """
    Convert PDF or image file to text using OCR
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
                    
                    # Try to extract text directly first (faster for text-based PDFs)
                    direct_text = page.get_text()
                    if direct_text and len(direct_text.strip()) > 50:
                        log(f"Page {i+1}: Using direct text extraction")
                        all_text.append(direct_text)
                        continue
                    
                    # If no text, use OCR
                    log(f"Page {i+1}: Using OCR")
                    pix = page.get_pixmap(dpi=300)
                    img_data = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_data))
                    
                    processed_image = preprocess_image(image)
                    page_text = run_local_ocr(processed_image)
                    
                    if page_text.strip():
                        all_text.append(page_text)
                    
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
    
    # Keep 80% from start, 20% from end
    keep_start = int(max_length * 0.8)
    keep_end = max_length - keep_start
    
    truncated = text[:keep_start] + "\n\n[... MIDDLE TRUNCATED ...]\n\n" + text[-keep_end:]
    
    log(f"Text truncated from {len(text)} to {len(truncated)} characters")
    return truncated


def clean_json_response(text: str) -> str:
    """
    Clean Mistral response to extract valid JSON
    """
    # Remove markdown code blocks
    text = text.strip()
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
    # Remove trailing commas before closing braces/brackets
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    
    # Fix unescaped newlines in strings
    text = re.sub(r'(?<!\\)\\n', r'\\\\n', text)
    
    return text


def run_mistral_extraction(ocr_text: str, api_key: str, doc_type_hint: str = None) -> dict:
    """
    Extract structured data using Mistral AI API - Optimized version
    """
    if not ocr_text or not api_key:
        return {"raw_text": ocr_text, "doc_type": "unknown"}

    try:
        # Truncate text if too long
        original_length = len(ocr_text)
        if len(ocr_text) > MAX_TEXT_LENGTH:
            ocr_text = truncate_text_smart(ocr_text, MAX_TEXT_LENGTH)
            log(f"Text truncated from {original_length} to {len(ocr_text)} chars")
        
        # Use mistral-large for better accuracy
        model = "mistral-large-latest"
        log(f"Calling Mistral API with model: {model}")
        
        client = Mistral(api_key=api_key)

        # Build document-type specific prompt
        if doc_type_hint == "po":
            doc_instruction = "This is a Purchase Order (PO) document."
            id_field = '"po_number"'
        else:
            doc_instruction = "This is an Invoice document."
            id_field = '"invoice_number"'

        prompt = f"""You are a precise financial document parser. {doc_instruction}

Extract ALL fields into a JSON object. Be extremely careful with numbers - extract them as numbers, not strings.

Required JSON structure:
{{
  "doc_type": "invoice" or "po",
  "id": "primary document number",
  "invoice_number": "for invoices only",
  "po_number": "PO reference (can be in invoice or PO)",
  "vendor": "vendor/supplier company name",
  "buyer": "buyer/customer company name", 
  "currency": "USD, EUR, INR, etc.",
  "date": "document date in YYYY-MM-DD format",
  "invoice_date": "for invoices",
  "order_date": "for POs",
  "subtotal": number or null,
  "tax": number or null,
  "total": number or null,
  "items": [
    {{
      "item_id": "item identifier",
      "description": "item name/description",
      "quantity": number,
      "unit_price": number,
      "line_total": number
    }}
  ]
}}

CRITICAL RULES:
1. Return ONLY valid JSON - no markdown, no code blocks, no explanations
2. Extract ALL numeric values as actual numbers (not strings with currency symbols)
3. For missing fields, use null (not empty string)
4. Extract ALL line items you can find
5. If this is an invoice referencing a PO, include both invoice_number and po_number
6. Parse quantities and prices very carefully
7. Ensure all items array entries have complete data

DOCUMENT TEXT:
{ocr_text}

Return ONLY the JSON object:"""

        # Call Mistral API
        response = client.chat.complete(
            model=model,
            messages=[
                {
                    "role": "system", 
                    "content": "You are a precise JSON extractor. Return ONLY valid JSON with no formatting."
                },
                {
                    "role": "user", 
                    "content": prompt
                },
            ],
            temperature=0.0,
            max_tokens=3000,
            response_format={"type": "json_object"}
        )

        # Extract response text
        text_response = response.choices[0].message.content if response.choices else ""
        
        if not text_response:
            log("Mistral returned empty response")
            return {"raw_text": ocr_text, "doc_type": "unknown", "extraction_method": "mistral_empty"}

        log(f"Mistral response received ({len(text_response)} chars)")

        # Clean and parse JSON
        try:
            cleaned_json = clean_json_response(text_response)
            data = json.loads(cleaned_json)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            logger.debug(f"Response: {text_response[:500]}")
            return {"raw_text": ocr_text, "doc_type": "unknown", "extraction_method": "mistral_parse_failed", "error": str(e)}

        # Normalize the data
        # Set primary ID
        if not data.get("id"):
            data["id"] = data.get("invoice_number") or data.get("po_number")
        
        # Ensure doc_type is set
        if not data.get("doc_type"):
            data["doc_type"] = doc_type_hint or "unknown"
        
        # Normalize numeric fields
        for field in ["subtotal", "tax", "total"]:
            if field in data:
                if isinstance(data[field], str):
                    try:
                        cleaned = re.sub(r"[^\d.]", "", data[field])
                        data[field] = float(cleaned) if cleaned else None
                    except Exception:
                        data[field] = None
                elif isinstance(data[field], (int, float)):
                    data[field] = float(data[field])

        # Normalize items array
        if "items" not in data or not isinstance(data["items"], list):
            data["items"] = []
        
        normalized_items = []
        for item in data["items"]:
            normalized_item = {
                "item_id": item.get("item_id"),
                "description": item.get("description"),
                "quantity": None,
                "unit_price": None,
                "line_total": None
            }
            
            for field in ["quantity", "unit_price", "line_total"]:
                value = item.get(field)
                if isinstance(value, str):
                    try:
                        cleaned = re.sub(r"[^\d.]", "", value)
                        normalized_item[field] = float(cleaned) if cleaned else None
                    except Exception:
                        normalized_item[field] = None
                elif isinstance(value, (int, float)):
                    normalized_item[field] = float(value)
                else:
                    normalized_item[field] = value
            
            normalized_items.append(normalized_item)
        
        data["items"] = normalized_items

        # Add metadata
        data["raw_text"] = ocr_text[:1000]
        data["extraction_method"] = "mistral"

        # Log summary
        log("=" * 60)
        log("MISTRAL EXTRACTION SUMMARY:")
        log(f"  Document Type: {data.get('doc_type')}")
        log(f"  Document ID: {data.get('id')}")
        log(f"  Invoice Number: {data.get('invoice_number')}")
        log(f"  PO Number: {data.get('po_number')}")
        log(f"  Vendor: {data.get('vendor')}")
        log(f"  Buyer: {data.get('buyer')}")
        log(f"  Currency: {data.get('currency')}")
        log(f"  Date: {data.get('date')}")
        log(f"  Subtotal: {data.get('subtotal')}")
        log(f"  Tax: {data.get('tax')}")
        log(f"  Total: {data.get('total')}")
        log(f"  Items Count: {len(data.get('items', []))}")
        if data.get('items'):
            for i, item in enumerate(data['items'], 1):
                log(f"    Item {i}: {item.get('description')} - Qty: {item.get('quantity')} - Price: {item.get('unit_price')}")
        log("=" * 60)

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
    
    # Pattern for structured item lines
    item_pattern = re.compile(r'(.+?)\s+(\d+)\s+([\d\.,]+)\s*(?:USD|EUR|INR|Rs|₹|\$|€|£)?\s+([\d\.,]+)', re.I)
    
    for line in lines:
        match = item_pattern.search(line)
        if match:
            desc, qty, price, total = match.groups()
            try:
                quantity = int(qty)
                unit_price = float(price.replace(",", ""))
                line_total = float(total.replace(",", ""))
                
                items.append({
                    "description": desc.strip(),
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "line_total": line_total
                })
                continue
            except Exception:
                pass
    
    log(f"Regex parsed {len(items)} line items")
    return items


def extract_with_regex(text: str, doc_type: str = None) -> dict:
    """
    Fallback extraction using regex patterns
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

    # Extract IDs
    invoice_match = _invoice_rx.search(text)
    po_match = _po_rx.search(text)
    
    if doc_type == "invoice" and invoice_match:
        result["id"] = invoice_match.group(2).strip()
        result["invoice_number"] = invoice_match.group(2).strip()
    elif doc_type == "po" and po_match:
        result["id"] = po_match.group(2).strip()
        result["po_number"] = po_match.group(2).strip()
    
    # If invoice references a PO, extract both
    if invoice_match and po_match:
        result["invoice_number"] = invoice_match.group(2).strip()
        result["po_number"] = po_match.group(2).strip()
        result["id"] = invoice_match.group(2).strip()

    # Extract vendor
    vendor_match = _vendor_rx.search(text)
    if vendor_match:
        result["vendor"] = vendor_match.group(2).strip().split("\n")[0].strip()[:100]

    # Extract date
    date_match = _date_rx.search(text)
    if date_match:
        result["date"] = date_match.group(2).strip()

    # Extract currency
    currency_match = re.search(r'\b(USD|EUR|GBP|INR|CAD|AUD|JPY)\b', text, re.IGNORECASE)
    if currency_match:
        result["currency"] = currency_match.group(1).upper()

    # Extract totals
    total_match = re.search(r"(grand\s*total|total)[^\d]*([\d\.,]+)", text, re.IGNORECASE)
    if total_match:
        try:
            result["total"] = float(total_match.group(2).replace(",", ""))
        except Exception:
            pass

    # Extract subtotal
    subtotal_match = re.search(r"subtotal[^\d]*([\d\.,]+)", text, re.IGNORECASE)
    if subtotal_match:
        try:
            result["subtotal"] = float(subtotal_match.group(1).replace(",", ""))
        except Exception:
            pass

    # Extract tax
    tax_match = re.search(r"tax[^\d]*([\d\.,]+)", text, re.IGNORECASE)
    if tax_match:
        try:
            result["tax"] = float(tax_match.group(1).replace(",", ""))
        except Exception:
            pass

    # Parse items
    result["items"] = parse_items_from_text(text)
    
    log(f"Regex extraction complete - Found {len(result['items'])} items")
    
    return result


def extract_structured_fields(text: str, doc_type_hint: str = None) -> dict:
    """
    Main extraction function - tries Mistral first, falls back to regex
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

    # Try Mistral extraction
    if api_key and api_key.strip():
        log("Attempting Mistral AI extraction")
        mistral_data = run_mistral_extraction(text, api_key, doc_type_hint=doc_type)
        
        # Check if successful
        if (mistral_data.get("extraction_method") == "mistral" and 
            (mistral_data.get("total") is not None or len(mistral_data.get("items", [])) > 0)):
            log("✓ Mistral extraction successful")
            return mistral_data
        else:
            log(f"✗ Mistral extraction incomplete: {mistral_data.get('extraction_method')}")
    else:
        log("No Mistral API key - skipping AI extraction")

    # Fallback to regex
    log("Using regex fallback")
    return extract_with_regex(text, doc_type)
