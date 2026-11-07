import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Sum
from django.db.models.functions import TruncDate
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.monitoring.models import MonitoringSession, OccupancySample

PERIODS = {7: "Últimos 7 días", 30: "Últimos 30 días", 90: "Últimos 90 días"}


def _period(request) -> int:
    try:
        days = int(request.GET.get("days", 30))
    except (TypeError, ValueError):
        days = 30
    return days if days in PERIODS else 30


def _sessions(user, since):
    return (
        MonitoringSession.objects.visible_to(user)
        .select_related("laboratory", "created_by")
        .filter(started_at__gte=since)
    )


@login_required
@require_GET
def index(request):
    days = _period(request)
    since = timezone.now() - timedelta(days=days - 1)
    sessions = _sessions(request.user, since)

    summary = sessions.aggregate(
        total_sessions=Count("id"),
        total_entries=Sum("total_entries"),
        total_exits=Sum("total_exits"),
        total_unique=Sum("unique_visitors"),
        max_peak=Max("peak_occupancy"),
    )
    summary["total_entries"] = summary["total_entries"] or 0
    summary["total_exits"] = summary["total_exits"] or 0
    summary["total_unique"] = summary["total_unique"] or 0
    summary["max_peak"] = summary["max_peak"] or 0

    durations = [session.duration_seconds for session in sessions]
    summary["avg_duration"] = int(sum(durations) / len(durations)) if durations else 0
    avg_seconds = summary["avg_duration"]
    summary["avg_duration_display"] = (
        f"{avg_seconds // 60:02d}:{avg_seconds % 60:02d}" if avg_seconds < 3600
        else f"{avg_seconds // 3600:02d}:{(avg_seconds % 3600) // 60:02d}"
    )

    daily_rows = list(
        sessions.annotate(day=TruncDate("started_at"))
        .values("day")
        .annotate(
            session_count=Count("id"),
            entries=Sum("total_entries"),
            exits=Sum("total_exits"),
            unique=Sum("unique_visitors"),
            peak=Max("peak_occupancy"),
        )
        .order_by("day")
    )
    daily_map = {row["day"]: row for row in daily_rows}
    max_entries = max([row["entries"] or 0 for row in daily_rows], default=0)
    daily = []
    for offset in range(days):
        day = (since + timedelta(days=offset)).date()
        row = daily_map.get(day, {})
        entries = row.get("entries") or 0
        daily.append(
            {
                "day": day,
                "label": day.strftime("%d/%m"),
                "entries": entries,
                "exits": row.get("exits") or 0,
                "session_count": row.get("session_count") or 0,
                "height": round((entries / max_entries) * 100) if max_entries else 0,
            }
        )

    by_lab = list(
        sessions.values("laboratory__name", "laboratory__capacity")
        .annotate(
            session_count=Count("id"),
            entries=Sum("total_entries"),
            unique=Sum("unique_visitors"),
            peak=Max("peak_occupancy"),
        )
        .order_by("-entries", "laboratory__name")
    )
    top_sessions = sessions.order_by("-peak_occupancy", "-started_at")[:6]

    context = {
        "days": days,
        "periods": PERIODS,
        "period_label": PERIODS[days],
        "summary": summary,
        "daily": daily,
        "by_lab": by_lab,
        "top_sessions": top_sessions,
        "sessions_count": summary["total_sessions"] or 0,
    }
    return render(request, "reports/index.html", context)


def _csv_response(filename: str) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")  # BOM para que Excel reconozca UTF-8
    return response


@login_required
@require_GET
def export_sessions(request):
    days = _period(request)
    since = timezone.now() - timedelta(days=days - 1)
    sessions = _sessions(request.user, since).order_by("-started_at")
    response = _csv_response(f"labcount_sesiones_{days}d.csv")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        [
            "ID",
            "Inicio",
            "Fin",
            "Laboratorio",
            "Fuente",
            "Deteccion",
            "Estado",
            "Duracion",
            "Pico",
            "Entradas",
            "Salidas",
            "Visitantes unicos",
            "Responsable",
        ]
    )
    for session in sessions.iterator():
        writer.writerow(
            [
                session.pk,
                timezone.localtime(session.started_at).strftime("%Y-%m-%d %H:%M:%S"),
                timezone.localtime(session.ended_at).strftime("%Y-%m-%d %H:%M:%S")
                if session.ended_at
                else "",
                session.laboratory.name,
                session.source_description,
                session.get_detection_mode_display(),
                session.get_status_display(),
                session.duration_display,
                session.peak_occupancy,
                session.total_entries,
                session.total_exits,
                session.unique_visitors,
                session.created_by.get_full_name() if session.created_by else "",
            ]
        )
    return response


@login_required
@require_GET
def export_session(request, pk: int):
    session = get_object_or_404(
        MonitoringSession.objects.visible_to(request.user).select_related("laboratory"),
        pk=pk,
    )
    response = _csv_response(f"labcount_sesion_{session.pk}.csv")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Sesion", session.pk])
    writer.writerow(["Laboratorio", session.laboratory.name])
    writer.writerow(["Fuente", session.source_description])
    writer.writerow(["Inicio", timezone.localtime(session.started_at).strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow(
        [
            "Fin",
            timezone.localtime(session.ended_at).strftime("%Y-%m-%d %H:%M:%S")
            if session.ended_at
            else "En curso",
        ]
    )
    writer.writerow(["Duracion", session.duration_display])
    writer.writerow(["Pico de ocupacion", session.peak_occupancy])
    writer.writerow(["Entradas", session.total_entries])
    writer.writerow(["Salidas", session.total_exits])
    writer.writerow(["Visitantes unicos", session.unique_visitors])
    writer.writerow([])
    writer.writerow(["Fecha y hora", "Ocupacion", "Entradas", "Salidas", "FPS"])
    samples = OccupancySample.objects.filter(session=session).order_by("captured_at")
    for sample in samples.iterator():
        writer.writerow(
            [
                timezone.localtime(sample.captured_at).strftime("%Y-%m-%d %H:%M:%S"),
                sample.occupancy,
                sample.entries,
                sample.exits,
                sample.fps,
            ]
        )
    return response
