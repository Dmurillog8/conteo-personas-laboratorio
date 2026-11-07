from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AccountsTests(TestCase):
    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Inicia sesión")

    def test_register_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "María",
                "last_name": "López",
                "email": "maria@example.com",
                "username": "marialopez",
                "password1": "ClaveSegura123!",
                "password2": "ClaveSegura123!",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("monitoring:dashboard"))
        user = get_user_model().objects.get(username="marialopez")
        self.assertEqual(user.email, "maria@example.com")
        self.assertTrue(user.check_password("ClaveSegura123!"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), user.pk)

    def test_register_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existente", email="correo@example.com", password="ClaveSegura123!"
        )
        response = self.client.post(
            reverse("accounts:register"),
            {
                "first_name": "Otra",
                "last_name": "Persona",
                "email": "CORREO@example.com",
                "username": "nueva",
                "password1": "OtraClave123!",
                "password2": "OtraClave123!",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe una cuenta")
        self.assertFalse(get_user_model().objects.filter(username="nueva").exists())

    def test_login_with_valid_credentials(self):
        get_user_model().objects.create_user(username="usuario", password="ClaveSegura123!")
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "usuario", "password": "ClaveSegura123!"},
        )
        self.assertRedirects(response, reverse("monitoring:dashboard"))

    def test_logout_requires_post_and_redirects(self):
        user = get_user_model().objects.create_user(username="salir", password="ClaveSegura123!")
        self.client.force_login(user)
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("core:landing"))
