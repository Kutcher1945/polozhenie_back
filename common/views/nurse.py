"""
Nurse-specific views
"""
import logging
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from ..permissions import IsNurse

logger = logging.getLogger(__name__)


class NurseViewSet(ViewSet):
    """Nurse-specific endpoints"""
    permission_classes = [IsAuthenticated, IsNurse]

    @swagger_auto_schema(operation_description="Nurse Dashboard")
    @action(detail=False, methods=["get"], url_path="dashboard")
    def dashboard(self, request):
        """Nurse dashboard"""
        return Response({"message": "Welcome, Nurse!"})
