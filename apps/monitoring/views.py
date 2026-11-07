import logging
from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Avg, Count, Max, Q, Sum
from django.http import HttpResponseForbidden, JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from apps.core.models import Laboratory

from .forms import StartMonitoringForm
from .models import CrossingEvent, MonitoringSession, OccupancySample, Snapshot
from .services.manager import StreamSourceError, placeholder_jpeg, stream_manager

logger = logging.getLogger("apps.monitoring")


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def visible_sessions(user):
    return MonitoringSession.objects.visible_to(user).select_related(
        "laboratory", "created_by"
    )


def reconcile_stale_sessions() -> int:
    """Marca como error las sesiones que quedaron 'en curso' tras un reinicio."""
    if stream_manager.running:
        return 0
    updated = MonitoringSession.objects.filter(
        status=MonitoringSession.Status.RUNNING
    ).update(
        status=MonitoringSession.Status.ERROR,
        ended_at=timezone.now(),
        current_occupancy=0,
        last_error="El servicio se reinició mientras la sesión estaba en curso.",
    )
    if updated:
        logger.warning("Se reconciliaron %s sesiones interrumpidas.", updated)
    return updated


def history_payload(session_id: int, limit: int = 90) -> list[dict]:
    samples = list(
        OccupancySample.objects.filter(session_id=session_id)
        .order_by("-captured_at")
        .values("captured_at", "occupancy", "entries", "exits")[:limit]
    )
    samples.reverse()
    return [
        {
            "t": timezone.localtime(sample["captured_at"]).isoformat(),
            "y": sample["occupancy"],
            "entries": sample["entries"],
            "exits": sample["exits"],
        }
        for sample in samples
    ]


def _form_defaults() -> dict:
    first_lab = Laboratory.objects.filter(is_active=True).first()
    return {
        "laboratory": first_lab,
        "source_type": MonitoringSession.SourceType.WEBCAM,
        "webcam_index": settings.LABCOUNT_CAMERA_INDEX,
        "detection_mode": settings.LABCOUNT_DEFAULT_DETECTOR,
        "line_orientation": settings.LABCOUNT_LINE_ORIENTATION,
        "line_position": settings.LABCOUNT_LINE_POSITION,
    }


# ---------------------------------------------------------------------------
# Panel principal
# ---------------------------------------------------------------------------
@login_required
def dashboard(request):
    reconcile_stale_sessions()
    stats = stream_manager.get_stats()
    active_session = None
    if stats.get("session_id"):
        active_session = (
            MonitoringSession.objects.select_related("laboratory", "created_by")
            .filter(pk=stats["session_id"])
            .first()
        )

    live = bool(stats.get("running") and active_session)
    stats["can_control"] = stream_manager.can_control(request.user) if live else False
    stats["owner"] = (
        active_session.created_by.get_full_name() or active_session.created_by.username
        if active_session and active_session.created_by
        else ""
    )
    history = history_payload(active_session.pk) if live else []

    recent_sessions = visible_sessions(request.user)[:5]
    laboratories = Laboratory.objects.filter(is_active=True)
    form = StartMonitoringForm(initial=_form_defaults())

    context = {
        "stats": stats,
        "live": live,
        "active_session": active_session,
        "history": history,
        "recent_sessions": recent_sessions,
        "laboratories": laboratories,
        "form": form,
        "system": {
            "database": "PostgreSQL" if connection.vendor == "postgresql" else connection.vendor,
            "opencv": __import__("cv2").__version__,
            "frame_rate": settings.LABCOUNT_STREAM_FPS,
        },
    }
    return render(request, "monitoring/dashboard.html", context)


# ---------------------------------------------------------------------------
# Control de sesiones
# ---------------------------------------------------------------------------
@login_required
@require_POST
def start_session(request):
    reconcile_stale_sessions()
    if stream_manager.running:
        messages.warning(
            request, "Ya existe una sesión de monitoreo en curso. Deténgala antes de iniciar otra."
        )
        return redirect("monitoring:dashboard")

    form = StartMonitoringForm(request.POST, request.FILES)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0] if form.errors else "Datos inválidos."
        messages.error(request, f"No se pudo iniciar la sesión: {first_error}")
        return redirect("monitoring:dashboard")

    data = form.cleaned_data
    source_type = data["source_type"]
    session = MonitoringSession(
        laboratory=data["laboratory"],
        created_by=request.user,
        source_type=source_type,
        detection_mode=data["detection_mode"],
        line_orientation=data["line_orientation"],
        line_position=data["line_position"],
        status=MonitoringSession.Status.RUNNING,
        started_at=timezone.now(),
    )

    if source_type == MonitoringSession.SourceType.WEBCAM:
        index = data.get("webcam_index")
        session.source_index = settings.LABCOUNT_CAMERA_INDEX if index is None else index
        session.source_label = f"Cámara {session.source_index}"
    elif source_type == MonitoringSession.SourceType.VIDEO:
        upload = data["video_file"]
        session.video_file = upload
        session.source_label = upload.name[:200]
    else:
        session.source_label = "Escena de demostración (sintética)"
        session.source_index = 0

    session.save()

    try:
        stream_manager.start(session)
    except StreamSourceError as exc:
        session.status = MonitoringSession.Status.ERROR
        session.ended_at = timezone.now()
        session.current_occupancy = 0
        session.last_error = str(exc)
        session.save(update_fields=["status", "ended_at", "current_occupancy", "last_error"])
        messages.error(request, f"No se pudo iniciar la fuente de video: {exc}")
    except Exception as exc:  # pragma: no cover - protección ante fallos del hardware
        logger.exception("Error inesperado al iniciar la sesión")
        session.status = MonitoringSession.Status.ERROR
        session.ended_at = timezone.now()
        session.current_occupancy = 0
        session.last_error = str(exc)
        session.save(update_fields=["status", "ended_at", "current_occupancy", "last_error"])
        messages.error(
            request,
            "Ocurrió un error inesperado al abrir la fuente de video. "
            "Revise el archivo o intente con la modalidad de demostración.",
        )
    else:
        messages.success(
            request,
            f"Monitoreo iniciado en {session.laboratory}. "
            f"Fuente: {session.source_description}.",
        )

    return redirect("monitoring:dashboard")


@login_required
@require_POST
def stop_session(request):
    session_id = stream_manager.session_id
    if not session_id:
        reconcile_stale_sessions()
        messages.info(request, "No hay una sesión de monitoreo activa.")
        return redirect("monitoring:dashboard")

    if not stream_manager.can_control(request.user):
        return HttpResponseForbidden("No tiene permisos para detener esta sesión.")

    stream_manager.stop()
    messages.success(request, "La sesión de monitoreo finalizó correctamente.")
    return redirect("monitoring:dashboard")


# ---------------------------------------------------------------------------
# Streaming y API
# ---------------------------------------------------------------------------
@login_required
@require_GET
def video_stream(request):
    response = StreamingHttpResponse(
        stream_manager.mjpeg_generator(),
        content_type="multipart/x-mixed-replace; boundary=frame",
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


@login_required
@require_GET
def api_stats(request):
    data = stream_manager.get_stats()
    session_id = data.get("session_id")
    if session_id:
        data["history"] = history_payload(session_id)
        session = (
            MonitoringSession.objects.select_related("laboratory", "created_by")
            .filter(pk=session_id)
            .first()
        )
        if session:
            data["session"] = {
                "id": session.pk,
                "laboratory": session.laboratory.name,
                "source": session.source_description,
                "started_at": timezone.localtime(session.started_at).isoformat(),
                "owner": session.created_by.get_full_name() or session.created_by.username
                if session.created_by
                else "",
                "can_control": stream_manager.can_control(request.user),
            }
            data["capacity"] = session.laboratory.capacity
            data["percent"] = (
                round((data.get("current", 0) / session.laboratory.capacity) * 100, 1)
                if session.laboratory.capacity
                else 0
            )
    data["server_time"] = timezone.localtime().strftime("%H:%M:%S")
    return JsonResponse(data)


@login_required
@require_GET
def api_preview(request):
    """Último frame JPEG (útil para integraciones o depuración)."""
    from django.http import HttpResponse

    frame = stream_manager.latest_frame()
    if frame is None:
        return HttpResponse(placeholder_jpeg("Sin imagen disponible"), content_type="image/jpeg")
    import cv2

    success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        return HttpResponse(placeholder_jpeg("Imagen no disponible"), content_type="image/jpeg")
    return HttpResponse(buffer.tobytes(), content_type="image/jpeg")


@login_required
@require_POST
def save_snapshot(request):
    session_id = stream_manager.session_id
    if not session_id:
        messages.warning(request, "No hay una transmisión activa para capturar.")
        return redirect("monitoring:dashboard")

    session = get_object_or_404(MonitoringSession, pk=session_id)
    if not stream_manager.can_control(request.user):
        return HttpResponseForbidden("No tiene permisos para guardar capturas de esta sesión.")

    frame = stream_manager.latest_frame()
    if frame is None:
        messages.warning(request, "Todavía no hay un frame disponible. Espere un momento.")
        return redirect("monitoring:dashboard")

    import cv2

    success, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not success:
        messages.error(request, "No se pudo codificar la captura.")
        return redirect("monitoring:dashboard")

    filename = f"captura_{timezone.localtime():%Y%m%d_%H%M%S}.jpg"
    stats = stream_manager.get_stats()
    Snapshot.objects.create(
        session=session,
        image=ContentFile(buffer.tobytes(), name=filename),
        occupancy=stats.get("current", 0),
    )
    messages.success(request, "Captura guardada en el historial de la sesión.")
    return redirect("monitoring:dashboard")


# ---------------------------------------------------------------------------
# Historial
# ---------------------------------------------------------------------------
@login_required
@require_GET
def session_list(request):
    queryset = visible_sessions(request.user)
    status = request.GET.get("status", "").strip()
    query = request.GET.get("q", "").strip()

    if status in MonitoringSession.Status.values:
        queryset = queryset.filter(status=status)
    if query:
        queryset = queryset.filter(
            Q(laboratory__name__icontains=query)
            | Q(source_label__icontains=query)
            | Q(created_by__username__icontains=query)
        )

    summary = queryset.aggregate(
        total=Count("id"),
        entries=Sum("total_entries"),
        exits=Sum("total_exits"),
        unique=Sum("unique_visitors"),
        peak=Max("peak_occupancy"),
        avg_peak=Avg("peak_occupancy"),
    )

    paginator = Paginator(queryset, 12)
    page = paginator.get_page(request.GET.get("page"))
    context = {
        "sessions": page,
        "page_obj": page,
        "summary": summary,
        "status_filter": status,
        "query": query,
        "statuses": MonitoringSession.Status.choices,
    }
    return render(request, "monitoring/sessions.html", context)


@login_required
@require_GET
def session_detail(request, pk: int):
    session = get_object_or_404(visible_sessions(request.user), pk=pk)
    samples = list(
        session.samples.order_by("-captured_at").values(
            "captured_at", "occupancy", "entries", "exits", "fps"
        )[:500]
    )
    samples.reverse()
    chart_data = [
        {
            "t": timezone.localtime(sample["captured_at"]).isoformat(),
            "y": sample["occupancy"],
            "entries": sample["entries"],
            "exits": sample["exits"],
        }
        for sample in samples
    ]
    crossings = session.crossings.all()[:100]
    snapshots = session.snapshots.all()[:12]
    context = {
        "session": session,
        "chart_data": chart_data,
        "crossings": crossings,
        "snapshots": snapshots,
        "entries_count": session.crossings.filter(
            direction=CrossingEvent.Direction.IN
        ).count(),
        "exits_count": session.crossings.filter(
            direction=CrossingEvent.Direction.OUT
        ).count(),
    }
    return render(request, "monitoring/session_detail.html", context)
