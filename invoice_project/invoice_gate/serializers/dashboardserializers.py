# from rest_framework import serializers
# from django.utils.timesince import timesince
# from ..models import (
#     PurchaseOrder, 
#     Invoice,
#     ItemVerification,
#     Discrepancy,
#     VerificationRun,
# )


# class InvoiceListSerializer(serializers.ModelSerializer):
#     """Serializer for invoice list view"""
#     linked_po = serializers.SerializerMethodField()
#     upload_date = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Invoice
#         fields = [
#             'id',
#             'invoice_id',
#             'linked_po',
#             'issue_date',
#             'currency',
#             'subtotal',
#             'tax',
#             'total',
#             'supplier_name',
#             'source_type',
#             'upload_date',
#         ]
    
#     def get_linked_po(self, obj):
#         """Return the PO filename that this invoice is linked to"""
#         if obj.purchase_order:
#             return f"{obj.purchase_order.purchase_order_id}.pdf"
#         return None
    
#     def get_upload_date(self, obj):
#         """Return human-readable upload date"""
#         return f"{timesince(obj.created_at)} ago"


# class PurchaseOrderListSerializer(serializers.ModelSerializer):
#     """Serializer for purchase order list with invoice data"""
#     name = serializers.SerializerMethodField()
#     size = serializers.SerializerMethodField()
#     upload_date = serializers.SerializerMethodField()
#     invoice_count = serializers.SerializerMethodField()
#     status = serializers.SerializerMethodField()
    
#     class Meta:
#         model = PurchaseOrder
#         fields = [
#             'id',
#             'purchase_order_id',
#             'name',
#             'size',
#             'upload_date',
#             'currency',
#             'subtotal',
#             'tax',
#             'total',
#             'issued_date',
#             'buyer_name',
#             'supplier_name',
#             'invoice_count',
#             'status',
#         ]
    
#     def get_name(self, obj):
#         """Return filename format expected by frontend"""
#         return f"{obj.purchase_order_id}.pdf"
    
#     def get_size(self, obj):
#         """Return file size - can be stored in payload or as separate field"""
#         if obj.payload and 'file_size' in obj.payload:
#             return obj.payload['file_size']
#         return 2457600  # Default mock size
    
#     def get_upload_date(self, obj):
#         """Return human-readable upload date"""
#         return f"{timesince(obj.created_at)} ago"
    
#     def get_invoice_count(self, obj):
#         """Return count of linked invoices"""
#         return getattr(obj, 'invoice_count', 0)
    
#     def get_status(self, obj):
#         """Return status based on invoice count"""
#         count = getattr(obj, 'invoice_count', 0)
#         if count == 0:
#             return {"text": "No Invoices", "type": "pending"}
#         elif count == 1:
#             return {"text": "Invoice Ready", "type": "ready"}
#         else:
#             return {"text": f"{count} Invoices", "type": "completed"}


# class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
#     """Detailed serializer with nested invoices"""
#     name = serializers.SerializerMethodField()
#     size = serializers.SerializerMethodField()
#     upload_date = serializers.SerializerMethodField()
#     invoice_count = serializers.SerializerMethodField()
#     invoices = serializers.SerializerMethodField()
#     status = serializers.SerializerMethodField()
    
#     class Meta:
#         model = PurchaseOrder
#         fields = [
#             'id',
#             'purchase_order_id',
#             'name',
#             'size',
#             'upload_date',
#             'currency',
#             'subtotal',
#             'tax',
#             'total',
#             'issued_date',
#             'buyer_name',
#             'supplier_name',
#             'invoice_count',
#             'invoices',
#             'status',
#             'payload',
#         ]
    
#     def get_name(self, obj):
#         return f"{obj.purchase_order_id}.pdf"
    
#     def get_size(self, obj):
#         if obj.payload and 'file_size' in obj.payload:
#             return obj.payload['file_size']
#         return 2457600
    
#     def get_upload_date(self, obj):
#         return f"{timesince(obj.created_at)} ago"
    
#     def get_invoice_count(self, obj):
#         return obj.invoices.count()
    
#     def get_invoices(self, obj):
#         """Return all linked invoices"""
#         invoices = obj.invoices.all()
#         return InvoiceListSerializer(invoices, many=True).data
    
#     def get_status(self, obj):
#         count = obj.invoices.count()
#         if count == 0:
#             return {"text": "No Invoices", "type": "pending"}
#         elif count == 1:
#             return {"text": "Invoice Ready", "type": "ready"}
#         else:
#             return {"text": f"{count} Invoices", "type": "completed"}


# class UploadPageSummarySerializer(serializers.Serializer):
#     """Summary statistics for upload page"""
#     total_pos = serializers.IntegerField()
#     total_invoices = serializers.IntegerField()
#     pos_with_invoices = serializers.IntegerField()
#     pos_without_invoices = serializers.IntegerField()


# # ===== Item-level Serializers =====

# class VerificationItemResultSerializer(serializers.ModelSerializer):
#     """Serializer for individual item verification results"""
#     is_match = serializers.BooleanField()
#     quantity_match = serializers.SerializerMethodField()
#     price_match = serializers.SerializerMethodField()
    
#     class Meta:
#         model = ItemVerification
#         fields = [
#             'id',
#             'item_id',
#             'description',
#             'po_quantity',
#             'po_unit_price',
#             'invoice_quantity',
#             'invoice_unit_price',
#             'is_match',
#             'quantity_match',
#             'price_match',
#         ]
    
#     def get_quantity_match(self, obj):
#         return obj.po_quantity == obj.invoice_quantity
    
#     def get_price_match(self, obj):
#         return obj.po_unit_price == obj.invoice_unit_price


# class DiscrepancySerializer(serializers.ModelSerializer):
#     """Serializer for discrepancy details"""
#     level_display = serializers.CharField(source='get_level_display', read_only=True)
#     type_display = serializers.CharField(source='get_type_display', read_only=True)
    
#     class Meta:
#         model = Discrepancy
#         fields = [
#             'id',
#             'level',
#             'level_display',
#             'type',
#             'type_display',
#             'field',
#             'expected',
#             'actual',
#             'message',
#         ]


# # ===== Purchase Order with Items =====

# class POItemSerializer(serializers.Serializer):
#     """Serializer for PO line items from payload"""
#     id = serializers.IntegerField()
#     name = serializers.CharField()
#     quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
#     unit_price = serializers.DecimalField(max_digits=14, decimal_places=4)
#     total = serializers.DecimalField(max_digits=14, decimal_places=2)


# class PurchaseOrderWithItemsSerializer(serializers.ModelSerializer):
#     """Detailed PO serializer with line items for review page"""
#     items_list = serializers.SerializerMethodField()
#     po_number = serializers.CharField(source='purchase_order_id')
#     vendor = serializers.CharField(source='supplier_name')
#     date = serializers.DateField(source='issued_date')
#     total_amount = serializers.DecimalField(source='total', max_digits=14, decimal_places=2)
    
#     class Meta:
#         model = PurchaseOrder
#         fields = [
#             'id',
#             'po_number',
#             'vendor',
#             'date',
#             'total_amount',
#             'currency',
#             'subtotal',
#             'tax',
#             'items_list',
#         ]
    
#     def get_items_list(self, obj):
#         """Extract line items from payload"""
#         if obj.payload and 'items' in obj.payload:
#             return obj.payload['items']
#         return []


# # ===== Invoice with Items =====

# class InvoiceItemSerializer(serializers.Serializer):
#     """Serializer for invoice line items from payload"""
#     id = serializers.IntegerField()
#     name = serializers.CharField()
#     quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
#     unit_price = serializers.DecimalField(max_digits=14, decimal_places=4)
#     total = serializers.DecimalField(max_digits=14, decimal_places=2)


# class InvoiceWithItemsSerializer(serializers.ModelSerializer):
#     """Detailed invoice serializer with line items"""
#     invoice_number = serializers.CharField(source='invoice_id')
#     date = serializers.DateField(source='issue_date')
#     amount = serializers.DecimalField(source='total', max_digits=14, decimal_places=2)
#     items = serializers.SerializerMethodField()
#     status = serializers.SerializerMethodField()
    
#     class Meta:
#         model = Invoice
#         fields = [
#             'id',
#             'invoice_number',
#             'date',
#             'amount',
#             'status',
#             'currency',
#             'subtotal',
#             'tax',
#             'items',
#         ]
    
#     def get_items(self, obj):
#         """Extract line items from payload"""
#         if obj.payload and 'items' in obj.payload:
#             return obj.payload['items']
#         return []
    
#     def get_status(self, obj):
#         """Get invoice status from payload or default"""
#         if obj.payload and 'status' in obj.payload:
#             return obj.payload['status']
#         return 'Pending'


# # ===== Verification/Match Results =====

# class VerificationDetailSerializer(serializers.Serializer):
#     """Individual detail line for match data"""
#     text = serializers.CharField()
#     match = serializers.BooleanField()


# class MatchDataSerializer(serializers.ModelSerializer):
#     """Serializer for verification run results (match data)"""
#     status = serializers.SerializerMethodField()
#     icon = serializers.SerializerMethodField()
#     title = serializers.SerializerMethodField()
#     description = serializers.CharField(source='summary')
#     details = serializers.SerializerMethodField()
#     final_status = serializers.SerializerMethodField()
#     status_description = serializers.SerializerMethodField()
#     type = serializers.SerializerMethodField()
#     timestamp = serializers.SerializerMethodField()
    
#     class Meta:
#         model = VerificationRun
#         fields = [
#             'id',
#             'status',
#             'icon',
#             'title',
#             'description',
#             'details',
#             'final_status',
#             'status_description',
#             'type',
#             'timestamp',
#         ]
    
#     def get_status(self, obj):
#         """Map status to frontend format"""
#         status_map = {
#             'matched': 'perfect',
#             'mismatched': 'mismatch',
#             'pending': 'pending',
#             'error': 'error'
#         }
#         return status_map.get(obj.status, 'pending')
    
#     def get_icon(self, obj):
#         """Return icon name for frontend"""
#         return 'CheckCircle' if obj.status == 'matched' else 'XCircle'
    
#     def get_title(self, obj):
#         """Generate title based on status"""
#         if obj.status == 'matched':
#             return 'Perfect Match'
#         elif obj.status == 'mismatched':
#             return 'Discrepancy Found'
#         else:
#             return 'Verification Pending'
    
#     def get_details(self, obj):
#         """Build details list from verification data"""
#         details = []
        
#         if obj.invoice and obj.purchase_order:
#             details.append({
#                 'text': f"Invoice #{obj.invoice.invoice_id} matches PO #{obj.purchase_order.purchase_order_id}",
#                 'match': obj.linkage_ok
#             })
            
#             if obj.invoice.supplier_name:
#                 details.append({
#                     'text': f"Vendor: {obj.invoice.supplier_name}",
#                     'match': True
#                 })
            
#             details.append({
#                 'text': f"Total amount: ${obj.invoice.total}",
#                 'match': obj.totals_ok
#             })
            
#             details.append({
#                 'text': "All line items verified" if obj.status == 'matched' else f"{obj.mismatch_count} discrepancies found",
#                 'match': obj.status == 'matched'
#             })
        
#         return details
    
#     def get_final_status(self, obj):
#         """Get final approval status"""
#         if obj.status == 'matched':
#             return 'APPROVED'
#         elif obj.status == 'mismatched':
#             return 'NEEDS REVIEW'
#         else:
#             return 'PENDING'
    
#     def get_status_description(self, obj):
#         """Get status description"""
#         if obj.status == 'matched':
#             return 'No issues found'
#         elif obj.status == 'mismatched':
#             return f"{obj.mismatch_count} issue(s) detected"
#         else:
#             return 'Verification in progress'
    
#     def get_type(self, obj):
#         """Get type for frontend styling"""
#         return 'match' if obj.status == 'matched' else 'mismatch'
    
#     def get_timestamp(self, obj):
#         """Get human-readable timestamp"""
#         if obj.finished_at:
#             return f"Verified {timesince(obj.finished_at)} ago"
#         return f"Started {timesince(obj.created_at)} ago"


# class ReviewPageDocumentSerializer(serializers.Serializer):
#     """Combined document serializer for review page"""
#     id = serializers.IntegerField()
#     title = serializers.CharField()
#     icon = serializers.CharField()
#     desc = serializers.CharField()
#     items = serializers.IntegerField()
#     type = serializers.CharField()
#     # Additional fields based on type
#     po_data = serializers.DictField(required=False)
#     invoices_data = serializers.ListField(required=False)


# dashboardserializers.py

from rest_framework import serializers
from django.utils.timesince import timesince
from ..models import (
    PurchaseOrder, 
    Invoice,
    ItemVerification,
    Discrepancy,
    VerificationRun,
)


class InvoiceListSerializer(serializers.ModelSerializer):
    """Serializer for invoice list view"""
    linked_po = serializers.SerializerMethodField()
    upload_date = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_id',
            'linked_po',
            'issue_date',
            'currency',
            'subtotal',
            'tax',
            'total',
            'supplier_name',
            'source_type',
            'upload_date',
        ]
    
    def get_linked_po(self, obj):
        """Return the PO filename that this invoice is linked to"""
        if obj.purchase_order:
            return f"{obj.purchase_order.purchase_order_id}.pdf"
        return None
    
    def get_upload_date(self, obj):
        """Return human-readable upload date"""
        return f"{timesince(obj.created_at)} ago"


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    """Serializer for purchase order list with invoice data"""
    name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    upload_date = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'purchase_order_id',
            'name',
            'size',
            'upload_date',
            'currency',
            'subtotal',
            'tax',
            'total',
            'issued_date',
            'buyer_name',
            'supplier_name',
            'invoice_count',
            'status',
        ]
    
    def get_name(self, obj):
        """Return filename format expected by frontend"""
        return f"{obj.purchase_order_id}.pdf"
    
    def get_size(self, obj):
        """Return file size - can be stored in payload or as separate field"""
        if obj.payload and 'file_size' in obj.payload:
            return obj.payload['file_size']
        return 2457600  # Default mock size
    
    def get_upload_date(self, obj):
        """Return human-readable upload date"""
        return f"{timesince(obj.created_at)} ago"
    
    def get_invoice_count(self, obj):
        """Return count of linked invoices"""
        return getattr(obj, 'invoice_count', 0)
    
    def get_status(self, obj):
        """Return status based on invoice count"""
        count = getattr(obj, 'invoice_count', 0)
        if count == 0:
            return {"text": "No Invoices", "type": "pending"}
        elif count == 1:
            return {"text": "Invoice Ready", "type": "ready"}
        else:
            return {"text": f"{count} Invoices", "type": "completed"}


class PurchaseOrderDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with nested invoices"""
    name = serializers.SerializerMethodField()
    size = serializers.SerializerMethodField()
    upload_date = serializers.SerializerMethodField()
    invoice_count = serializers.SerializerMethodField()
    invoices = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'purchase_order_id',
            'name',
            'size',
            'upload_date',
            'currency',
            'subtotal',
            'tax',
            'total',
            'issued_date',
            'buyer_name',
            'supplier_name',
            'invoice_count',
            'invoices',
            'status',
            'payload',
        ]
    
    def get_name(self, obj):
        return f"{obj.purchase_order_id}.pdf"
    
    def get_size(self, obj):
        if obj.payload and 'file_size' in obj.payload:
            return obj.payload['file_size']
        return 2457600
    
    def get_upload_date(self, obj):
        return f"{timesince(obj.created_at)} ago"
    
    def get_invoice_count(self, obj):
        return obj.invoices.count()
    
    def get_invoices(self, obj):
        """Return all linked invoices"""
        invoices = obj.invoices.all()
        return InvoiceListSerializer(invoices, many=True).data
    
    def get_status(self, obj):
        count = obj.invoices.count()
        if count == 0:
            return {"text": "No Invoices", "type": "pending"}
        elif count == 1:
            return {"text": "Invoice Ready", "type": "ready"}
        else:
            return {"text": f"{count} Invoices", "type": "completed"}


class UploadPageSummarySerializer(serializers.Serializer):
    """Summary statistics for upload page"""
    total_pos = serializers.IntegerField()
    total_invoices = serializers.IntegerField()
    pos_with_invoices = serializers.IntegerField()
    pos_without_invoices = serializers.IntegerField()


# ===== Item-level Serializers =====

class VerificationItemResultSerializer(serializers.ModelSerializer):
    """Serializer for individual item verification results"""
    is_match = serializers.BooleanField()
    quantity_match = serializers.SerializerMethodField()
    price_match = serializers.SerializerMethodField()
    
    class Meta:
        model = ItemVerification
        fields = [
            'id',
            'item_id',
            'description',
            'po_quantity',
            'po_unit_price',
            'invoice_quantity',
            'invoice_unit_price',
            'is_match',
            'quantity_match',
            'price_match',
        ]
    
    def get_quantity_match(self, obj):
        return obj.po_quantity == obj.invoice_quantity
    
    def get_price_match(self, obj):
        return obj.po_unit_price == obj.invoice_unit_price


class DiscrepancySerializer(serializers.ModelSerializer):
    """Serializer for discrepancy details"""
    level_display = serializers.CharField(source='get_level_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    created_at_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Discrepancy
        fields = [
            'id',
            'level',
            'level_display',
            'type',
            'type_display',
            'field',
            'expected',
            'actual',
            'message',
            'created_at',
            'created_at_formatted',
        ]
    
    def get_created_at_formatted(self, obj):
        """Format timestamp for display"""
        return obj.created_at.strftime('%b. %d, %Y, %I:%M %p')


# ===== Purchase Order with Items =====

class POItemSerializer(serializers.Serializer):
    """Serializer for PO line items from payload"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=4)
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class PurchaseOrderWithItemsSerializer(serializers.ModelSerializer):
    """Detailed PO serializer with line items for review page"""
    items_list = serializers.SerializerMethodField()
    po_number = serializers.CharField(source='purchase_order_id')
    vendor = serializers.CharField(source='supplier_name')
    date = serializers.DateField(source='issued_date')
    total_amount = serializers.DecimalField(source='total', max_digits=14, decimal_places=2)
    
    class Meta:
        model = PurchaseOrder
        fields = [
            'id',
            'po_number',
            'vendor',
            'date',
            'total_amount',
            'currency',
            'subtotal',
            'tax',
            'items_list',
        ]
    
    def get_items_list(self, obj):
        """Extract line items from payload"""
        if obj.payload and 'items' in obj.payload:
            return obj.payload['items']
        return []


# ===== Invoice with Items =====

class InvoiceItemSerializer(serializers.Serializer):
    """Serializer for invoice line items from payload"""
    id = serializers.IntegerField()
    name = serializers.CharField()
    quantity = serializers.DecimalField(max_digits=14, decimal_places=2)
    unit_price = serializers.DecimalField(max_digits=14, decimal_places=4)
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class InvoiceWithItemsSerializer(serializers.ModelSerializer):
    """Detailed invoice serializer with line items"""
    invoice_number = serializers.CharField(source='invoice_id')
    date = serializers.DateField(source='issue_date')
    amount = serializers.DecimalField(source='total', max_digits=14, decimal_places=2)
    items = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    
    class Meta:
        model = Invoice
        fields = [
            'id',
            'invoice_number',
            'date',
            'amount',
            'status',
            'currency',
            'subtotal',
            'tax',
            'items',
        ]
    
    def get_items(self, obj):
        """Extract line items from payload"""
        if obj.payload and 'items' in obj.payload:
            return obj.payload['items']
        return []
    
    def get_status(self, obj):
        """Get invoice status from payload or default"""
        if obj.payload and 'status' in obj.payload:
            return obj.payload['status']
        return 'Pending'


# ===== Verification/Match Results =====

class VerificationDetailSerializer(serializers.Serializer):
    """Individual detail line for match data"""
    text = serializers.CharField()
    match = serializers.BooleanField()


class MatchDataSerializer(serializers.ModelSerializer):
    """Serializer for verification run results (match data)"""
    status = serializers.SerializerMethodField()
    icon = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    description = serializers.CharField(source='summary')
    details = serializers.SerializerMethodField()
    final_status = serializers.SerializerMethodField()
    status_description = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    timestamp = serializers.SerializerMethodField()
    discrepancies = serializers.SerializerMethodField()  # NEW: Add discrepancies
    
    class Meta:
        model = VerificationRun
        fields = [
            'id',
            'status',
            'icon',
            'title',
            'description',
            'details',
            'final_status',
            'status_description',
            'type',
            'timestamp',
            'discrepancies',  # NEW
        ]
    
    def get_status(self, obj):
        """Map status to frontend format"""
        status_map = {
            'matched': 'perfect',
            'mismatched': 'mismatch',
            'pending': 'pending',
            'error': 'error'
        }
        return status_map.get(obj.status, 'pending')
    
    def get_icon(self, obj):
        """Return icon name for frontend"""
        return 'CheckCircle' if obj.status == 'matched' else 'XCircle'
    
    def get_title(self, obj):
        """Generate title based on status"""
        if obj.status == 'matched':
            return 'Perfect Match'
        elif obj.status == 'mismatched':
            return 'Discrepancy Found'
        else:
            return 'Verification Pending'
    
    def get_details(self, obj):
        """Build details list from verification data"""
        details = []
        
        if obj.invoice and obj.purchase_order:
            details.append({
                'text': f"Invoice #{obj.invoice.invoice_id} matches PO #{obj.purchase_order.purchase_order_id}",
                'match': obj.linkage_ok
            })
            
            if obj.invoice.supplier_name:
                details.append({
                    'text': f"Vendor: {obj.invoice.supplier_name}",
                    'match': True
                })
            
            details.append({
                'text': f"Total amount: ${obj.invoice.total}",
                'match': obj.totals_ok
            })
            
            details.append({
                'text': "All line items verified" if obj.status == 'matched' else f"{obj.mismatch_count} discrepancies found",
                'match': obj.status == 'matched'
            })
        
        return details
    
    def get_final_status(self, obj):
        """Get final approval status"""
        if obj.status == 'matched':
            return 'APPROVED'
        elif obj.status == 'mismatched':
            return 'NEEDS REVIEW'
        else:
            return 'PENDING'
    
    def get_status_description(self, obj):
        """Get status description"""
        if obj.status == 'matched':
            return 'No issues found'
        elif obj.status == 'mismatched':
            return f"{obj.mismatch_count} issue(s) detected"
        else:
            return 'Verification in progress'
    
    def get_type(self, obj):
        """Get type for frontend styling"""
        return 'match' if obj.status == 'matched' else 'mismatch'
    
    def get_timestamp(self, obj):
        """Get human-readable timestamp"""
        if obj.finished_at:
            return f"Verified {timesince(obj.finished_at)} ago"
        return f"Started {timesince(obj.created_at)} ago"
    
    def get_discrepancies(self, obj):
        """Get all discrepancies for this verification run"""
        discrepancies = obj.discrepancies.all()
        return DiscrepancySerializer(discrepancies, many=True).data


class ReviewPageDocumentSerializer(serializers.Serializer):
    """Combined document serializer for review page"""
    id = serializers.IntegerField()
    title = serializers.CharField()
    icon = serializers.CharField()
    desc = serializers.CharField()
    items = serializers.IntegerField()
    type = serializers.CharField()
    # Additional fields based on type
    po_data = serializers.DictField(required=False)
    invoices_data = serializers.ListField(required=False)