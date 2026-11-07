"""Seguimiento de personas mediante centroides.

El detector entrega cajas en cada ciclo; este módulo las asocia con las
pistas existentes para conservar un identificador estable, confirmar una
detección después de varios aciertos y descartar ruido temporal.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class Track:
    """Una persona seguida a lo largo del video."""

    id: int
    centroid: tuple[float, float]
    box: tuple[float, float, float, float]
    previous_centroid: tuple[float, float] | None = None
    hits: int = 1
    missed: int = 0
    confirmed: bool = False
    first_seen: float = 0.0
    last_seen: float = 0.0
    history: list[tuple[float, float]] = field(default_factory=list)

    def update(
        self,
        centroid: tuple[float, float],
        box: tuple[float, float, float, float],
        now: float,
    ) -> None:
        self.previous_centroid = self.centroid
        self.centroid = centroid
        self.box = box
        self.hits += 1
        self.missed = 0
        self.last_seen = now
        self.history.append(centroid)
        if len(self.history) > 30:
            del self.history[:-30]


class CentroidTracker:
    """Asociación greedy por distancia euclidiana.

    Es determinista, no requiere dependencias externas y funciona bien para
    pocas personas (el escenario típico de un laboratorio).
    """

    def __init__(
        self,
        max_disappeared: int = 18,
        max_distance: float = 95.0,
        min_hits: int = 3,
    ) -> None:
        self.max_disappeared = max(1, int(max_disappeared))
        self.max_distance = float(max_distance)
        self.min_hits = max(1, int(min_hits))
        self.tracks: dict[int, Track] = {}
        self.next_id = 1
        self.total_confirmed = 0
        self._confirmed_ids: set[int] = set()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------
    @staticmethod
    def _rect_centroid(rect: tuple[float, float, float, float]) -> tuple[float, float]:
        x, y, w, h = rect
        return (float(x + w / 2.0), float(y + h / 2.0))

    def _register(
        self,
        centroid: tuple[float, float],
        box: tuple[float, float, float, float],
        now: float,
    ) -> Track:
        track = Track(
            id=self.next_id,
            centroid=centroid,
            box=box,
            first_seen=now,
            last_seen=now,
            history=[centroid],
        )
        self.tracks[track.id] = track
        self.next_id += 1
        self._confirm(track)
        return track

    def _confirm(self, track: Track) -> None:
        if not track.confirmed and track.hits >= self.min_hits:
            track.confirmed = True
            if track.id not in self._confirmed_ids:
                self._confirmed_ids.add(track.id)
                self.total_confirmed += 1

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------
    def update(
        self, rects: list[tuple[float, float, float, float]], now: float
    ) -> dict[int, Track]:
        """Actualiza el estado con las cajas detectadas en el frame actual."""
        detections = [self._rect_centroid(rect) for rect in rects]

        if not self.tracks:
            for rect, centroid in zip(rects, detections):
                self._register(centroid, rect, now)
            return self.tracks

        if not detections:
            for track in list(self.tracks.values()):
                track.missed += 1
                if track.missed > self.max_disappeared:
                    del self.tracks[track.id]
            return self.tracks

        track_ids = list(self.tracks.keys())
        track_centroids = np.array([self.tracks[tid].centroid for tid in track_ids], dtype=float)
        detection_centroids = np.array(detections, dtype=float)
        distances = np.linalg.norm(
            track_centroids[:, None, :] - detection_centroids[None, :, :], axis=2
        )

        pairs = sorted(
            (
                (float(distances[i, j]), i, j)
                for i in range(distances.shape[0])
                for j in range(distances.shape[1])
            ),
            key=lambda item: item[0],
        )

        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()

        for distance, track_index, detection_index in pairs:
            if distance > self.max_distance:
                break
            if track_index in matched_tracks or detection_index in matched_detections:
                continue
            track = self.tracks[track_ids[track_index]]
            track.update(detections[detection_index], rects[detection_index], now)
            self._confirm(track)
            matched_tracks.add(track_index)
            matched_detections.add(detection_index)

        # Pistas sin detección: envejecen y eventualmente se eliminan.
        for track_index, track_id in enumerate(track_ids):
            if track_index in matched_tracks:
                continue
            track = self.tracks[track_id]
            track.missed += 1
            if track.missed > self.max_disappeared:
                del self.tracks[track_id]

        # Detecciones nuevas.
        for detection_index, centroid in enumerate(detections):
            if detection_index in matched_detections:
                continue
            self._register(centroid, rects[detection_index], now)

        return self.tracks

    def active_tracks(self, max_missed: int = 5) -> list[Track]:
        """Pistas confirmadas y presentes (tolerando pequeños huecos)."""
        return [
            track
            for track in self.tracks.values()
            if track.confirmed and track.missed <= max_missed
        ]

    def reset(self) -> None:
        self.tracks.clear()
        self.next_id = 1
        self.total_confirmed = 0
        self._confirmed_ids.clear()
