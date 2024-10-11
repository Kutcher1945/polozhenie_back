from rest_framework import serializers
from .models import ModulesCategory, ModulesSubCategory

class ModulesCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ModulesCategory
        fields = ['id', 'name_ru', 'name_kz', 'is_deleted', 'created_at', 'updated_at']


class ModulesSubCategorySerializer(serializers.ModelSerializer):
    # Use the ModulesCategorySerializer to show all details of the related category
    module_category = ModulesCategorySerializer(read_only=True)

    class Meta:
        model = ModulesSubCategory
        fields = ['id', 'name_ru', 'name_kz', 'module_category', 'is_deleted', 'created_at', 'updated_at']