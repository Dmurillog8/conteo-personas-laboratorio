from django.db import models
from django.urls import reverse


class Laboratory(models.Model):
    """Laboratorio físico monitoreado por el sistema."""

    name = models.CharField("nombre", max_length=120, unique=True)
    location = models.CharField("ubicación", max_length=200, blank=True)
    capacity = models.PositiveIntegerField("aforo máximo", default=200)
    is_active = models.BooleanField("activo", default=True)
    created_at = models.DateTimeField("creado", auto_now_add=True)

    class Meta:
        verbose_name = "laboratorio"
        verbose_name_plural = "laboratorios"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def get_absolute_url(self) -> str:
        return reverse("core:landing")
