"""Detectores de personas basados exclusivamente en OpenCV.

Se ofrecen cuatro estrategias:

* ``dnn``    : red neuronal YOLO (ONNX) ejecutada con ``cv2.dnn``. Es la más
               precisa: detecta personas de cuerpo completo o parcial, de
               frente, de lado o sentadas. Recomendada.
* ``hog``    : descriptor HOG + SVM incluido en OpenCV (cuerpo completo).
* ``motion`` : sustracción de fondo MOG2 + análisis de contornos (cámara fija).
* ``hybrid`` : HOG + movimiento.

Todas las clases devuelven cajas ``(x, y, ancho, alto)`` en coordenadas del
frame original, lo que mantiene el resto del sistema independiente del
algoritmo de detección elegido.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger("apps.monitoring")

Box = tuple[int, int, int, int]


# ----------------------------------------------------------------------
# Utilidades geométricas
# ----------------------------------------------------------------------
def _intersection(a: Box, b: Box) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    return float(max(0, x2 - x1) * max(0, y2 - y1))


def iou(a: Box, b: Box) -> float:
    inter = _intersection(a, b)
    if inter <= 0:
        return 0.0
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / float(max(1.0, union))


def containment(inner: Box, outer: Box) -> float:
    """Fracción del área de ``inner`` que queda dentro de ``outer``."""
    area = float(max(1, inner[2] * inner[3]))
    return _intersection(inner, outer) / area


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


def suppress_contained(
    boxes: list[Box], scores: list[float], threshold: float = 0.6
) -> tuple[list[Box], list[float]]:
    """Elimina cajas que están mayormente dentro de otra caja más grande.

    El NMS clásico (IoU) no elimina una caja pequeña de la cabeza o de las
    piernas que vive dentro de la caja del cuerpo, porque su IoU es bajo.
    Ese caso producía una sola persona contada como dos o tres.
    """
    if len(boxes) < 2:
        return list(boxes), list(scores)
    order = sorted(range(len(boxes)), key=lambda i: boxes[i][2] * boxes[i][3], reverse=True)
    kept: list[int] = []
    for index in order:
        box = boxes[index]
        if any(containment(box, boxes[other]) >= threshold for other in kept):
            continue
        kept.append(index)
    kept.sort()
    return [boxes[i] for i in kept], [scores[i] for i in kept]


def merge_fragments(boxes: list[Box], gap_x: int, gap_y: int) -> list[Box]:
    """Une cajas cercanas (fragmentos de una misma silueta) en una sola."""
    merged = [list(box) for box in boxes]
    changed = True
    while changed and len(merged) > 1:
        changed = False
        for i in range(len(merged)):
            for j in range(i + 1, len(merged)):
                ax, ay, aw, ah = merged[i]
                bx, by, bw, bh = merged[j]
                horizontal_gap = max(ax, bx) - min(ax + aw, bx + bw)
                vertical_gap = max(ay, by) - min(ay + ah, by + bh)
                # Fragmentos apilados (cabeza / torso / piernas) o solapados.
                overlap_x = min(ax + aw, bx + bw) - max(ax, bx)
                min_w = max(1, min(aw, bw))
                stacked = overlap_x >= 0.35 * min_w and vertical_gap <= gap_y
                touching = horizontal_gap <= gap_x and vertical_gap <= 0
                if stacked or touching:
                    x1, y1 = min(ax, bx), min(ay, by)
                    x2, y2 = max(ax + aw, bx + bw), max(ay + ah, by + bh)
                    merged[i] = [x1, y1, x2 - x1, y2 - y1]
                    del merged[j]
                    changed = True
                    break
            if changed:
                break
    return [tuple(int(v) for v in box) for box in merged]


def _clip(box: Box, width: int, height: int) -> Box | None:
    x, y, w, h = box
    x1, y1 = max(0, int(x)), max(0, int(y))
    x2, y2 = min(width, int(x + w)), min(height, int(y + h))
    if x2 - x1 < 2 or y2 - y1 < 2:
        return None
    return (x1, y1, x2 - x1, y2 - y1)


@dataclass
class Detection:
    """Resultado interno de un detector (no se persiste)."""

    box: Box
    score: float = 1.0


class DetectorUnavailable(RuntimeError):
    """El detector no puede usarse (por ejemplo, falta el modelo)."""


class BaseDetector:
    name = "base"
    label = "Detector"

    def detect(self, frame: np.ndarray) -> list[Box]:  # pragma: no cover - interfaz
        raise NotImplementedError


# ----------------------------------------------------------------------
# Red neuronal YOLO (OpenCV DNN)
# ----------------------------------------------------------------------
def default_model_path() -> Path:
    try:
        from django.conf import settings

        configured = getattr(settings, "LABCOUNT_DNN_MODEL", "")
        if configured:
            return Path(configured)
        return Path(settings.BASE_DIR) / "models" / "yolov5n.onnx"
    except Exception:  # pragma: no cover - fuera de Django
        return Path(__file__).resolve().parents[3] / "models" / "yolov5n.onnx"


class DnnPersonDetector(BaseDetector):
    """Detector YOLO (v5/v8 exportado a ONNX) ejecutado con ``cv2.dnn``.

    Solo se conserva la clase 0 de COCO (``person``). La imagen se adapta con
    *letterbox* para no deformar a las personas, lo que mejora mucho la
    precisión frente a un simple redimensionado.
    """

    name = "dnn"
    label = "Red neuronal (YOLO · OpenCV DNN)"

    def __init__(
        self,
        model_path: str | Path | None = None,
        confidence: float = 0.45,
        nms_threshold: float = 0.45,
        input_size: int = 640,
        min_height_ratio: float = 0.08,
    ) -> None:
        path = Path(model_path) if model_path else default_model_path()
        if not path.exists():
            raise DetectorUnavailable(
                f"No se encontró el modelo YOLO en '{path}'. "
                "Ejecute: python scripts/download_models.py"
            )
        try:
            self._net = cv2.dnn.readNetFromONNX(str(path))
        except cv2.error as exc:
            raise DetectorUnavailable(f"OpenCV no pudo cargar el modelo: {exc}") from exc
        try:
            self._net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
            self._net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        except (cv2.error, AttributeError):  # pragma: no cover
            pass
        self.model_path = path
        self.confidence = float(confidence)
        self.nms_threshold = float(nms_threshold)
        self.input_size = int(input_size)
        self.min_height_ratio = float(min_height_ratio)

    def _letterbox(self, frame: np.ndarray) -> tuple[np.ndarray, float]:
        height, width = frame.shape[:2]
        scale = self.input_size / float(max(height, width))
        new_w, new_h = max(1, int(round(width * scale))), max(1, int(round(height * scale)))
        canvas = np.full((self.input_size, self.input_size, 3), 114, dtype=np.uint8)
        canvas[:new_h, :new_w] = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        return canvas, scale

    def detect(self, frame: np.ndarray) -> list[Box]:
        height, width = frame.shape[:2]
        if width == 0 or height == 0:
            return []

        canvas, scale = self._letterbox(frame)
        blob = cv2.dnn.blobFromImage(
            canvas, 1 / 255.0, (self.input_size, self.input_size), swapRB=True, crop=False
        )
        self._net.setInput(blob)
        output = self._net.forward()
        predictions = np.squeeze(output)
        if predictions.ndim != 2:
            return []
        # YOLOv8 exporta (84, 8400); YOLOv5 (25200, 85).
        if predictions.shape[0] < predictions.shape[1]:
            predictions = predictions.T

        columns = predictions.shape[1]
        if columns == 85:  # YOLOv5: x, y, w, h, objectness, 80 clases
            scores_all = predictions[:, 4] * predictions[:, 5]
        elif columns == 84:  # YOLOv8: x, y, w, h, 80 clases
            scores_all = predictions[:, 4]
        else:
            scores_all = predictions[:, 4] * predictions[:, 5]

        # Para que "persona" sea la clase ganadora, se exige que su puntaje sea
        # el mayor entre las clases (evita confundir sillas o mochilas).
        class_offset = 5 if columns == 85 else 4
        class_scores = predictions[:, class_offset:]
        is_person = np.argmax(class_scores, axis=1) == 0
        mask = (scores_all >= self.confidence) & is_person
        if not np.any(mask):
            return []

        selected = predictions[mask]
        confidences = scores_all[mask]
        min_height = height * self.min_height_ratio

        boxes: list[Box] = []
        scores: list[float] = []
        for row, score in zip(selected, confidences):
            cx, cy, bw, bh = row[:4] / scale
            box = _clip((cx - bw / 2.0, cy - bh / 2.0, bw, bh), width, height)
            if box is None or box[3] < min_height:
                continue
            boxes.append(box)
            scores.append(float(score))

        kept = _nms(boxes, scores, self.nms_threshold)
        kept_scores = [scores[boxes.index(box)] for box in kept]
        kept, _ = suppress_contained(kept, kept_scores, 0.75)
        return kept


# ----------------------------------------------------------------------
# HOG
# ----------------------------------------------------------------------
class HogPersonDetector(BaseDetector):
    """Detector de personas de cuerpo completo incluido en OpenCV."""

    name = "hog"
    label = "Personas (HOG)"

    def __init__(
        self,
        max_width: int = 640,
        scale_factor: float = 1.05,
        win_stride: tuple[int, int] = (8, 8),
        padding: tuple[int, int] = (8, 8),
        hit_threshold: float = 0.0,
        min_weight: float = 0.35,
        nms_threshold: float = 0.4,
    ) -> None:
        self.max_width = max(320, int(max_width))
        self.scale_factor = scale_factor
        self.win_stride = win_stride
        self.padding = padding
        self.hit_threshold = hit_threshold
        self.min_weight = min_weight
        self.nms_threshold = nms_threshold
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect_scored(self, frame: np.ndarray) -> tuple[list[Box], list[float]]:
        height, width = frame.shape[:2]
        if width == 0 or height == 0:
            return [], []

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
        gray = cv2.equalizeHist(gray)
        rects, weights = self._hog.detectMultiScale(
            gray,
            hitThreshold=self.hit_threshold,
            winStride=self.win_stride,
            padding=self.padding,
            scale=self.scale_factor,
        )

        boxes: list[Box] = []
        scores: list[float] = []
        weights = np.array(weights).flatten() if len(rects) else []
        for index, (x, y, w, h) in enumerate(rects):
            if h <= 0 or w <= 0:
                continue
            score = float(weights[index]) if index < len(weights) else 1.0
            if score < self.min_weight:
                continue
            actual_h = h / ratio
            actual_w = w / ratio
            aspect = actual_h / max(1.0, actual_w)
            if aspect < 1.15 or aspect > 5.5:
                continue
            if actual_h < 96:
                continue
            # HOG devuelve cajas con mucho margen: se recortan ~10 % por lado.
            shrink_w, shrink_h = actual_w * 0.10, actual_h * 0.05
            box = _clip(
                (
                    x / ratio + shrink_w,
                    y / ratio + shrink_h,
                    actual_w - 2 * shrink_w,
                    actual_h - 2 * shrink_h,
                ),
                width,
                height,
            )
            if box is None:
                continue
            boxes.append(box)
            scores.append(score)

        kept = _nms(boxes, scores, self.nms_threshold)
        kept_scores = [scores[boxes.index(box)] for box in kept]
        return suppress_contained(kept, kept_scores)

    def detect(self, frame: np.ndarray) -> list[Box]:
        return self.detect_scored(frame)[0]


# ----------------------------------------------------------------------
# Movimiento (MOG2)
# ----------------------------------------------------------------------
class MotionPersonDetector(BaseDetector):
    """Sustracción de fondo para cámaras fijas y escenas controladas."""

    name = "motion"
    label = "Movimiento (MOG2)"

    def __init__(
        self,
        history: int = 500,
        var_threshold: float = 32.0,
        warmup_frames: int = 25,
        min_area_ratio: float = 0.004,
        min_height_ratio: float = 0.12,
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
        self._kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        # Kernel alto: une cabeza, torso y piernas en un solo contorno.
        self._kernel_close = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 31))

    def detect(self, frame: np.ndarray) -> list[Box]:
        blurred = cv2.GaussianBlur(frame, (5, 5), 0)
        foreground = self._background.apply(blurred)
        self._seen_frames += 1

        if self._seen_frames <= self.warmup_frames:
            return []

        # 255 = objeto, 127 = sombra, 0 = fondo. Se descartan sombras.
        _, mask = cv2.threshold(foreground, 200, 255, cv2.THRESH_BINARY)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self._kernel_open, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self._kernel_close, iterations=2)

        height, width = frame.shape[:2]
        frame_area = float(width * height)

        # Cambio global de iluminación o movimiento de cámara: se ignora el frame.
        if cv2.countNonZero(mask) > frame_area * 0.55:
            return []

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        raw: list[Box] = []
        for contour in contours:
            if cv2.contourArea(contour) < frame_area * 0.0015:
                continue
            raw.append(tuple(int(v) for v in cv2.boundingRect(contour)))

        gap = max(12, int(height * 0.06))
        merged = merge_fragments(raw, gap_x=gap // 2, gap_y=gap)

        min_area = frame_area * self.min_area_ratio
        max_area = frame_area * 0.6
        min_height = height * self.min_height_ratio
        boxes: list[Box] = []
        scores: list[float] = []
        for x, y, w, h in merged:
            area = w * h
            if area < min_area or area > max_area:
                continue
            if w < 16 or h < min_height:
                continue
            aspect = h / float(max(1, w))
            if aspect < 0.9 or aspect > 6.0:
                continue
            fill_ratio = cv2.countNonZero(mask[y : y + h, x : x + w]) / float(max(1, area))
            if fill_ratio < 0.25:
                continue
            boxes.append((x, y, w, h))
            scores.append(min(1.0, 0.5 + area / (frame_area * 0.05)))

        kept = _nms(boxes, scores, self.nms_threshold)
        kept_scores = [scores[boxes.index(box)] for box in kept]
        return suppress_contained(kept, kept_scores)[0]


# ----------------------------------------------------------------------
# Híbrido
# ----------------------------------------------------------------------
class HybridPersonDetector(BaseDetector):
    """Combina HOG y movimiento.

    HOG valida que lo detectado sea una persona; el movimiento solo aporta
    cajas nuevas cuando no se solapan con una persona ya encontrada por HOG,
    y se descartan las que quedan dentro de una caja de HOG.
    """

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
        if self._calls % self.hog_every == 0 or self._calls == 1:
            self._last_hog_boxes = self.hog.detect(frame)

        hog_boxes = list(self._last_hog_boxes)
        extra: list[Box] = []
        for box in motion_boxes:
            if any(iou(box, hog) > 0.2 or containment(box, hog) > 0.4 for hog in hog_boxes):
                continue
            # Si la caja de movimiento envuelve a una de HOG, HOG manda.
            if any(containment(hog, box) > 0.6 for hog in hog_boxes):
                continue
            extra.append(box)

        boxes = hog_boxes + extra
        scores = [1.0] * len(hog_boxes) + [0.8] * len(extra)
        kept = _nms(boxes, scores, 0.35)
        kept_scores = [scores[boxes.index(box)] for box in kept]
        return suppress_contained(kept, kept_scores)[0]


def create_detector(mode: str) -> BaseDetector:
    """Fábrica de detectores a partir del modo guardado en la sesión.

    Si se pide ``dnn`` y el modelo no está disponible, se usa el híbrido para
    no impedir el monitoreo (y se registra la advertencia).
    """
    mode = (mode or "dnn").lower()
    if mode == "hog":
        return HogPersonDetector()
    if mode == "motion":
        return MotionPersonDetector()
    if mode == "hybrid":
        return HybridPersonDetector()

    try:
        from django.conf import settings

        confidence = float(getattr(settings, "LABCOUNT_DNN_CONFIDENCE", 0.45))
    except Exception:  # pragma: no cover
        confidence = 0.45
    try:
        return DnnPersonDetector(confidence=confidence)
    except DetectorUnavailable as exc:
        logger.warning("%s Se usará el detector híbrido.", exc)
        detector = HybridPersonDetector()
        detector.label = "Híbrido (modelo YOLO no encontrado)"
        return detector
