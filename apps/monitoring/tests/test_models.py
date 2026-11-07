from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.core.models import Laboratory
from apps.monitoring.models import MonitoringSession


class MonitoringSessionModelTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="monitor", password="ClaveSegura123"
        )
        self.lab = Laboratory.objects.create(name="Lab A", capacity=20)
        self.start = timezone.now() - timedelta(seconds=125)
        self.session = MonitoringSession.objects.create(
            laboratory=self.lab,
            created_by=self.user,
            source_type=MonitoringSession.SourceType.DEMO,
            source_label="Demo",
            current_occupancy=3,
            peak_occupancy=7,
            total_entries=15,
            total_exits=12,
            unique_visitors=15,
            started_at=self.start,
            ended_at=self.start + timedelta(seconds=125),
            status=MonitoringSession.Status.STOPPED,
        )

    def test_duration_and_percentages(self):
        self.assertEqual(self.session.duration_seconds, 125)
        self.assertEqual(self.session.duration_display, "02:05")
        self.assertEqual(self.session.occupancy_percent, 15.0)
        self.assertEqual(self.session.peak_percent, 35.0)

    def test_source_description(self):
        self.assertEqual(self.session.source_description, "Demo")
        self.session.source_label = ""
        self.assertEqual(self.session.source_description, "Escena de demostración")

    def test_visible_queryset_filters_by_owner(self):
        other = get_user_model().objects.create_user(username="otro", password="ClaveSegura123")
        MonitoringSession.objects.create(
            laboratory=self.lab,
            created_by=other,
            source_type=MonitoringSession.SourceType.DEMO,
            status=MonitoringSession.Status.STOPPED,
        )
        self.assertEqual(MonitoringSession.objects.visible_to(self.user).count(), 1)
        other.is_staff = True
        other.save(update_fields=["is_staff"])
        self.assertEqual(MonitoringSession.objects.visible_to(other).count(), 2)

    def test_capacity_and_running_properties(self):
        self.assertEqual(self.session.capacity, 20)
        self.assertFalse(self.session.is_running)
        self.session.status = MonitoringSession.Status.RUNNING
        self.assertTrue(self.session.is_running)
