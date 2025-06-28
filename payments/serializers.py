from rest_framework import serializers
from payments.models import HomeAppointmentKaspiPayment


class HomeAppointmentKaspiPaymentSerializer(serializers.ModelSerializer):
    customer_id = serializers.IntegerField(source='customer.id', read_only=True)
    customer_email = serializers.EmailField(source='customer.email', read_only=True)
    is_paid = serializers.BooleanField(read_only=True)

    class Meta:
        model = HomeAppointmentKaspiPayment
        fields = [
            'id',
            'appointment',
            'customer_id',
            'customer_email',
            'payment_id',
            'mpp_payment_id',
            'amount',
            'status',
            'is_paid',
            'receipt_url',
            'receipt_pdf',
            'created_at',
        ]
        read_only_fields = [
            'payment_id',
            'mpp_payment_id',
            'status',
            'receipt_url',
            'receipt_pdf',
            'created_at',
            'is_paid',
        ]
