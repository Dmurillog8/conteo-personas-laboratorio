"""Seguimiento de personas.

El detector entrega cajas en cada ciclo; este módulo las asocia con las
pistas existentes para conservar un identificador estable, confirmar una
detección después de varios aciertos y descartar ruido temporal.

La asociación combina solapamiento (IoU) y distancia entre centroides
normalizada por el tamaño de la persona: una persona cerca de la cámara
puede moverse muchos píxeles entre frames sin que eso sea otra persona.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


def _iou(a, b) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    if inter <= 0:
        return 0.0
    return inter / max(1.0, aw * ah + bw * bh - inter)


def _containment(inner, outer) -> float:
    ix, iy, iw, ih = inner
    ox, oy, ow, oh = outer
    x1, y1 = max(ix, ox), max(iy, oy)
    x2, y2 = min(ix + iw, ox + ow), min(iy + ih, oy + oh)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    return inter / max(1.0, iw * ih)


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
        smoothing: float = 0.0,
    ) -> None:
        if smoothing > 0:
            alpha = 1.0 - smoothing
            box = tuple(alpha * new + smoothing * old for new, old in zip(box, self.box))
            centroid = (box[0] + box[2] / 2.0, box[1] + box[3] / 2.0)
        self.previous_centroid = self.centroid
        self.centroid = (float(centroid[0]), float(centroid[1]))
        self.box = tuple(float(v) for v in box)
        self.hits += 1
        self.missed = 0
        self.last_seen = now
        self.history.append(self.centroid)
        if len(self.history) > 30:
            del self.history[:-30]

    @property
    def size(self) -> float:
        """Escala de la persona (diagonal de su caja)."""
        return float(np.hypot(self.box[2], self.box[3]))


class CentroidTracker:
    """Asociación greedy por costo (IoU + distancia normalizada).

    Es determinista, no requiere dependencias externas y funciona bien para
    pocas personas (el escenario típico de un laboratorio).
    """

    def __init__(
        self,
        max_disappeared: int = 18,
        max_distance: float = 95.0,
        min_hits: int = 3,
        smoothing: float = 0.35,
    ) -> None:
        self.max_disappeared = max(1, int(max_disappeared))
        self.max_distance = float(max_distance)
        self.min_hits = max(1, int(min_hits))
        self.smoothing = min(0.9, max(0.0, float(smoothing)))
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
            box=tuple(float(v) for v in box),
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

    def _gate(self, track: Track) -> float:
        """Distancia máxima permitida para asociar una detección a la pista."""
        # Crece con el tamaño de la persona y con los frames perdidos.
        adaptive = 0.75 * track.size * (1.0 + 0.15 * min(track.missed, 6))
        return max(self.max_distance, adaptive)

    def _remove_duplicates(self) -> None:
        """Fusiona pistas que describen a la misma persona.

        Si dos pistas se solapan mucho, se conserva la más antigua (o la
        confirmada) y se elimina la otra. Una pista nueva eliminada antes de
        confirmarse no suma visitantes únicos.
        """
        ids = sorted(self.tracks.keys())
        removed: set[int] = set()
        for i, first_id in enumerate(ids):
            if first_id in removed:
                continue
            first = self.tracks[first_id]
            if first.missed > 0:
                continue
            for second_id in ids[i + 1 :]:
                if second_id in removed:
                    continue
                second = self.tracks[second_id]
                if second.missed > 0:
                    continue
                overlap = _iou(first.box, second.box)
                inside = max(
                    _containment(second.box, first.box), _containment(first.box, second.box)
                )
                if overlap < 0.55 and inside < 0.8:
                    continue
                keep, drop = first, second
                if second.confirmed and not first.confirmed:
                    keep, drop = second, first
                removed.add(drop.id)
                if drop.id == first_id:
                    break
        for track_id in removed:
            self.tracks.pop(track_id, None)

    # ------------------------------------------------------------------
    # Actualización
    # ------------------------------------------------------------------
    def update(
        self, rects: list[tuple[float, float, float, float]], now: float
    ) -> dict[int, Track]:
        """Actualiza el estado con las cajas detectadas en el frame actual."""
        rects = [tuple(float(v) for v in rect) for rect in rects]
        detections = [self._rect_centroid(rect) for rect in rects]

        if not self.tracks:
            for rect, centroid in zip(rects, detections):
                self._register(centroid, rect, now)
            self._remove_duplicates()
            return self.tracks

        if not detections:
            for track in list(self.tracks.values()):
                track.missed += 1
                limit = self.max_disappeared if track.confirmed else max(2, self.min_hits)
                if track.missed > limit:
                    del self.tracks[track.id]
            return self.tracks

        track_ids = list(self.tracks.keys())
        candidates: list[tuple[float, int, int]] = []
        for i, track_id in enumerate(track_ids):
            track = self.tracks[track_id]
            gate = self._gate(track)
            for j, rect in enumerate(rects):
                distance = float(
                    np.hypot(
                        track.centroid[0] - detections[j][0],
                        track.centroid[1] - detections[j][1],
                    )
                )
                overlap = _iou(track.box, rect)
                if overlap < 0.05 and distance > gate:
                    continue
                # Costo bajo = mejor coincidencia. Se penaliza un gran cambio de
                # tamaño (no suele ser la misma persona en un solo ciclo).
                size_ratio = (rect[3] + 1.0) / (track.box[3] + 1.0)
                size_penalty = abs(np.log(size_ratio))
                cost = (1.0 - overlap) + distance / max(gate, 1.0) + 0.5 * size_penalty
                candidates.append((cost, i, j))

        candidates.sort(key=lambda item: item[0])
        matched_tracks: set[int] = set()
        matched_detections: set[int] = set()

        for _, track_index, detection_index in candidates:
            if track_index in matched_tracks or detection_index in matched_detections:
                continue
            track = self.tracks[track_ids[track_index]]
            track.update(
                detections[detection_index], rects[detection_index], now, self.smoothing
            )
            self._confirm(track)
            matched_tracks.add(track_index)
            matched_detections.add(detection_index)

        # Pistas sin detección: envejecen y eventualmente se eliminan. Las que
        # nunca se confirmaron se eliminan rápido (eran ruido).
        for track_index, track_id in enumerate(track_ids):
            if track_index in matched_tracks:
                continue
            track = self.tracks[track_id]
            track.missed += 1
            limit = self.max_disappeared if track.confirmed else max(2, self.min_hits)
            if track.missed > limit:
                del self.tracks[track_id]

        # Detecciones nuevas: no se crea una pista si la caja está casi
        # completamente dentro de una persona ya seguida (cabeza, brazos...).
        for detection_index, centroid in enumerate(detections):
            if detection_index in matched_detections:
                continue
            rect = rects[detection_index]
            if any(
                _containment(rect, track.box) > 0.7 and track.missed <= 2
                for track in self.tracks.values()
            ):
                continue
            self._register(centroid, rect, now)

        self._remove_duplicates()
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
