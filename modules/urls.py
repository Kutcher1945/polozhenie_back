from rest_framework.routers import DefaultRouter

from .views import ModulesCategoryViewSet, ModulesSubCategoryViewSet

router = DefaultRouter()
router.register(
    prefix='module-category', viewset=ModulesCategoryViewSet, basename='module-category'
)
router.register(
    prefix='module-sub-category', viewset=ModulesSubCategoryViewSet, basename='module-sub-category'
)

urlpatterns = router.urls
