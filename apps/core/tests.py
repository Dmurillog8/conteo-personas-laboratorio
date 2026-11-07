from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Laboratory


class CoreTests(TestCase):
    def test_landing_is_public(self):
        response = self.client.get(reverse("core:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Conteo de personas")

    def test_landing_redirects_authenticated_user(self):
        user = get_user_model().objects.create_user(username="user", password="ClaveSegura123!")
        self.client.force_login(user)
        response = self.client.get(reverse("core:landing"))
        self.assertRedirects(response, reverse("monitoring:dashboard"))

    def test_health_endpoint_reports_database_and_opencv(self):
        response = self.client.get(reverse("core:health"))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["database"], "ok")
        self.assertIsNotNone(payload["opencv"])

    def test_default_laboratory_seeded(self):
        self.assertTrue(Laboratory.objects.filter(name="Laboratorio P", capacity=200).exists())
