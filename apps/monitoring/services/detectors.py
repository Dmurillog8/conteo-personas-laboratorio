"""Detectores de personas basados exclusivamente en OpenCV.

Se ofrecen tres estrategias:

* ``hog``    : descriptor HOG + SVM incluido en OpenCV (personas de cuerpo completo).
* ``motion`` : sustracción de fondo MOG2 + análisis de contornos (cámara fija).
* ``hybrid`` : combinación de ambas para mejorar la cobertura.

Todas las clases devuelven cajas ``(x, y, ancho, alto)`` en coordenadas del
frame original, lo que mantiene el resto del sistema independiente del
algoritmo de detección elegido.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


Box = tuple[int, int, int, int]


def _nms(boxes: list[Box], scores: list[float], threshold: float = 0.4) -> list[Box]:
    """Non-Maximum Suppression usando OpenCV DNN."""
    if not boxes:
        return []
    if len(boxes) == 1:
        return boxes
    bboxes = [[int(x), int(y), int(w), int(h)] for x, y, w, h in boxes]
    strengths = [float(score) for score in scores]
    try:
        indices = cv2.dnn.NMSBoxes(bboxes, strengths, 0.0, threshold)
        if indices is None or len(indices) == 0:
            return []
        return [boxes[int(index)] for index in np.array(indices).flatten()]
    except cv2.error:
        return boxes


@dataclass
class Detection:
    """Resultado interno de un detector (no se persiste)."""

    box: Box
    score: float = 1.0


class BaseDetector:
    name = "base"
    label = "Detector"

    def detect(self, frame: np.ndarray) -> list[Box]:  # pragma: no cover - interfaz
        raise NotImplementedError


class HogPersonDetector(BaseDetector):
    """Detector de personas de cuerpo completo incluido en OpenCV."""

    name = "hog"
    label = "Personas (HOG)"

    def __init__(
        self,
        max_width: int = 560,
        scale_factor: float = 1.06,
        win_stride: tuple[int, int] = (8, 8),
        padding: tuple[int, int] = (8, 8),
        hit_threshold: float = 0.0,
        nms_threshold: float = 0.4,
    ) -> None:
        self.max_width = max(320, int(max_width))
        self.scale_factor = scale_factor
        self.win_stride = win_stride
        self.padding = padding
        self.hit_threshold = hit_threshold
        self.nms_threshold = nms_threshold
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame: np.ndarray) -> list[Box]:
        height, width = frame.shape[:2]
        if width == 0 or height == 0:
            return []

        ratio = min(1.0, self.max_width / float(width))
        if ratio < 1.0:
            small = cv2.resize(
                frame,
                (max(1, int(width * ratio)), max(1, int(height * ratio))),
                interpolation=cv2.INTER_AREA,
            )
        else:
            small = frame

        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
        rects, weights = self._hog.detectMultiScale(
            gray,
            hitThreshold=self.hit_threshold,
            winStride=self.win_stride,
            padding=self.padding,
            scale=self.scale_factor,
        )

        boxes: list[Box] = []
        scores: list[float] = []
        for index, (x, y, w, h) in enumerate(rects):
            if h <= 0 or w <= 0:
                continue
            actual_h = h / ratio
            actual_w = w / ratio
            aspect = actual_h / max(1.0, actual_w)
            # Un cuerpo humano completo es más alto que ancho.
            if aspect < 1.15 or aspect > 5.5:
                continue
            if actual_h < 96:
                continue
            box = (
                int(round(x / ratio)),
                int(round(y / ratio)),
                int(round(actual_w)),
                int(round(actual_h)),
            )
            boxes.append(box)
            score = float(weights[index]) if index < len(weights) else 1.0
            scores.append(max(score, 0.01))

        return _nms(boxes, scores, self.nms_threshold)


class MotionPersonDetector(BaseDetector):
    """Sustracción de fondo para cámaras fijas y escenas controladas."""

    name = "motion"
    label = "Movimiento (MOG2)"

    def __init__(
        self,
        history: int = 400,
        var_threshold: float = 20.0,
        warmup_frames: int = 18,
        min_area_ratio: float = 0.0014,
        min_height_ratio: float = 0.055,
        nms_threshold: float = 0.35,
    ) -> None:
        self.warmup_frames = max(1, int(warmup_frames))
        self.min_area_ratio = min_area_ratio
        self.min_height_ratio = min_height_ratio
        self.nms_threshold = nms_threshold
        self._seen_frames = 0
        self._background = cv2.createBackgroundSubtractorMOG2(
            history=history,
            varThreshold=var_threshold,
            detectShadows=True,
        )
        self._kernel_open = np.ones((3, 3), np.uint8)
        self._kernel_close = np.ones((11, 11), np.uint8)
        self._kernel_dilate = np.ones((3, 3), np.uint8)

    def detect(self, frame: np.ndarray) -> list[Box]:
        foreground = self._background.apply(frame)
        self._seen_frames += 1

        # 255 = objeto, 127 = sombra, 0 = fondo. Se descartan sombras.
        _, mask = cv2.threshold(foreground, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_open, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel_close, iterations=2)
        mask = cv2.dilate(mask, self._kernel_dilate, iterations=1)

        if self._seen_frames <= self.warmup_frames:
            return []

        height, width = frame.shape[:2]
        frame_area = float(width * height)
        min_area = max(650.0, frame_area * self.min_area_ratio)
        max_area = frame_area * 0.45
        min_height = max(36.0, height * self.min_height_ratio)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes: list[Box] = []
        scores: list[float] = []

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < min_area or area > max_area:
                continue

            x, y, w, h = cv2.boundingRect(contour)
            if w < 12 or h < min_height:
                continue

            aspect = h / float(max(1, w))
            if aspect < 1.05 or aspect > 6.5:
                continue

            fill_ratio = area / float(max(1, w * h))
            if fill_ratio < 0.12:
                continue

            boxes.append((int(x), int(y), int(w), int(h)))
            scores.append(min(1.0, 0.5 + area / (frame_area * 0.02)))

        return _nms(boxes, scores, self.nms_threshold)


class HybridPersonDetector(BaseDetector):
    """Combina HOG y movimiento; el HOG se ejecuta con menor frecuencia."""

    name = "hybrid"
    label = "Híbrido (HOG + movimiento)"

    def __init__(self, hog_every: int = 2) -> None:
        self.hog = HogPersonDetector()
        self.motion = MotionPersonDetector()
        self.hog_every = max(1, int(hog_every))
        self._calls = 0
        self._last_hog_boxes: list[Box] = []

    def detect(self, frame: np.ndarray) -> list[Box]:
        motion_boxes = self.motion.detect(frame)
        self._calls += 1
        if self._calls % self.hog_every == 0:
            self._last_hog_boxes = self.hog.detect(frame)

        boxes = list(self._last_hog_boxes) + list(motion_boxes)
        scores = [1.0] * len(self._last_hog_boxes) + [0.9] * len(motion_boxes)
        return _nms(boxes, scores, nms_threshold=0.35)


def create_detector(mode: str) -> BaseDetector:
    """Fábrica de detectores a partir del modo guardado en la sesión."""
    mode = (mode or "hybrid").lower()
    if mode == "hog":
        return HogPersonDetector()
    if mode == "motion":
        return MotionPersonDetector()
    return HybridPersonDetector()
