from unittest.mock import PropertyMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Laboratory
from apps.monitoring.models import MonitoringSession
from apps.monitoring.services.manager import StreamManager, stream_manager


class MonitoringViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="ana", password="ClaveSegura123", first_name="Ana", last_name="Pérez"
        )
        self.lab = Laboratory.objects.create(name="Laboratorio de Pruebas", capacity=30)
        self.client.force_login(self.user)

    def _session(self, **kwargs):
        defaults = {
            "laboratory": self.lab,
            "created_by": self.user,
            "source_type": MonitoringSession.SourceType.DEMO,
            "source_label": "Demo",
            "status": MonitoringSession.Status.STOPPED,
            "started_at": timezone.now(),
            "ended_at": timezone.now(),
            "peak_occupancy": 4,
            "total_entries": 8,
            "total_exits": 6,
            "unique_visitors": 8,
        }
        defaults.update(kwargs)
        return MonitoringSession.objects.create(**defaults)

    def test_dashboard_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("monitoring:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response.url)

    def test_dashboard_renders_start_form(self):
        response = self.client.get(reverse("monitoring:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "monitoring/dashboard.html")
        self.assertContains(response, "Inicia una sesión de conteo")

    def test_start_demo_session(self):
        with patch.object(StreamManager, "running", new_callable=PropertyMock) as running:
            running.return_value = False
            with patch.object(stream_manager, "start", return_value={"session_id": 1}) as start:
                response = self.client.post(
                    reverse("monitoring:start"),
                    {
                        "laboratory": self.lab.pk,
                        "source_type": MonitoringSession.SourceType.DEMO,
                        "source_index": 0,
                        "detection_mode": MonitoringSession.DetectionMode.HYBRID,
                        "line_orientation": MonitoringSession.LineOrientation.VERTICAL,
                        "line_position": "0.5",
                    },
                )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(start.called)
        session = MonitoringSession.objects.get(created_by=self.user)
        self.assertEqual(session.source_type, MonitoringSession.SourceType.DEMO)
        self.assertEqual(session.status, MonitoringSession.Status.RUNNING)
        self.assertIn("Escena de demostración", session.source_label)

    def test_cannot_start_video_without_file(self):
        with patch.object(StreamManager, "running", new_callable=PropertyMock) as running:
            running.return_value = False
            response = self.client.post(
                reverse("monitoring:start"),
                {
                    "laboratory": self.lab.pk,
                    "source_type": MonitoringSession.SourceType.VIDEO,
                    "detection_mode": MonitoringSession.DetectionMode.HYBRID,
                    "line_orientation": MonitoringSession.LineOrientation.VERTICAL,
                    "line_position": "0.5",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MonitoringSession.objects.exists())

    def test_cannot_start_second_session(self):
        with patch.object(StreamManager, "running", new_callable=PropertyMock) as running:
            running.return_value = True
            response = self.client.post(
                reverse("monitoring:start"),
                {
                    "laboratory": self.lab.pk,
                    "source_type": MonitoringSession.SourceType.DEMO,
                    "detection_mode": MonitoringSession.DetectionMode.HYBRID,
                    "line_orientation": MonitoringSession.LineOrientation.VERTICAL,
                    "line_position": "0.5",
                },
            )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(MonitoringSession.objects.exists())

    def test_stats_api(self):
        fake_stats = {
            "running": False,
            "session_id": None,
            "current": 0,
            "entries": 0,
            "exits": 0,
            "unique": 0,
            "capacity": 30,
            "percent": 0,
        }
        with patch.object(stream_manager, "get_stats", return_value=fake_stats):
            response = self.client.get(reverse("monitoring:api_stats"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["capacity"], 30)

    def test_session_list_and_filters(self):
        session = self._session()
        response = self.client.get(reverse("monitoring:sessions"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lab.name)
        response = self.client.get(reverse("monitoring:sessions"), {"status": "stopped"})
        self.assertContains(response, self.lab.name)
        response = self.client.get(reverse("monitoring:sessions"), {"status": "running"})
        self.assertNotContains(response, self.lab.name)

    def test_session_detail_is_private(self):
        session = self._session()
        other = get_user_model().objects.create_user(username="otro", password="ClaveSegura123")
        self.client.force_login(other)
        response = self.client.get(reverse("monitoring:session_detail", args=[session.pk]))
        self.assertEqual(response.status_code, 404)

    def test_session_detail_owner(self):
        session = self._session()
        response = self.client.get(reverse("monitoring:session_detail", args=[session.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(session.pk))

    def test_stop_without_active_session(self):
        with patch.object(StreamManager, "session_id", new_callable=PropertyMock) as session_id:
            session_id.return_value = None
            response = self.client.post(reverse("monitoring:stop"))
        self.assertEqual(response.status_code, 302)

    def test_stream_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("monitoring:stream"))
        self.assertEqual(response.status_code, 302)

    def test_health_endpoint(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
