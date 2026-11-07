"""Variables globales disponibles en todas las plantillas."""

from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _opencv_version() -> str:
    try:
        import cv2

        return cv2.__version__
    except Exception:  # pragma: no cover - depende del entorno
        return "no disponible"


def app_info(request):
    return {
        "APP_NAME": "LabCount",
        "APP_TAGLINE": "Conteo de personas en el laboratorio",
        "APP_VERSION": "1.0.0",
        "OPENCV_VERSION": _opencv_version(),
        "LABCOUNT_STREAM_FPS": settings.LABCOUNT_STREAM_FPS,
    }
