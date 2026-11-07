from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


def snapshot_upload_to(instance, filename: str) -> str:
    now = timezone.localtime()
    return f"snapshots/{instance.session_id}/{now:%Y/%m/%d}/{filename}"


class MonitoringSessionQuerySet(models.QuerySet):
    def visible_to(self, user):
        if user.is_staff or user.is_superuser:
            return self
        return self.filter(created_by=user)


class MonitoringSession(models.Model):
    """Una ejecución del motor de conteo sobre una fuente de video."""

    objects = MonitoringSessionQuerySet.as_manager()

    class Status(models.TextChoices):
        RUNNING = "running", "En curso"
        STOPPED = "stopped", "Finalizada"
        ERROR = "error", "Con error"

    class SourceType(models.TextChoices):
        WEBCAM = "webcam", "Cámara web"
        VIDEO = "video", "Archivo de video"
        DEMO = "demo", "Demostración"

    class DetectionMode(models.TextChoices):
        HOG = "hog", "Personas (HOG)"
        MOTION = "motion", "Movimiento (MOG2)"
        HYBRID = "hybrid", "Híbrido (HOG + movimiento)"

    class LineOrientation(models.TextChoices):
        VERTICAL = "vertical", "Vertical"
        HORIZONTAL = "horizontal", "Horizontal"

    laboratory = models.ForeignKey(
        "core.Laboratory",
        on_delete=models.PROTECT,
        related_name="sessions",
        verbose_name="laboratorio",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="monitoring_sessions",
        verbose_name="creado por",
    )
    source_type = models.CharField(
        "tipo de fuente", max_length=20, choices=SourceType.choices, default=SourceType.WEBCAM
    )
    source_label = models.CharField("descripción de la fuente", max_length=200, blank=True)
    source_index = models.PositiveSmallIntegerField("índice de cámara", default=0)
    video_file = models.FileField(
        "archivo de video", upload_to="uploads/videos/%Y/%m/%d/", blank=True
    )
    detection_mode = models.CharField(
        "método de detección",
        max_length=20,
        choices=DetectionMode.choices,
        default=DetectionMode.HYBRID,
    )
    line_orientation = models.CharField(
        "orientación de la línea",
        max_length=10,
        choices=LineOrientation.choices,
        default=LineOrientation.VERTICAL,
    )
    line_position = models.FloatField(
        "posición de la línea",
        default=0.5,
        validators=[MinValueValidator(0.1), MaxValueValidator(0.9)],
        help_text="Proporción del ancho o alto de la imagen (0.1 a 0.9).",
    )
    status = models.CharField(
        "estado", max_length=20, choices=Status.choices, default=Status.RUNNING
    )
    started_at = models.DateTimeField("inicio", default=timezone.now)
    ended_at = models.DateTimeField("fin", null=True, blank=True)
    peak_occupancy = models.PositiveIntegerField("pico de ocupación", default=0)
    current_occupancy = models.PositiveIntegerField("ocupación actual", default=0)
    total_entries = models.PositiveIntegerField("entradas", default=0)
    total_exits = models.PositiveIntegerField("salidas", default=0)
    unique_visitors = models.PositiveIntegerField("visitantes únicos", default=0)
    last_error = models.TextField("último error", blank=True)

    class Meta:
        verbose_name = "sesión de monitoreo"
        verbose_name_plural = "sesiones de monitoreo"
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["created_by", "-started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.laboratory} · {self.started_at:%d/%m/%Y %H:%M}"

    @property
    def is_running(self) -> bool:
        return self.status == self.Status.RUNNING

    @property
    def duration_seconds(self) -> int:
        end = self.ended_at or timezone.now()
        return max(0, int((end - self.started_at).total_seconds()))

    @property
    def duration_display(self) -> str:
        total = self.duration_seconds
        hours, remainder = divmod(total, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def capacity(self) -> int:
        return self.laboratory.capacity

    @property
    def occupancy_percent(self) -> float:
        if not self.capacity:
            return 0.0
        return round((self.current_occupancy / self.capacity) * 100, 1)

    @property
    def peak_percent(self) -> float:
        if not self.capacity:
            return 0.0
        return round((self.peak_occupancy / self.capacity) * 100, 1)

    @property
    def source_description(self) -> str:
        if self.source_label:
            return self.source_label
        if self.source_type == self.SourceType.WEBCAM:
            return f"Cámara {self.source_index}"
        if self.source_type == self.SourceType.VIDEO:
            return self.video_file.name.rsplit("/", 1)[-1] if self.video_file else "Video"
        return "Escena de demostración"


class OccupancySample(models.Model):
    """Muestra periódica de ocupación para gráficas e históricos."""

    session = models.ForeignKey(
        MonitoringSession,
        on_delete=models.CASCADE,
        related_name="samples",
        verbose_name="sesión",
    )
    captured_at = models.DateTimeField("capturada", default=timezone.now)
    occupancy = models.PositiveIntegerField("ocupación", default=0)
    entries = models.PositiveIntegerField("entradas", default=0)
    exits = models.PositiveIntegerField("salidas", default=0)
    fps = models.FloatField("FPS", default=0)

    class Meta:
        verbose_name = "muestra de ocupación"
        verbose_name_plural = "muestras de ocupación"
        ordering = ["captured_at"]
        indexes = [models.Index(fields=["session", "captured_at"])]

    def __str__(self) -> str:
        return f"{self.session_id} · {self.captured_at:%H:%M:%S} · {self.occupancy}"


class CrossingEvent(models.Model):
    """Cruce de una persona por la línea virtual de conteo."""

    class Direction(models.TextChoices):
        IN = "in", "Entrada"
        OUT = "out", "Salida"

    session = models.ForeignKey(
        MonitoringSession,
        on_delete=models.CASCADE,
        related_name="crossings",
        verbose_name="sesión",
    )
    occurred_at = models.DateTimeField("ocurrido", default=timezone.now)
    direction = models.CharField("dirección", max_length=3, choices=Direction.choices)
    track_id = models.PositiveIntegerField("identificador de seguimiento")

    class Meta:
        verbose_name = "cruce de línea"
        verbose_name_plural = "cruces de línea"
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["session", "-occurred_at"])]

    def __str__(self) -> str:
        return f"{self.get_direction_display()} · pista {self.track_id}"


class Snapshot(models.Model):
    """Captura manual del video con las anotaciones de OpenCV."""

    session = models.ForeignKey(
        MonitoringSession,
        on_delete=models.CASCADE,
        related_name="snapshots",
        verbose_name="sesión",
    )
    image = models.ImageField("imagen", upload_to=snapshot_upload_to)
    occupancy = models.PositiveIntegerField("ocupación al capturar", default=0)
    created_at = models.DateTimeField("creada", auto_now_add=True)

    class Meta:
        verbose_name = "captura"
        verbose_name_plural = "capturas"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Captura de la sesión {self.session_id}"
