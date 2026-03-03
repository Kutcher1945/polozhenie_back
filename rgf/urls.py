from django.urls import path
from . import views

urlpatterns = [
    path("organizations/",  views.OrganizationsView.as_view(),  name="rgf-organizations"),
    path("preview/",        views.PreviewView.as_view(),         name="rgf-preview"),
    path("import/",         views.ImportView.as_view(),          name="rgf-import"),
    path("records/",        views.RecordsView.as_view(),         name="rgf-records"),
    path("records/delete/", views.DeleteRecordsView.as_view(),   name="rgf-delete"),
]
