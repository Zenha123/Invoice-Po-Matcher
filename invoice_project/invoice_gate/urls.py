# # invoice_gate/urls.py
# from django.urls import path
# from .views.uploadviews import (
#     PurchaseOrderUploadView, 
#     InvoiceUploadAndVerifyView,
# )
# from .views.dashboardviews import (
#     UploadPageDataView,
#     PurchaseOrderListView,
#     PurchaseOrderDetailView,
#     PurchaseOrderInvoicesView,
#     InvoiceListView,
#     InvoiceDetailView,
#     ReviewPageDataView,
#     VerificationRunListView,
#     VerificationRunDetailView,
#     VerificationItemResultsView,
#     DiscrepancyListView,
# )

# urlpatterns = [
#     path("po/upload/", PurchaseOrderUploadView.as_view(), name="po-upload"),
#     path("api/home/invoice/upload-and-verify/", InvoiceUploadAndVerifyView.as_view(), name="invoice-upload-verify"),

#     # Main endpoint - all data for home/upload page
#     path('upload-page-data/', 
#          UploadPageDataView.as_view(), 
#          name='home-upload-page-data'),
    
#     # Purchase Orders
#     path('api/home/purchase-orders/', 
#          PurchaseOrderListView.as_view(), 
#          name='home-purchase-orders-list'),
    
#     path('api/home/purchase-orders/<uuid:id>/', 
#          PurchaseOrderDetailView.as_view(), 
#          name='home-purchase-order-detail'),
    
#     path('api/home/purchase-orders/<uuid:po_id>/invoices/', 
#          PurchaseOrderInvoicesView.as_view(), 
#          name='home-purchase-order-invoices'),
    
#     # Invoices
#     path('api/home/invoices/', 
#          InvoiceListView.as_view(), 
#          name='home-invoices-list'),
    
#     path('api/home/invoices/<uuid:id>/', 
#          InvoiceDetailView.as_view(), 
#          name='home-invoice-detail'),
    
    
#     # ===== DASHBOARD PAGE APIs (Review Page - PO Review/Matching) =====
    
#     # Main endpoint - all data for dashboard/review page
#     path('api/dashboard/review-page-data/', 
#          ReviewPageDataView.as_view(), 
#          name='dashboard-review-page-data'),
    
#     # Verification runs (match results)
#     path('api/dashboard/verification-runs/', 
#          VerificationRunListView.as_view(), 
#          name='dashboard-verification-runs-list'),
    
#     path('api/dashboard/verification-runs/<uuid:id>/', 
#          VerificationRunDetailView.as_view(), 
#          name='dashboard-verification-run-detail'),
    
#     path('api/dashboard/verification-runs/<uuid:run_id>/items/', 
#          VerificationItemResultsView.as_view(), 
#          name='dashboard-verification-item-results'),
    
#     path('api/dashboard/verification-runs/<uuid:run_id>/discrepancies/', 
#          DiscrepancyListView.as_view(), 
#          name='dashboard-verification-discrepancies'),
# ]




from django.urls import path
from .views.uploadviews import (
    PurchaseOrderUploadView, 
    InvoiceUploadAndVerifyView,
)
from .views.dashboardviews import (
    UploadPageDataView,
    PurchaseOrderListView,
    PurchaseOrderDetailView,
    PurchaseOrderInvoicesView,
    InvoiceListView,
    InvoiceDetailView,
    ReviewPageDataView,
    VerificationRunListView,
    VerificationRunDetailView,
    VerificationItemResultsView,
    DiscrepancyListView,
)

urlpatterns = [
    # ===== HOME PAGE APIs =====

    # Purchase Order Upload
    path("home/po/upload/", PurchaseOrderUploadView.as_view(), name="po-upload"),

    # Invoice Upload & Verify
    path("home/invoice/upload-and-verify/", InvoiceUploadAndVerifyView.as_view(), name="invoice-upload-verify"),

    # Main endpoint - all data for home/upload page
    path("home/upload-page-data/", UploadPageDataView.as_view(), name="home-upload-page-data"),

    # Purchase Orders
    path("home/purchase-orders/", PurchaseOrderListView.as_view(), name="home-purchase-orders-list"),
    path("home/purchase-orders/<uuid:id>/", PurchaseOrderDetailView.as_view(), name="home-purchase-order-detail"),
    path("home/purchase-orders/<uuid:po_id>/invoices/", PurchaseOrderInvoicesView.as_view(), name="home-purchase-order-invoices"),

    # Invoices
    path("home/invoices/", InvoiceListView.as_view(), name="home-invoices-list"),
    path("home/invoices/<uuid:id>/", InvoiceDetailView.as_view(), name="home-invoice-detail"),

    # ===== DASHBOARD PAGE APIs (Review Page - PO Review/Matching) =====

    # Main endpoint - all data for dashboard/review page
    path("dashboard/review-page-data/", ReviewPageDataView.as_view(), name="dashboard-review-page-data"),

    # Verification runs (match results)
    path("dashboard/verification-runs/", VerificationRunListView.as_view(), name="dashboard-verification-runs-list"),
    path("dashboard/verification-runs/<uuid:id>/", VerificationRunDetailView.as_view(), name="dashboard-verification-run-detail"),
    path("dashboard/verification-runs/<uuid:run_id>/items/", VerificationItemResultsView.as_view(), name="dashboard-verification-item-results"),
    path("dashboard/verification-runs/<uuid:run_id>/discrepancies/", DiscrepancyListView.as_view(), name="dashboard-verification-discrepancies"),
]
