from rest_framework import serializers


class POUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    filename = serializers.CharField(required=False, allow_blank=True)  # optional override


class POReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = None  # set in view when used dynamically


class InvoiceUploadSerializer(serializers.Serializer):
    file = serializers.FileField(write_only=True)
    filename = serializers.CharField(required=False, allow_blank=True)
    purchase_order_id = serializers.CharField(required=False, allow_blank=True)  # optional explicit link

class InvoiceReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = None  # set dynamically in view


class VerificationRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = None  # set dynamically in view
        fields = '__all__'

