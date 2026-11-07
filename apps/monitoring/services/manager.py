"""Administrador del flujo de video en tiempo real.

Un único hilo mantiene abierta la fuente (cámara, archivo o demostración),
procesa los frames con OpenCV y publica el último JPEG para el endpoint
MJPEG. Este diseño evita abrir la cámara por cada petición HTTP y mantiene
el conteo consistente entre todos los clientes conectados.
"""

from __future__ import annotations

import logging
import platform
import threading
import time
from functools import lru_cache
from typing import Any

import cv2
import numpy as np
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone

from apps.monitoring.models import CrossingEvent, MonitoringSession, OccupancySample

from .counter import CountingStats, PeopleCounter
from .demo import DemoPersonDetector, DemoScene
from .detectors import create_detector

logger = logging.getLogger("apps.monitoring")


class StreamSourceError(RuntimeError):
    """La fuente de video no pudo abrirse o no entrega frames."""


@lru_cache(maxsize=16)
def placeholder_jpeg(message: str = "Sin transmision en vivo") -> bytes:
    """Imagen 16:9 usada cuando todavía no hay frames disponibles."""
    width, height = 960, 540
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    for y in range(height):
        factor = y / height
        frame[y, :] = (
            int(11 + 8 * factor),
            int(16 + 10 * factor),
            int(26 + 14 * factor),
        )
    for offset in range(-width, width, 60):
        cv2.line(frame, (offset, 0), (offset + height, height), (16, 23, 35), 1)
    cv2.circle(frame, (width // 2, 210), 40, (34, 211, 238), 2, cv2.LINE_AA)
    cv2.circle(frame, (width // 2, 196), 7, (80, 80, 255), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (width // 2, 224), (18, 12), 0, 0, 360, (34, 211, 238), 2, cv2.LINE_AA)
    cv2.putText(
        frame,
        "LabCount",
        (width // 2 - 86, 300),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (226, 232, 240),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        message,
        (width // 2 - 150, 342),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.62,
        (148, 163, 184),
        1,
        cv2.LINE_AA,
    )
    cv2.putText(
        frame,
        "Django + OpenCV + PostgreSQL",
        (width // 2 - 140, 448),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.46,
        (71, 85, 105),
        1,
        cv2.LINE_AA,
    )
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
    if not ok:
        return b""
    return buffer.tobytes()


def _resize_frame(frame: np.ndarray) -> np.ndarray:
    height, width = frame.shape[:2]
    if width == 0 or height == 0:
        return frame
    max_width = max(480, int(settings.LABCOUNT_MAX_FRAME_WIDTH))
    target_width = min(width, max_width)
    if target_width < 520:
        target_width = min(max_width, 520)
    if target_width != width:
        scale = target_width / float(width)
        frame = cv2.resize(
            frame,
            (target_width, max(1, int(height * scale))),
            interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
        )
    return frame


class StreamManager:
    """Estado global (por proceso) del monitoreo en vivo."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._capture: cv2.VideoCapture | None = None
        self._running = False
        self._session_id: int | None = None
        self._session_started_at = None
        self._session_ended_at = None
        self._status = "idle"
        self._error = ""
        self._source = ""
        self._laboratory = ""
        self._capacity = 0
        self._detector_label = ""
        self._latest_jpeg: bytes | None = None
        self._latest_frame: np.ndarray | None = None
        self._stats: dict[str, Any] = {}
        self._fps = 0.0

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------
    @property
    def running(self) -> bool:
        with self._lock:
            return self._running

    @property
    def session_id(self) -> int | None:
        with self._lock:
            return self._session_id

    def can_control(self, user) -> bool:
        with self._lock:
            if not self._session_id:
                return False
            if user.is_staff or user.is_superuser:
                return True
            try:
                session = MonitoringSession.objects.only("created_by_id").get(
                    pk=self._session_id
                )
                return session.created_by_id == user.id
            except MonitoringSession.DoesNotExist:
                return False

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            data = dict(self._stats)
            now = timezone.now()
            elapsed = 0
            if self._session_started_at:
                end = self._session_ended_at or now
                elapsed = max(0, int((end - self._session_started_at).total_seconds()))
            data.update(
                {
                    "running": self._running,
                    "status": self._status,
                    "session_id": self._session_id,
                    "error": self._error,
                    "source": self._source,
                    "laboratory": self._laboratory,
                    "capacity": self._capacity,
                    "detector": data.get("detector") or self._detector_label,
                    "elapsed_seconds": elapsed,
                    "elapsed": self._format_duration(elapsed),
                    "percent": round((data.get("current", 0) / self._capacity) * 100, 1)
                    if self._capacity
                    else 0.0,
                    "has_frame": self._latest_jpeg is not None,
                }
            )
            return data

    def latest_frame(self) -> np.ndarray | None:
        with self._lock:
            return None if self._latest_frame is None else self._latest_frame.copy()

    @staticmethod
    def _format_duration(seconds: int) -> str:
        hours, remainder = divmod(max(0, seconds), 3600)
        minutes, secs = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    # ------------------------------------------------------------------
    # Fuente de video
    # ------------------------------------------------------------------
    def _open_source(self, session: MonitoringSession):
        source_type = session.source_type
        if source_type == MonitoringSession.SourceType.DEMO:
            scene = DemoScene()
            frame = scene.next_frame()
            return None, scene, frame

        if source_type == MonitoringSession.SourceType.VIDEO:
            if not session.video_file:
                raise StreamSourceError("La sesión no tiene un archivo de video asociado.")
            try:
                path = session.video_file.path
            except (ValueError, OSError) as exc:
                raise StreamSourceError(f"No se pudo acceder al video: {exc}") from exc

            capture = cv2.VideoCapture(path)
            if not capture.isOpened():
                capture.release()
                raise StreamSourceError(
                    "OpenCV no pudo abrir el video. Verifique el formato (MP4/AVI/MOV)."
                )
            ok, frame = capture.read()
            if not ok or frame is None:
                capture.release()
                raise StreamSourceError(
                    "El archivo de video no contiene frames legibles. Pruebe otro códec."
                )
            capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return capture, None, frame

        # Cámara web
        index = max(0, int(session.source_index))
        backends: list[int] = []
        if platform.system().lower() == "windows":
            for name in ("CAP_DSHOW", "CAP_MSMF"):
                backend = getattr(cv2, name, None)
                if backend is not None and backend not in backends:
                    backends.append(backend)
        if cv2.CAP_ANY not in backends:
            backends.append(cv2.CAP_ANY)

        last_error = "No se encontró una cámara disponible."
        # Windows puede tener la cámara ocupada brevemente (otra app, arranque
        # del dispositivo): se reintenta en varias rondas antes de fallar.
        for attempt in range(3):
            for backend in backends:
                capture = cv2.VideoCapture(index, backend)
                if not capture.isOpened():
                    capture.release()
                    continue
                try:
                    capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                except cv2.error:
                    pass

                for _ in range(20):
                    ok, frame = capture.read()
                    if ok and frame is not None:
                        return capture, None, frame
                    time.sleep(0.05)
                capture.release()
                last_error = (
                    f"La cámara {index} se abrió pero no entregó imagen. "
                    "Cierre otras aplicaciones que la estén usando e intente de nuevo."
                )
            if attempt < 2:
                time.sleep(0.8)

        raise StreamSourceError(last_error)

    # ------------------------------------------------------------------
    # Inicio / detención
    # ------------------------------------------------------------------
    def start(self, session: MonitoringSession) -> dict[str, Any]:
        with self._lock:
            if self._running:
                raise StreamSourceError("Ya existe una sesión de monitoreo en curso.")

        capture = None
        try:
            capture, demo_scene, first_frame = self._open_source(session)
            if first_frame is None or first_frame.size == 0:
                raise StreamSourceError("La fuente de video no entregó una imagen válida.")
            first_frame = _resize_frame(first_frame)

            if session.source_type == MonitoringSession.SourceType.DEMO:
                detector = DemoPersonDetector(demo_scene)
            else:
                detector = create_detector(session.detection_mode)

            counter = PeopleCounter(
                detector=detector,
                line_orientation=session.line_orientation,
                line_position=session.line_position,
                detect_every=settings.LABCOUNT_DETECT_EVERY,
            )

            loop_video = session.source_type == MonitoringSession.SourceType.VIDEO
            config = {
                "session_id": session.pk,
                "source_type": session.source_type,
                "loop_video": loop_video,
                "source_label": session.source_description,
                "laboratory": session.laboratory.name,
                "capacity": session.laboratory.capacity,
                "detector_label": detector.label,
            }

            stop_event = threading.Event()
            thread = threading.Thread(
                target=self._run,
                args=(capture, demo_scene, counter, config, stop_event),
                name=f"labcount-stream-{session.pk}",
                daemon=True,
            )

            with self._lock:
                self._capture = capture
                self._session_id = session.pk
                self._session_started_at = session.started_at or timezone.now()
                self._session_ended_at = None
                self._status = MonitoringSession.Status.RUNNING
                self._error = ""
                self._source = config["source_label"]
                self._laboratory = config["laboratory"]
                self._capacity = config["capacity"]
                self._detector_label = config["detector_label"]
                self._latest_jpeg = None
                self._latest_frame = None
                self._stats = {}
                self._fps = 0.0
                self._running = True
                self._stop_event = stop_event
                self._thread = thread

            thread.start()
            logger.info("Sesión %s iniciada con %s", session.pk, detector.label)
            return self.get_stats()
        except Exception:
            if capture is not None:
                capture.release()
            with self._lock:
                self._running = False
                self._status = MonitoringSession.Status.ERROR
                self._thread = None
                self._capture = None
            raise

    def stop(self, timeout: float = 5.0) -> None:
        with self._lock:
            thread = self._thread
            session_id = self._session_id
            self._stop_event.set()

        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)

        with self._lock:
            still_alive = bool(thread and thread.is_alive())
            self._running = False
            if self._status == MonitoringSession.Status.RUNNING:
                self._status = MonitoringSession.Status.STOPPED
            self._session_ended_at = self._session_ended_at or timezone.now()

        if session_id:
            self._finalize_session(session_id, MonitoringSession.Status.STOPPED)
        if still_alive:
            logger.warning("El hilo de la sesión %s no terminó en %.1fs", session_id, timeout)

    # ------------------------------------------------------------------
    # Bucle de procesamiento
    # ------------------------------------------------------------------
    def _run(
        self,
        capture: cv2.VideoCapture | None,
        demo_scene: DemoScene | None,
        counter: PeopleCounter,
        config: dict[str, Any],
        stop_event: threading.Event,
    ) -> None:
        session_id = config["session_id"]
        frame_interval = 1.0 / max(5, int(settings.LABCOUNT_STREAM_FPS))
        sample_interval = max(1.0, float(settings.LABCOUNT_SAMPLE_SECONDS))
        last_sample_at = 0.0
        last_stats: CountingStats | None = None
        error_message = ""
        consecutive_failures = 0
        logger.info("Hilo de video iniciado para la sesión %s", session_id)

        try:
            while not stop_event.is_set():
                started = time.perf_counter()

                if demo_scene is not None:
                    frame = demo_scene.next_frame()
                else:
                    ok, frame = capture.read() if capture is not None else (False, None)
                    if not ok or frame is None:
                        if config["source_type"] == MonitoringSession.SourceType.VIDEO:
                            # Un video se reproduce en bucle para demostraciones.
                            if capture is not None:
                                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                            time.sleep(0.05)
                            continue
                        consecutive_failures += 1
                        if consecutive_failures <= 20:
                            time.sleep(0.05)
                            continue
                        raise StreamSourceError(
                            "Se perdió la señal de la cámara. Verifique la conexión."
                        )
                consecutive_failures = 0
                frame = _resize_frame(frame)

                annotated, stats, crossings = counter.process(frame)
                last_stats = stats

                success, encoded = cv2.imencode(
                    ".jpg", annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 82]
                )
                if success:
                    with self._lock:
                        self._latest_jpeg = encoded.tobytes()
                        self._latest_frame = annotated
                        self._stats = stats.as_dict()

                now = time.perf_counter()
                if now - last_sample_at >= sample_interval:
                    last_sample_at = now
                    self._persist_sample(session_id, stats)

                if crossings:
                    self._persist_crossings(session_id, crossings)

                elapsed = time.perf_counter() - started
                time.sleep(max(0.001, frame_interval - elapsed))

        except StreamSourceError as exc:
            error_message = str(exc)
            logger.warning("Sesión %s detenida por error de fuente: %s", session_id, exc)
        except Exception as exc:  # pragma: no cover - protección del hilo
            error_message = f"Error inesperado del procesador de video: {exc}"
            logger.exception("Error inesperado en la sesión %s", session_id)
        finally:
            if capture is not None:
                capture.release()
            if last_stats is not None:
                self._persist_sample(session_id, last_stats)
            if error_message:
                with self._lock:
                    self._error = error_message
                    self._status = MonitoringSession.Status.ERROR
                    self._session_ended_at = timezone.now()
                self._finalize_session(
                    session_id, MonitoringSession.Status.ERROR, error_message
                )
            else:
                with self._lock:
                    self._status = MonitoringSession.Status.STOPPED
                    self._session_ended_at = timezone.now()
                self._finalize_session(session_id, MonitoringSession.Status.STOPPED)

            with self._lock:
                self._running = False
                self._thread = None
                self._capture = None
                if self._stats:
                    self._stats["current"] = 0
            logger.info("Hilo de video finalizado para la sesión %s", session_id)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------
    def _persist_sample(self, session_id: int, stats: CountingStats) -> None:
        close_old_connections()
        try:
            session = MonitoringSession.objects.get(pk=session_id)
            if session.status != MonitoringSession.Status.RUNNING:
                return
            OccupancySample.objects.create(
                session=session,
                occupancy=stats.current,
                entries=stats.entries,
                exits=stats.exits,
                fps=round(stats.fps, 2),
            )
            session.current_occupancy = stats.current
            session.peak_occupancy = max(session.peak_occupancy, stats.current)
            session.total_entries = stats.entries
            session.total_exits = stats.exits
            session.unique_visitors = stats.unique
            session.save(
                update_fields=[
                    "current_occupancy",
                    "peak_occupancy",
                    "total_entries",
                    "total_exits",
                    "unique_visitors",
                ]
            )
        except MonitoringSession.DoesNotExist:
            logger.warning("La sesión %s fue eliminada mientras estaba en curso", session_id)
        except Exception as exc:  # pragma: no cover - depende de la BD
            logger.exception("No se pudo guardar la muestra de la sesión %s: %s", session_id, exc)
        finally:
            close_old_connections()

    def _persist_crossings(self, session_id: int, crossings) -> None:
        close_old_connections()
        try:
            session = MonitoringSession.objects.get(pk=session_id)
            if session.status != MonitoringSession.Status.RUNNING:
                return
            now = timezone.now()
            CrossingEvent.objects.bulk_create(
                [
                    CrossingEvent(
                        session=session,
                        direction=crossing.direction,
                        track_id=crossing.track_id,
                        occurred_at=now,
                    )
                    for crossing in crossings
                ]
            )
        except Exception as exc:  # pragma: no cover
            logger.exception("No se pudieron guardar cruces de la sesión %s: %s", session_id, exc)
        finally:
            close_old_connections()

    def _finalize_session(self, session_id: int, status: str, error: str = "") -> None:
        close_old_connections()
        try:
            session = MonitoringSession.objects.get(pk=session_id)
            if session.status != MonitoringSession.Status.RUNNING:
                return
            session.status = status
            session.ended_at = timezone.now()
            session.current_occupancy = 0
            if error:
                session.last_error = error[:2000]
            session.save(
                update_fields=["status", "ended_at", "current_occupancy", "last_error"]
            )
        except MonitoringSession.DoesNotExist:
            pass
        except Exception as exc:  # pragma: no cover
            logger.exception("No se pudo finalizar la sesión %s: %s", session_id, exc)
        finally:
            close_old_connections()

    # ------------------------------------------------------------------
    # Streaming y capturas
    # ------------------------------------------------------------------
    def mjpeg_generator(self):
        boundary = b"--frame\r\n"
        while True:
            with self._lock:
                running = self._running
                jpeg = self._latest_jpeg
                error = self._error
            if not running:
                message = "Sesion finalizada"
                if error:
                    message = "Error de video - consulte el panel"
                jpeg = placeholder_jpeg(message)
            elif jpeg is None:
                jpeg = placeholder_jpeg("Iniciando camara y detector...")
            if not jpeg:
                time.sleep(0.2)
                continue
            yield boundary
            yield b"Content-Type: image/jpeg\r\n"
            yield f"Content-Length: {len(jpeg)}\r\n\r\n".encode("ascii")
            yield jpeg
            yield b"\r\n"
            time.sleep(1.0 / 25.0)


# Instancia única por proceso de Django.
stream_manager = StreamManager()
