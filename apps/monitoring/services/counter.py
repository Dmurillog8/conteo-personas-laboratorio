"""Motor de conteo: detector + seguimiento + línea virtual + anotación."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime

import cv2
import numpy as np

from .detectors import BaseDetector
from .tracker import CentroidTracker, Track


@dataclass
class CountingStats:
    """Métricas instantáneas del procesamiento de video."""

    current: int = 0
    entries: int = 0
    exits: int = 0
    unique: int = 0
    peak: int = 0
    fps: float = 0.0
    detections: int = 0
    detector: str = ""
    frame_width: int = 0
    frame_height: int = 0
    line_orientation: str = "vertical"
    line_position: float = 0.5

    def as_dict(self) -> dict:
        return {
            "current": self.current,
            "entries": self.entries,
            "exits": self.exits,
            "unique": self.unique,
            "peak": self.peak,
            "fps": round(self.fps, 1),
            "detections": self.detections,
            "detector": self.detector,
            "frame_width": self.frame_width,
            "frame_height": self.frame_height,
            "line_orientation": self.line_orientation,
            "line_position": self.line_position,
        }


@dataclass
class Crossing:
    direction: str
    track_id: int


class PeopleCounter:
    """Convierte frames BGR en frames anotados y estadísticas de conteo."""

    def __init__(
        self,
        detector: BaseDetector,
        line_orientation: str = "vertical",
        line_position: float = 0.5,
        min_hits: int = 3,
        max_disappeared: int = 18,
        presence_max_missed: int = 5,
        detect_every: int = 2,
        line_margin: float = 0.03,
        occupancy_window: int = 5,
    ) -> None:
        self.detector = detector
        self.line_orientation = (
            line_orientation if line_orientation in {"vertical", "horizontal"} else "vertical"
        )
        self.line_position = min(0.9, max(0.1, float(line_position)))
        self.detect_every = max(1, int(detect_every))
        self.tracker = CentroidTracker(
            max_disappeared=max_disappeared,
            min_hits=min_hits,
        )
        self.presence_max_missed = max(0, int(presence_max_missed))
        # Zona muerta alrededor de la línea (fracción del ancho/alto). Una
        # persona debe salir de la zona por el otro lado para contar el cruce.
        self.line_margin = min(0.2, max(0.0, float(line_margin)))
        self.occupancy_window = max(1, int(occupancy_window))
        self.entries = 0
        self.exits = 0
        self.peak = 0
        self._frame_index = 0
        self._last_detections = 0
        self._fps = 0.0
        self._last_process_at: float | None = None
        self._track_side: dict[int, int] = {}
        self._occupancy_history: deque[int] = deque(maxlen=self.occupancy_window)
        self._stable_current = 0

    # ------------------------------------------------------------------
    # Procesamiento
    # ------------------------------------------------------------------
    def process(self, frame: np.ndarray) -> tuple[np.ndarray, CountingStats, list[Crossing]]:
        started = time.perf_counter()
        height, width = frame.shape[:2]
        self._frame_index += 1

        crossings: list[Crossing] = []
        should_detect = self._frame_index == 1 or self._frame_index % self.detect_every == 0

        if should_detect:
            boxes = self.detector.detect(frame)
            self._last_detections = len(boxes)
            self.tracker.update(boxes, time.monotonic())
            crossings = self._detect_line_crossings(width, height)
            raw_current = len(self.tracker.active_tracks(self.presence_max_missed))
            self._occupancy_history.append(raw_current)
            # Mediana de los últimos ciclos: evita que el número parpadee por
            # una detección perdida o un falso positivo de un solo frame.
            self._stable_current = int(np.median(self._occupancy_history))

        stats = self._build_stats(width, height)
        self.peak = max(self.peak, stats.current)
        stats.peak = self.peak

        now = time.perf_counter()
        if self._last_process_at is not None:
            delta = max(now - self._last_process_at, 1e-6)
            instant_fps = 1.0 / delta
            self._fps = instant_fps if self._fps == 0 else (self._fps * 0.85 + instant_fps * 0.15)
        self._last_process_at = now
        stats.fps = self._fps

        annotated = self._annotate(frame.copy(), stats)
        return annotated, stats, crossings

    # ------------------------------------------------------------------
    # Líneas de conteo
    # ------------------------------------------------------------------
    def _side_of_line(self, track: Track, line_coordinate: float, margin: float) -> int:
        """-1 = lado de salida, +1 = lado de entrada, 0 = dentro de la zona muerta."""
        value = track.centroid[0] if self.line_orientation == "vertical" else track.centroid[1]
        if value < line_coordinate - margin:
            return -1
        if value > line_coordinate + margin:
            return 1
        return 0

    def _detect_line_crossings(self, width: int, height: int) -> list[Crossing]:
        """Cuenta un cruce cuando una pista pasa de un lado firme al otro.

        Cada pista recuerda el último lado en el que estuvo claramente (fuera
        de la zona muerta). Solo cuando aparece claramente del otro lado se
        registra una entrada o salida. Así, el temblor de la caja sobre la
        línea o una persona parada encima no generan conteos repetidos.
        """
        crossings: list[Crossing] = []
        vertical = self.line_orientation == "vertical"
        span = width if vertical else height
        line_coordinate = span * self.line_position
        margin = max(10.0, span * self.line_margin)

        for track in self.tracker.tracks.values():
            if track.missed > 0:
                continue
            side = self._side_of_line(track, line_coordinate, margin)
            previous = self._track_side.get(track.id)
            if side == 0:
                # Una persona que aparece cerca de la línea toma como origen el
                # lado en el que nació (si no está prácticamente encima).
                if previous is None:
                    value = track.centroid[0] if vertical else track.centroid[1]
                    offset = value - line_coordinate
                    if abs(offset) >= margin * 0.3:
                        self._track_side[track.id] = 1 if offset > 0 else -1
                continue
            self._track_side[track.id] = side
            if previous is None or previous == side or not track.confirmed:
                continue
            if side > 0:
                self.entries += 1
                direction = "in"
            else:
                self.exits += 1
                direction = "out"
            crossings.append(Crossing(direction=direction, track_id=track.id))

        # Limpia pistas que ya no existen.
        if len(self._track_side) > len(self.tracker.tracks) + 50:
            self._track_side = {
                track_id: side
                for track_id, side in self._track_side.items()
                if track_id in self.tracker.tracks
            }
        return crossings

    def _build_stats(self, width: int, height: int) -> CountingStats:
        return CountingStats(
            current=self._stable_current,
            entries=self.entries,
            exits=self.exits,
            unique=self.tracker.total_confirmed,
            peak=self.peak,
            fps=self._fps,
            detections=self._last_detections,
            detector=self.detector.label,
            frame_width=width,
            frame_height=height,
            line_orientation=self.line_orientation,
            line_position=self.line_position,
        )

    # ------------------------------------------------------------------
    # Anotación del video
    # ------------------------------------------------------------------
    def _annotate(self, frame: np.ndarray, stats: CountingStats) -> np.ndarray:
        height, width = frame.shape[:2]
        self._draw_counting_line(frame, width, height)
        self._draw_tracks(frame)
        self._draw_hud(frame, stats)
        self._draw_live_badge(frame, width)
        return frame

    def _draw_counting_line(self, frame: np.ndarray, width: int, height: int) -> None:
        color = (238, 211, 34)  # cian en BGR
        thickness = 2
        if self.line_orientation == "vertical":
            x = int(width * self.line_position)
            for y in range(0, height, 22):
                cv2.line(frame, (x, y), (x, min(height, y + 12)), color, thickness, cv2.LINE_AA)
            cv2.putText(
                frame,
                "ENTRADA >>>",
                (min(width - 120, x + 12), height - 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                "<<< SALIDA",
                (max(4, x - 118), height - 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )
        else:
            y = int(height * self.line_position)
            for x in range(0, width, 22):
                cv2.line(frame, (x, y), (min(width, x + 12), y), color, thickness, cv2.LINE_AA)
            cv2.putText(
                frame,
                "ENTRADA v",
                (width - 126, min(height - 8, y + 20)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                "SALIDA ^",
                (width - 118, max(18, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1,
                cv2.LINE_AA,
            )

    def _draw_tracks(self, frame: np.ndarray) -> None:
        for track in self.tracker.tracks.values():
            # Solo se dibujan personas confirmadas: lo que se ve es lo que se cuenta.
            if not track.confirmed or track.missed > self.presence_max_missed:
                continue
            x, y, w, h = [int(value) for value in track.box]
            color = (129, 236, 180)  # verde menta
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2, cv2.LINE_AA)
            label = f"ID {track.id}"
            (text_w, text_h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
            label_y = max(text_h + 4, y - 6)
            cv2.rectangle(
                frame,
                (x, label_y - text_h - 5),
                (x + text_w + 10, label_y + 3),
                color,
                -1,
                cv2.LINE_AA,
            )
            cv2.putText(
                frame,
                label,
                (x + 5, label_y - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (14, 22, 30),
                1,
                cv2.LINE_AA,
            )
            center = (int(track.centroid[0]), int(track.centroid[1]))
            cv2.circle(frame, center, 4, color, -1, cv2.LINE_AA)
            history = track.history[-12:]
            for index in range(1, len(history)):
                cv2.line(
                    frame,
                    (int(history[index - 1][0]), int(history[index - 1][1])),
                    (int(history[index][0]), int(history[index][1])),
                    color,
                    1,
                    cv2.LINE_AA,
                )

    def _draw_hud(self, frame: np.ndarray, stats: CountingStats) -> None:
        width = 420
        height = 102
        overlay = frame.copy()
        cv2.rectangle(overlay, (16, 16), (16 + width, 16 + height), (10, 16, 26), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
        cv2.rectangle(
            frame, (16, 16), (16 + width, 16 + height), (71, 85, 105), 1, cv2.LINE_AA
        )

        cv2.putText(
            frame,
            "PERSONAS EN EL LABORATORIO",
            (32, 42),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (148, 163, 184),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"{stats.current:02d}",
            (30, 96),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.75,
            (238, 211, 34),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Entradas: {stats.entries}",
            (128, 66),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (226, 232, 240),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Salidas: {stats.exits}",
            (128, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.58,
            (226, 232, 240),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Unicos: {stats.unique}  |  {stats.fps:4.1f} FPS",
            (272, 66),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (148, 163, 184),
            1,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            f"Pico: {stats.peak}  |  Detec.: {stats.detections}",
            (272, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (148, 163, 184),
            1,
            cv2.LINE_AA,
        )

    def _draw_live_badge(self, frame: np.ndarray, width: int) -> None:
        now = datetime.now().strftime("%H:%M:%S")
        text = f"EN VIVO  {now}"
        (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        x2 = width - 20
        x1 = x2 - text_w - 38
        y1 = 18
        overlay = frame.copy()
        cv2.rectangle(overlay, (x1, y1), (x2, y1 + 28), (10, 16, 26), -1, cv2.LINE_AA)
        cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
        cv2.circle(frame, (x1 + 14, y1 + 14), 5, (80, 80, 255), -1, cv2.LINE_AA)
        cv2.putText(
            frame,
            text,
            (x1 + 26, y1 + 19),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (226, 232, 240),
            1,
            cv2.LINE_AA,
        )
