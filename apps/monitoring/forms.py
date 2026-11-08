from pathlib import Path

from django import forms
from django.conf import settings

from apps.core.models import Laboratory

from .models import MonitoringSession


class StartMonitoringForm(forms.Form):
    """Configuración de una nueva sesión de conteo."""

    laboratory = forms.ModelChoiceField(
        label="Laboratorio",
        queryset=Laboratory.objects.filter(is_active=True),
        empty_label=None,
    )
    source_type = forms.ChoiceField(
        label="Fuente de video",
        choices=MonitoringSession.SourceType.choices,
        initial=MonitoringSession.SourceType.WEBCAM,
        widget=forms.RadioSelect,
    )
    webcam_index = forms.IntegerField(
        label="Número de cámara",
        min_value=0,
        max_value=10,
        initial=settings.LABCOUNT_CAMERA_INDEX,
        required=False,
    )
    video_file = forms.FileField(
        label="Archivo de video",
        required=False,
        help_text="Formatos: MP4, AVI, MOV, MKV o WEBM. Máximo 250 MB.",
    )
    detection_mode = forms.ChoiceField(
        label="Método de detección",
        choices=MonitoringSession.DetectionMode.choices,
        initial=MonitoringSession.DetectionMode.DNN,
    )
    line_orientation = forms.ChoiceField(
        label="Orientación de la línea",
        choices=MonitoringSession.LineOrientation.choices,
        initial=MonitoringSession.LineOrientation.VERTICAL,
    )
    line_position = forms.FloatField(
        label="Posición de la línea",
        min_value=0.1,
        max_value=0.9,
        initial=settings.LABCOUNT_LINE_POSITION,
    )

    allowed_extensions = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".m4v"}

    def clean(self):
        cleaned = super().clean()
        source_type = cleaned.get("source_type")
        video_file = cleaned.get("video_file")

        if source_type == MonitoringSession.SourceType.WEBCAM:
            if cleaned.get("webcam_index") is None:
                cleaned["webcam_index"] = settings.LABCOUNT_CAMERA_INDEX

        if source_type == MonitoringSession.SourceType.VIDEO:
            if not video_file:
                self.add_error(
                    "video_file", "Seleccione un archivo de video para este tipo de fuente."
                )
            else:
                extension = Path(video_file.name).suffix.lower()
                if extension not in self.allowed_extensions:
                    self.add_error(
                        "video_file",
                        "Formato no compatible. Use MP4, AVI, MOV, MKV o WEBM.",
                    )
                if video_file.size > settings.LABCOUNT_MAX_UPLOAD_MB * 1024 * 1024:
                    self.add_error(
                        "video_file",
                        f"El video supera el límite de {settings.LABCOUNT_MAX_UPLOAD_MB} MB.",
                    )
        return cleaned
