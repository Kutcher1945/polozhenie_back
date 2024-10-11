from rest_framework import viewsets, filters
from .models import ModulesCategory, ModulesSubCategory
from .serializers import ModulesCategorySerializer, ModulesSubCategorySerializer

class ModulesCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModulesCategory.objects.all()
    serializer_class = ModulesCategorySerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'name_ru', 'name_kz', 'created_at', 'updated_at']  # Added 'id' to the list of ordering fields
    ordering = ['id']  # Default ordering by 'id'

class ModulesSubCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ModulesSubCategory.objects.all()
    serializer_class = ModulesSubCategorySerializer
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'name_ru', 'name_kz', 'created_at', 'updated_at']  # Added 'id' to the list of ordering fields
    ordering = ['id']  # Default ordering by 'id'
