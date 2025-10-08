# 🧾 Invoice-PO Matcher

**Automated Purchase Order & Invoice Matching Tool**  
A web application for extracting, verifying, and reconciling POs and invoices efficiently.

---

## 🚀 Project Overview

The **Invoice-PO Matcher** streamlines the verification process between **Purchase Orders (POs)** and **Invoices**. Users can upload multiple invoices per PO, and the system intelligently matches and highlights discrepancies. Data extraction is automated using **Tesseract OCR** and structured with **Mistral AI** for accurate insights.  

**Key Features:**

- 📄 Upload POs and multiple invoices (PDF)  
- 🔄 Supports multiple invoices per PO with full comparison  
- 🧠 Automated data extraction using **Tesseract OCR**  
- 🤖 Intelligent data structuring using **Mistral AI**  
- ✅ Visual dashboard to review matched, unmatched, and pending items  
- 🗂️ Detailed item-level comparison in tables  
- 🖥️ Built with **Django (backend)**, **React (frontend)**, **Docker**, and **Supabase**  
- 🌐 Hosted backend on **[Render Web Service](https://invoice-po-matcher.onrender.com)**, frontend on **[Render Static Site](https://invoice-po-frontend.onrender.com)**, DB on **Supabase**

---

## 🛠️ Tech Stack

| Layer               | Technology                                   |
|--------------------|---------------------------------------------|
| Backend             | Django, Django REST Framework,Swagger (API Docs & Testing)               |
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
- **Tesseract OCR** extracts text from PDFs   
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

📘 **API Documentation & Testing:**  
Implemented using **Swagger UI** for interactive API exploration and testing.  
Access Swagger docs here → [https://invoice-po-matcher.onrender.com/swagger/](https://invoice-po-matcher.onrender.com/swagger/)  

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

- Supported files: `.pdf`  
- Each PO can have **multiple invoices linked**  
- **Tesseract OCR** extracts raw text  
- **Mistral AI** structures text into JSON for analysis  
- **Mistral** compares PO vs invoices **item-by-item**  
- Dashboard displays **match/mismatch visualization**  

---

## 🌐 Hosting Details

- **Backend:** [Render Web Service](https://invoice-po-matcher.onrender.com)  
- **Frontend:** [Render Static Site](https://invoice-po-frontend.onrender.com)  
- **Database:** Supabase (PostgreSQL)

**Admin Panel:**  
- URL: `http://127.0.0.1:8000/admin/`  
- Username: `admin`  
- Password: `admin`

- **Swagger API Docs:**  
- URL → [https://invoice-po-matcher.onrender.com/swagger/](https://invoice-po-matcher.onrender.com/swagger/)

---
## 🏃 **How to Run Locally**

### 🐍 **Backend (Django Setup)**
```bash
# 1️⃣ Clone repository
git clone https://github.com/Zenha123/invoice-po-matcher.git
cd invoice-po-matcher

# 2️⃣ Create and activate virtual environment
python -m venv venv
venv\Scripts\activate     # Windows
# or
source venv/bin/activate  # macOS/Linux

# 3️⃣ Install dependencies
pip install -r requirements.txt

# 4️⃣ Set up environment variables
SECRET_KEY=your_django_secret_key  
DEBUG=True  
SUPABASE_URL=your_supabase_url  
SUPABASE_KEY=your_supabase_key  
MISTRAL_API_KEY=your_mistral_api_key  

# 5️⃣ Apply migrations
python manage.py makemigrations
python manage.py migrate

# 6️⃣ Create superuser
python manage.py createsuperuser

# 7️⃣ Collect static files
python manage.py collectstatic --noinput

# 8️⃣ Run development server
python manage.py runserver
```
### ⚛️  **Frontend (React Setup)**
```
# 1️⃣ Navigate to the frontend directory: 
- cd invoice-frontend

# 2️⃣ Set up environment variables:
- VITE_API_BASE_URL=[http://127.0.0.1:8000/api](http://127.0.0.1:8000/api)
  
# 3️⃣Run the React app:
- npm run dev
```
## The backend and frontend will locally  available at:

- Backend →  [http://localhost:8000 ](http://localhost:8000 )
- Frontend → [http://localhost:5173](http://localhost:5173)

🐳 Run with Docker (Optional)
- docker-compose up --build

```
## ⚡ Tech Highlights

- 📄 **Multiple Invoice Support:** Each PO can have multiple invoices linked and matched automatically  
- 🤖 **AI-Powered Extraction:** Mistral AI structures data for precise item-level comparison  
- 🐳 **Full Docker Support:** Run the project locally or in cloud environments  
- 🌐 **Hosted & Accessible:** Backend + Frontend deployed on Render, DB on Supabase  

---

## 📞 ContactInfo 

- **Author:** Zenha Fathima  
- **Email:** fathimazenha21@gmail.com  
- **LinkedIn:** [https://www.linkedin.com/in/zenha-fathima-b37101270/](https://www.linkedin.com/in/zenha-fathima-b37101270/)  




