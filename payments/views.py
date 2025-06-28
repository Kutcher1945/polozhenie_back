from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from payments.models import HomeAppointmentKaspiPayment
from payments.serializers import HomeAppointmentKaspiPaymentSerializer

import requests
from django.conf import settings


class HomeAppointmentKaspiPaymentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = HomeAppointmentKaspiPayment.objects.select_related('customer', 'appointment')
    serializer_class = HomeAppointmentKaspiPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return self.queryset
        return self.queryset.filter(customer=user)

    def get_serializer_context(self):
        return {"request": self.request}

    @action(detail=True, methods=['post'], url_path='initiate')
    def initiate_payment(self, request, pk=None):
        """🔁 Initiates Kaspi Pay for this appointment"""
        payment = self.get_object()

        # Step 1: Prepare customer ID for Kaspi
        customer_id = str(payment.customer.pk).zfill(6)

        headers = {
            "Authorization": f"Bearer {settings.KASPI_TOKEN}",
            "X-Request-ID": f"zhan-{payment.pk}",
            "X-Caller-Name": "ZHANCARE",
            "X-Locale": "ru-RU",
            "Content-Type": "application/json",
        }

        # Step 2: Scan QR
        scan_data = {
            "qrCode": "https://kaspi.kz/pay/YourCustomQR",  # Replace with real QR code
            "customerId": customer_id
        }

        scan_resp = requests.post("https://api.kaspi.kz/api/v1/qr/scan", json=scan_data, headers=headers)
        if scan_resp.status_code != 200 or scan_resp.json().get("result", {}).get("resultCode") != "SUCCESS":
            return Response({"error": "Kaspi scan failed"}, status=400)

        data = scan_resp.json()
        payment_id = data["payment"]["paymentId"]
        payment_data = data.get("paymentData")

        # Step 3: Checkout
        checkout_data = {
            "paymentId": payment_id,
            "serviceId": payment_data["serviceId"],
            "parameters": [
                {
                    "id": payment_data["parameters"][0]["id"],
                    "value": "Вызов врача"
                }
            ]
        }

        checkout_resp = requests.post("https://api.kaspi.kz/api/v1/qr/checkout", json=checkout_data, headers=headers)
        if checkout_resp.status_code != 200 or checkout_resp.json().get("result", {}).get("resultCode") != "SUCCESS":
            return Response({"error": "Kaspi checkout failed"}, status=400)

        payment_amount = checkout_resp.json()["paymentAmount"]

        # Step 4: NotifyPayment
        notify_data = {
            "result": {
                "resultCode": "SUCCESS",
                "resultMessage": "success"
            },
            "payment": {
                "paymentId": payment_id,
                "mppPaymentId": f"zhan-{payment.pk}",
                "paymentAmount": str(payment_amount)
            },
            "customerId": customer_id
        }

        notify_resp = requests.post("https://api.kaspi.kz/api/v1/qr/notifyPayment", json=notify_data, headers=headers)
        if notify_resp.status_code != 200 or notify_resp.json().get("result", {}).get("resultCode") != "SUCCESS":
            return Response({"error": "Kaspi notify failed"}, status=400)

        # Step 5: Save result
        payment.payment_id = payment_id
        payment.mpp_payment_id = f"zhan-{payment.pk}"
        payment.amount = payment_amount
        payment.status = "paid"
        payment.receipt_url = notify_resp.json().get("linkReceipt")
        payment.receipt_pdf = notify_resp.json().get("pdfReceipt")
        payment.save()

        return Response({
            "status": "paid",
            "receipt_url": payment.receipt_url,
            "receipt_pdf": payment.receipt_pdf
        }, status=status.HTTP_200_OK)
