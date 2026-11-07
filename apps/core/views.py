from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET


@require_GET
def landing(request):
    """Página pública de presentación del proyecto."""
    if request.user.is_authenticated:
        return redirect("monitoring:dashboard")
    return render(request, "core/landing.html")


@require_GET
def health(request):
    """Comprobación sencilla de estado para despliegue y monitoreo."""
    database_ok = True
    database_error = ""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception as exc:  # pragma: no cover - depende de la BD
        database_ok = False
        database_error = str(exc)

    try:
        import cv2

        opencv_version = cv2.__version__
    except Exception:  # pragma: no cover
        opencv_version = None

    healthy = database_ok and opencv_version is not None
    return JsonResponse(
        {
            "status": "ok" if healthy else "error",
            "database": "ok" if database_ok else "error",
            "database_error": database_error if not database_ok else "",
            "opencv": opencv_version,
            "service": "LabCount",
            "version": "1.0.0",
        },
        status=200 if healthy else 503,
    )
