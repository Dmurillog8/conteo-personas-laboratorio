from django.urls import path

from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("start/", views.start_session, name="start"),
    path("stop/", views.stop_session, name="stop"),
    path("stream/", views.video_stream, name="stream"),
    path("api/stats/", views.api_stats, name="api_stats"),
    path("api/preview/", views.api_preview, name="api_preview"),
    path("snapshot/", views.save_snapshot, name="snapshot"),
    path("sessions/", views.session_list, name="sessions"),
    path("sessions/<int:pk>/", views.session_detail, name="session_detail"),
]
