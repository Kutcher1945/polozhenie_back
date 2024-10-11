from django.db import models
from .modules_category import ModulesCategory

class ModulesSubCategory(models.Model):
    name_ru = models.CharField(max_length=255, null=True, blank=True)
    name_kz = models.CharField(max_length=255, null=True, blank=True)
    module_category = models.ForeignKey(ModulesCategory, related_name='module_category_id', on_delete=models.CASCADE, blank=True, null=True, verbose_name='Категория модуля')
    is_deleted = models.BooleanField(editable=False, default=False)
    created_at = models.DateTimeField(editable=False, auto_now=True)
    updated_at = models.DateTimeField(editable=False, auto_now=True)
    
    def __str__(self):
        return self.name_ru

    class Meta:
        db_table = 'modules_sub_category'
        verbose_name = "Подкатегория модуля"
        verbose_name_plural = "Подкатегории модулей"