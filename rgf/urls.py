from django.urls import path
from . import views

urlpatterns = [
    path("auth/",           views.AuthView.as_view(),           name="rgf-auth"),
    path("organizations/",  views.OrganizationsView.as_view(),  name="rgf-organizations"),
    path("preview/",        views.PreviewView.as_view(),         name="rgf-preview"),
    path("import/",         views.ImportView.as_view(),          name="rgf-import"),
    path("import-parsed/",  views.ImportParsedView.as_view(),    name="rgf-import-parsed"),
    path("records/",        views.RecordsView.as_view(),         name="rgf-records"),
    path("records/delete/", views.DeleteRecordsView.as_view(),   name="rgf-delete"),
    path("audit/",          views.AuditLogView.as_view(),        name="rgf-audit"),
    path("ai-analyze/",    views.AiAnalyzeView.as_view(),       name="rgf-ai-analyze"),
]
