from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Count

from ..models import (
    PurchaseOrderRef, 
    InvoiceRef,
    VerificationRun,
    VerificationItemResult,
    Discrepancy
)

from ..serializers.dashboardserializers import (
    PurchaseOrderListSerializer,
    PurchaseOrderDetailSerializer,
    InvoiceListSerializer,
    # For detail page
    MatchDataSerializer,
    PurchaseOrderWithItemsSerializer,
    InvoiceWithItemsSerializer,
    VerificationItemResultSerializer,
    DiscrepancySerializer,
)


class UploadPageDataView(APIView):
    """
    GET: Retrieve all data needed for the upload page
    
    Query Parameters:
    - po_limit: int (default: 6) - Maximum number of POs to return
    - invoice_limit: int (default: 10) - Maximum number of invoices to return
    
    Response:
    {
        "purchase_orders": [...],
        "invoices": [...],
        "summary": {
            "total_pos": int,
            "total_invoices": int,
            "pos_with_invoices": int,
            "pos_without_invoices": int
        }
    }
    """
    
    def get(self, request):
        try:
            # Get query params with defaults
            po_limit = int(request.query_params.get('po_limit', 6))
            invoice_limit = int(request.query_params.get('invoice_limit', 10))
            
            # Validate limits
            po_limit = min(max(po_limit, 1), 100)  # Between 1 and 100
            invoice_limit = min(max(invoice_limit, 1), 100)
            
            # Fetch purchase orders with invoice count annotation
            purchase_orders = PurchaseOrderRef.objects.annotate(
                invoice_count=Count('invoices')
            ).order_by('-created_at')[:po_limit]
            
            # Fetch invoices
            invoices = InvoiceRef.objects.select_related(
                'purchase_order'
            ).order_by('-created_at')[:invoice_limit]
            
            # Calculate summary statistics
            total_pos = PurchaseOrderRef.objects.count()
            total_invoices = InvoiceRef.objects.count()
            pos_with_invoices = PurchaseOrderRef.objects.annotate(
                invoice_count=Count('invoices')
            ).filter(invoice_count__gt=0).count()
            
            # Serialize data
            po_serializer = PurchaseOrderListSerializer(purchase_orders, many=True)
            invoice_serializer = InvoiceListSerializer(invoices, many=True)
            
            response_data = {
                'purchase_orders': po_serializer.data,
                'invoices': invoice_serializer.data,
                'summary': {
                    'total_pos': total_pos,
                    'total_invoices': total_invoices,
                    'pos_with_invoices': pos_with_invoices,
                    'pos_without_invoices': total_pos - pos_with_invoices,
                }
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except ValueError as e:
            return Response(
                {'error': 'Invalid query parameters', 'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'Failed to retrieve upload page data', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PurchaseOrderListView(generics.ListAPIView):
    """
    GET: List all purchase orders
    
    Query Parameters:
    - limit: int (default: 6) - Number of items per page
    - offset: int (default: 0) - Pagination offset
    
    Response:
    {
        "count": int,
        "results": [...]
    }
    """
    serializer_class = PurchaseOrderListSerializer
    
    def get_queryset(self):
        queryset = PurchaseOrderRef.objects.annotate(
            invoice_count=Count('invoices')
        ).order_by('-created_at')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        # Get pagination params
        limit = int(request.query_params.get('limit', 6))
        offset = int(request.query_params.get('offset', 0))
        
        # Validate
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        # Get queryset and apply pagination
        queryset = self.get_queryset()[offset:offset + limit]
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': PurchaseOrderRef.objects.count(),
            'results': serializer.data
        })


class PurchaseOrderDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve a single purchase order with all linked invoices
    
    URL: /api/purchase-orders/{id}/
    """
    serializer_class = PurchaseOrderDetailSerializer
    queryset = PurchaseOrderRef.objects.prefetch_related('invoices')
    lookup_field = 'id'


class InvoiceListView(generics.ListAPIView):
    """
    GET: List all invoices
    
    Query Parameters:
    - limit: int (default: 10) - Number of items per page
    - offset: int (default: 0) - Pagination offset
    - po_id: str (optional) - Filter by purchase order ID
    
    Response:
    {
        "count": int,
        "results": [...]
    }
    """
    serializer_class = InvoiceListSerializer
    
    def get_queryset(self):
        queryset = InvoiceRef.objects.select_related(
            'purchase_order'
        ).order_by('-created_at')
        
        # Filter by PO ID if provided
        po_id = self.request.query_params.get('po_id')
        if po_id:
            queryset = queryset.filter(purchase_order__purchase_order_id=po_id)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        # Get pagination params
        limit = int(request.query_params.get('limit', 10))
        offset = int(request.query_params.get('offset', 0))
        
        # Validate
        limit = min(max(limit, 1), 100)
        offset = max(offset, 0)
        
        # Get queryset and apply pagination
        queryset = self.get_queryset()[offset:offset + limit]
        serializer = self.get_serializer(queryset, many=True)
        
        # Get total count (with filters applied)
        total_count = self.get_queryset().count()
        
        return Response({
            'count': total_count,
            'results': serializer.data
        })


class InvoiceDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve a single invoice
    
    URL: /api/invoices/{id}/
    """
    serializer_class = InvoiceListSerializer
    queryset = InvoiceRef.objects.select_related('purchase_order')
    lookup_field = 'id'


class PurchaseOrderInvoicesView(generics.ListAPIView):
    """
    GET: List all invoices for a specific purchase order
    
    URL: /api/purchase-orders/{po_id}/invoices/
    """
    serializer_class = InvoiceListSerializer
    
    def get_queryset(self):
        po_id = self.kwargs.get('po_id')
        return InvoiceRef.objects.filter(
            purchase_order__id=po_id
        ).select_related('purchase_order').order_by('-created_at')
    

#------------- Detail Page views ----------------#

class ReviewPageDataView(APIView):
    """
    GET: Retrieve all data needed for the PO Review page
    
    Returns:
    - match_data: List of verification runs with match results
    - documents: PO and Invoice details with line items
    """
    
    def get(self, request):
        try:
            # Get query parameters
            po_id = request.query_params.get('po_id')
            limit = int(request.query_params.get('limit', 10))
            
            # Fetch verification runs (match data)
            verification_runs = VerificationRun.objects.select_related(
                'purchase_order', 'invoice'
            ).prefetch_related(
                'item_results', 'discrepancies'
            ).order_by('-created_at')
            
            # Filter by PO if specified
            if po_id:
                verification_runs = verification_runs.filter(
                    purchase_order__id=po_id
                )
            
            verification_runs = verification_runs[:limit]
            
            # Serialize match data
            match_serializer = MatchDataSerializer(verification_runs, many=True)
            
            # Get documents (PO and Invoices) for the first verification run
            documents = []
            if verification_runs.exists():
                first_run = verification_runs.first()
                
                if first_run.purchase_order:
                    # Get PO with items
                    po = first_run.purchase_order
                    po_serializer = PurchaseOrderWithItemsSerializer(po)
                    po_data = po_serializer.data
                    
                    documents.append({
                        'id': 1,
                        'title': 'Purchase Order',
                        'icon': 'ClipboardList',
                        'desc': f"PO #{po.purchase_order_id} - Total: ${po.total}",
                        'items': len(po_data.get('items_list', [])),
                        'type': 'po',
                        **po_data
                    })
                    
                    # Get all invoices for this PO
                    invoices = InvoiceRef.objects.filter(
                        purchase_order=po
                    ).order_by('-created_at')
                    
                    invoice_serializer = InvoiceWithItemsSerializer(invoices, many=True)
                    
                    documents.append({
                        'id': 2,
                        'title': 'Invoices',
                        'icon': 'DollarSign',
                        'desc': f"{invoices.count()} invoices for PO #{po.purchase_order_id}",
                        'items': invoices.count(),
                        'type': 'invoices',
                        'invoices': invoice_serializer.data
                    })
            
            response_data = {
                'match_data': match_serializer.data,
                'documents': documents
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': 'Failed to retrieve review page data', 'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class VerificationRunListView(generics.ListAPIView):
    """
    GET: List all verification runs (match results)
    
    Query Parameters:
    - po_id: Filter by purchase order UUID
    - invoice_id: Filter by invoice UUID
    - status: Filter by status (matched, mismatched, pending, error)
    - limit: Number of results (default: 10)
    - offset: Pagination offset (default: 0)
    """
    serializer_class = MatchDataSerializer
    
    def get_queryset(self):
        queryset = VerificationRun.objects.select_related(
            'purchase_order', 'invoice'
        ).prefetch_related(
            'item_results', 'discrepancies'
        ).order_by('-created_at')
        
        # Apply filters
        po_id = self.request.query_params.get('po_id')
        if po_id:
            queryset = queryset.filter(purchase_order__id=po_id)
        
        invoice_id = self.request.query_params.get('invoice_id')
        if invoice_id:
            queryset = queryset.filter(invoice__id=invoice_id)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        limit = int(request.query_params.get('limit', 10))
        offset = int(request.query_params.get('offset', 0))
        
        queryset = self.get_queryset()[offset:offset + limit]
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': self.get_queryset().count(),
            'results': serializer.data
        })


class VerificationRunDetailView(generics.RetrieveAPIView):
    """
    GET: Retrieve detailed verification run with all item results and discrepancies
    
    URL: /api/verification-runs/{id}/
    """
    serializer_class = MatchDataSerializer
    queryset = VerificationRun.objects.select_related(
        'purchase_order', 'invoice'
    ).prefetch_related(
        'item_results', 'discrepancies'
    )
    lookup_field = 'id'
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        
        # Include item results and discrepancies
        item_results = VerificationItemResultSerializer(
            instance.item_results.all(), many=True
        ).data
        
        discrepancies = DiscrepancySerializer(
            instance.discrepancies.all(), many=True
        ).data
        
        response_data = serializer.data
        response_data['item_results'] = item_results
        response_data['discrepancies'] = discrepancies
        
        return Response(response_data)


class VerificationItemResultsView(generics.ListAPIView):
    """
    GET: List item-level verification results for a specific verification run
    
    URL: /api/verification-runs/{run_id}/items/
    """
    serializer_class = VerificationItemResultSerializer
    
    def get_queryset(self):
        run_id = self.kwargs.get('run_id')
        return VerificationItemResult.objects.filter(
            run__id=run_id
        ).order_by('item_id')


class DiscrepancyListView(generics.ListAPIView):
    """
    GET: List all discrepancies for a specific verification run
    
    URL: /api/verification-runs/{run_id}/discrepancies/
    """
    serializer_class = DiscrepancySerializer
    
    def get_queryset(self):
        run_id = self.kwargs.get('run_id')
        return Discrepancy.objects.filter(
            run__id=run_id
        ).select_related('item_result').order_by('level', 'type')