from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Laboratory
from apps.monitoring.models import MonitoringSession, OccupancySample


class ReportsTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="reportes", password="ClaveSegura123!"
        )
        self.lab = Laboratory.objects.create(name="Laboratorio Reportes", capacity=50)
        self.session = MonitoringSession.objects.create(
            laboratory=self.lab,
            created_by=self.user,
            source_type=MonitoringSession.SourceType.DEMO,
            source_label="Demo",
            status=MonitoringSession.Status.STOPPED,
            started_at=timezone.now(),
            ended_at=timezone.now(),
            peak_occupancy=6,
            total_entries=9,
            total_exits=7,
            unique_visitors=9,
        )
        OccupancySample.objects.create(
            session=self.session, occupancy=3, entries=5, exits=2, fps=15.2
        )
        self.client.force_login(self.user)

    def test_report_page(self):
        response = self.client.get(reverse("reports:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.lab.name)

    def test_report_period_parameter(self):
        response = self.client.get(reverse("reports:index"), {"days": 7})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Últimos 7 días")

    def test_export_sessions_csv(self):
        response = self.client.get(reverse("reports:export_sessions"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        content = response.content.decode("utf-8-sig")
        self.assertIn("Entradas", content)
        self.assertIn(self.lab.name, content)

    def test_export_session_csv(self):
        response = self.client.get(reverse("reports:export_session", args=[self.session.pk]))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8-sig")
        self.assertIn("Ocupacion", content)
        self.assertIn("15.2", content)

    def test_export_other_user_session_forbidden(self):
        other = get_user_model().objects.create_user(username="ajeno", password="ClaveSegura123!")
        self.client.force_login(other)
        response = self.client.get(reverse("reports:export_session", args=[self.session.pk]))
        self.assertEqual(response.status_code, 404)
