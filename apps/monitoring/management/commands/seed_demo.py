"""Crea datos de demostración: laboratorio, usuario e historial sintético."""

import random
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Laboratory
from apps.monitoring.models import (
    CrossingEvent,
    MonitoringSession,
    OccupancySample,
)


class Command(BaseCommand):
    help = "Crea el laboratorio por defecto y, opcionalmente, un usuario e historial de ejemplo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--with-user",
            action="store_true",
            help="Crea/actualiza el usuario demo (demo / Demo12345!).",
        )
        parser.add_argument(
            "--with-history",
            action="store_true",
            help="Genera seis sesiones de ejemplo finalizadas.",
        )

    def handle(self, *args, **options):
        laboratory, created = Laboratory.objects.get_or_create(
            name="Laboratorio P",
            defaults={
                "location": "Bloque P · Campus Universitario",
                "capacity": 200,
                "is_active": True,
            },
        )
        action = "creado" if created else "verificado"
        self.stdout.write(
            self.style.SUCCESS(
                f"Laboratorio '{laboratory.name}' {action} (aforo {laboratory.capacity})."
            )
        )

        user = None
        if options["with_user"]:
            User = get_user_model()
            user, user_created = User.objects.get_or_create(
                username="demo",
                defaults={
                    "first_name": "Usuario",
                    "last_name": "Demo",
                    "email": "demo@labcount.local",
                },
            )
            user.set_password("Demo12345!")
            user.save()
            action = "creado" if user_created else "actualizado"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Usuario demo {action}: demo / Demo12345! (cambiar en producción)."
                )
            )
        else:
            user = get_user_model().objects.filter(is_superuser=True).first()

        if options["with_history"]:
            self._create_history(laboratory, user)
            self.stdout.write(self.style.SUCCESS("Historial de demostración generado."))

    def _create_history(self, laboratory, user):
        rng = random.Random(42)
        now = timezone.now()
        for day in range(1, 7):
            start = now - timedelta(days=day, hours=rng.randint(0, 3), minutes=rng.randint(0, 50))
            duration = rng.randint(17, 52)
            end = start + timedelta(minutes=duration)
            peak = rng.randint(4, 14)
            entries = rng.randint(8, 32)
            exits = max(0, entries - rng.randint(0, 4))
            session = MonitoringSession.objects.create(
                laboratory=laboratory,
                created_by=user,
                source_type=MonitoringSession.SourceType.DEMO,
                source_label="Escena de demostración (sintética)",
                detection_mode=MonitoringSession.DetectionMode.HYBRID,
                status=MonitoringSession.Status.STOPPED,
                started_at=start,
                ended_at=end,
                peak_occupancy=peak,
                current_occupancy=0,
                total_entries=entries,
                total_exits=exits,
                unique_visitors=max(entries, peak),
            )
            samples = []
            step = 30
            total_steps = max(6, int(duration * 60 / step))
            occupancy = 0
            for index in range(total_steps):
                occupancy = max(0, min(peak, occupancy + rng.randint(-2, 3)))
                samples.append(
                    OccupancySample(
                        session=session,
                        captured_at=start + timedelta(seconds=index * step),
                        occupancy=occupancy,
                        entries=int(entries * index / total_steps),
                        exits=int(exits * index / total_steps),
                        fps=round(rng.uniform(13.5, 16.5), 1),
                    )
                )
            OccupancySample.objects.bulk_create(samples)
            CrossingEvent.objects.bulk_create(
                [
                    CrossingEvent(
                        session=session,
                        occurred_at=start + timedelta(minutes=rng.randint(1, duration)),
                        direction=rng.choice(
                            [CrossingEvent.Direction.IN, CrossingEvent.Direction.OUT]
                        ),
                        track_id=rng.randint(1, 30),
                    )
                    for _ in range(min(entries + exits, 20))
                ]
            )
