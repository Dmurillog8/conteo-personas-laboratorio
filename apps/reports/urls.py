from django.urls import path

from . import views

app_name = "reports"

urlpatterns = [
    path("", views.index, name="index"),
    path("export/sessions/", views.export_sessions, name="export_sessions"),
    path("export/session/<int:pk>/", views.export_session, name="export_session"),
]
