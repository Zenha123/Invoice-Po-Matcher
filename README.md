# 🧾 Invoice-PO Matcher

**Automated Purchase Order & Invoice Matching Tool**  
A web application for extracting, verifying, and reconciling POs and invoices efficiently.

---

## 🚀 Project Overview

The **Invoice-PO Matcher** streamlines the verification process between **Purchase Orders (POs)** and **Invoices**. Users can:

- Upload multiple invoices per PO  
- Automatically match POs with linked invoices  
- Highlight discrepancies with item-level comparison  

**Key Features:**

- 📄 Upload POs and multiple invoices (PDF, PNG, JPG)  
- 🔄 Supports multiple invoices per PO with full comparison  
- 🧠 Automated data extraction using **Tesseract OCR**  
- 🤖 Intelligent data structuring using **Mistral AI**  
- ✅ Visual dashboard to review matched, unmatched, and pending items  
- 🗂️ Detailed item-level comparison in tables  
- 🖥️ Built with **Django (backend)**, **React (frontend)**, **Docker**, and **Supabase**  
- 🌐 Hosted backend on **Render Web Service**, frontend on **Render Static Site**, DB on **Supabase**

---

## 🛠️ Tech Stack

| Layer               | Technology                                   |
|--------------------|---------------------------------------------|
| Backend             | Django, Django REST Framework               |
| Frontend            | React, React Router, Lucide Icons           |
| Database            | Supabase (PostgreSQL)                        |
| AI / NLP            | Mistral AI (Data Structuring)               |
| OCR                 | Tesseract OCR                                |
| Containerization    | Docker                                       |
| Hosting             | Render (Backend: Web Service, Frontend: Static Site) |

---

## 📂 Project Workflow

### 1️⃣ Upload Documents
- Users upload **POs** and **invoices** through a drag-and-drop UI  
- Multiple invoices can be linked to a single PO  

### 2️⃣ OCR & Extraction
- **Tesseract OCR** extracts text from PDFs and images  
- Extracted text is sent to **Mistral AI**, which parses it into **structured JSON** including:  
  - Vendor name  
  - PO/Invoice number  
  - Item descriptions  
  - Quantities & prices  

### 3️⃣ Matching & Verification
- POs and linked invoices are compared **item-by-item**  
- Status indicators:  
  - ✅ Matched  
  - ⚠️ Pending  
  - ❌ Mismatch  

### 4️⃣ Dashboard Review
- Expand items to inspect **quantities, prices, and subtotals**  
- Visual indicators show match/mismatch status  
- Supports viewing multiple invoices per PO  

### 5️⃣ Data Management
- Full **CRUD operations** through backend  
- Admin panel available to manage POs and invoices  

---

## 🗄️ Models Overview

### PurchaseOrder
| Field         | Type        | Description                     |
|---------------|------------|---------------------------------|
| id            | UUID       | Unique PO identifier            |
| name          | CharField  | PO filename                     |
| upload_date   | DateTime   | Date of upload                  |
| invoice_count | Integer    | Number of linked invoices       |
| items_list    | JSON       | List of items with quantity and price |

### Invoice
| Field     | Type        | Description                   |
|-----------|------------|-------------------------------|
| id        | UUID       | Unique Invoice identifier     |
| linked_po | ForeignKey | Associated PO                 |
| file      | FileField  | Uploaded invoice              |
| amount    | Float      | Total invoice amount          |
| items     | JSON       | Item-level details            |

### VerificationRun
| Field         | Type        | Description                     |
|---------------|------------|---------------------------------|
| id            | UUID       | Unique verification run         |
| po            | ForeignKey | Associated PO                   |
| status        | String     | Match status (Matched/Mismatch/Pending) |
| discrepancies | JSON       | List of discrepancies found     |

---

## 🔗 API Endpoints

### Upload APIs
| Endpoint                                  | Method | Description                        |
|-------------------------------------------|--------|------------------------------------|
| /api/home/po/upload/                      | POST   | Upload purchase order              |
| /api/home/invoice/upload-and-verify/     | POST   | Upload invoice and verify          |

### Fetch Data
| Endpoint                                  | Method | Description                        |
|-------------------------------------------|--------|------------------------------------|
| /api/home/upload-page-data/               | GET    | Fetch all POs and invoices         |
| /api/dashboard/review-page-data/          | GET    | Fetch matched results for review   |

### PO & Invoice Management
| Endpoint                                  | Method | Description                        |
|-------------------------------------------|--------|------------------------------------|
| /api/home/purchase-orders/                 | GET    | List all POs                       |
| /api/home/purchase-orders/<uuid:id>/      | GET    | PO details                         |
| /api/home/purchase-orders/<uuid:po_id>/invoices/ | GET | Invoices linked to PO             |
| /api/home/invoices/                        | GET    | List all invoices                  |
| /api/home/invoices/<uuid:id>/              | GET    | Invoice details                    |
| /api/dashboard/verification-runs/          | GET    | Verification runs list             |
| /api/dashboard/verification-runs/<uuid:id>/ | GET  | Verification run details           |
| /api/dashboard/verification-runs/<uuid:run_id>/discrepancies/ | GET | Discrepancy list |

---

## 📤 Document Uploads & Extraction

- Supported files: `.pdf`, `.png`, `.jpg`, `.jpeg`  
- Each PO can have **multiple invoices linked**  
- **Tesseract OCR** extracts raw text  
- **Mistral AI** structures text into JSON for analysis  
- Backend compares PO vs invoices **item-by-item**  
- Dashboard displays **match/mismatch visualization**  

---

## 🌐 Hosting Details

- **Backend:** Render Web Service  
- **Frontend:** Render Static Site  
- **Database:** Supabase (PostgreSQL)  

**Admin Panel:**  
- URL: `/admin`  
- Username: `admin@example.com`  
- Password: `Admin@123`  

**Docker Deployment:**
```bash


Tech Highlights

Multiple Invoice Support: Each PO can have multiple invoices linked and matched automatically

AI-Powered Extraction: Mistral AI structures data for precise item-level comparison

Full Docker Support: Run the project locally or in cloud environments

Hosted & Accessible: Backend + Frontend deployed on Render, DB on Supabase

📞 Contact / Support

For issues or collaboration:

Author: Zenha Fathima
Email: zenha@example.com

LinkedIn: https://www.linkedin.com/in/zenha
