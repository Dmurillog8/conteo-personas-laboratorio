"""Escena sintética de laboratorio para demostrar el sistema sin cámara.

La escena se dibuja con OpenCV y varias personas caminan frente a una cámara
fija. El modo ``demo`` está pensado para presentaciones y pruebas: entrega
las cajas de las figuras directamente al rastreador, evitando depender de la
calidad de un detector sobre gráficos generados.
"""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

import cv2
import numpy as np

from .detectors import BaseDetector, Box


@dataclass
class DemoPerson:
    x: float
    y: float
    speed: float
    scale: float
    color: tuple[int, int, int]
    phase: float
    name: str = ""

    @property
    def direction(self) -> int:
        return 1 if self.speed >= 0 else -1

    @property
    def height(self) -> float:
        return 156.0 * self.scale

    @property
    def width(self) -> float:
        return 52.0 * self.scale

    def bounding_box(self) -> Box:
        w = int(self.width * 1.25)
        h = int(self.height * 1.03)
        return (int(self.x - w / 2), int(self.y - h), w, h)


class DemoScene:
    """Generador de frames 960x540 con personas caminando."""

    WIDTH = 960
    HEIGHT = 540

    def __init__(self, people: int = 5, seed: int = 7) -> None:
        self.width = self.WIDTH
        self.height = self.HEIGHT
        self._random = random.Random(seed)
        self._background = self._build_background()
        self._last_time = time.perf_counter()
        self._elapsed = 0.0
        self._boxes: list[Box] = []
        self.people: list[DemoPerson] = [
            self._make_person(
                x=self._random.uniform(80, self.width - 80),
                direction=self._random.choice([-1, 1]),
            )
            for _ in range(max(3, people))
        ]
        # Aseguramos que la primera escena muestre personas distribuidas.
        for index, person in enumerate(self.people):
            person.x = 120 + index * ((self.width - 240) / max(1, len(self.people) - 1))
            if index % 2:
                person.speed = -abs(person.speed)
            else:
                person.speed = abs(person.speed)

    # ------------------------------------------------------------------
    # Construcción
    # ------------------------------------------------------------------
    def _make_person(self, x: float, direction: int) -> DemoPerson:
        palette = [
            (196, 128, 58),   # azul acero (BGR)
            (92, 196, 172),   # turquesa
            (72, 108, 232),   # coral
            (188, 108, 176),  # violeta
            (96, 184, 92),    # verde
            (60, 154, 236),   # ámbar
        ]
        scale = self._random.uniform(0.82, 1.08)
        y = self._random.uniform(360.0, 505.0)
        # Las personas más lejanas (más arriba) se dibujan más pequeñas.
        scale *= 0.78 + ((y - 360.0) / 145.0) * 0.32
        speed = self._random.uniform(52.0, 92.0) * direction
        return DemoPerson(
            x=x,
            y=y,
            speed=speed,
            scale=scale,
            color=self._random.choice(palette),
            phase=self._random.uniform(0.0, math.tau),
        )

    def _build_background(self) -> np.ndarray:
        width, height = self.width, self.height
        image = np.zeros((height, width, 3), dtype=np.uint8)

        # Pared con degradado vertical.
        for y in range(height):
            factor = y / height
            color = (
                int(24 + 16 * factor),
                int(29 + 18 * factor),
                int(38 + 20 * factor),
            )
            image[y, :] = color

        horizon = 332
        # Piso con perspectiva.
        floor_color = (34, 39, 47)
        cv2.rectangle(image, (0, horizon), (width, height), floor_color, -1)
        vanish = (width // 2, horizon)
        for offset in range(-900, 901, 150):
            end = (vanish[0] + offset, height)
            cv2.line(image, vanish, end, (47, 54, 64), 1, cv2.LINE_AA)
        for step in range(1, 7):
            y = horizon + int((height - horizon) * (step / 6.0) ** 1.7)
            cv2.line(image, (0, y), (width, y), (44, 50, 60), 1, cv2.LINE_AA)

        # Zócalo y paneles de pared.
        cv2.rectangle(image, (0, horizon - 8), (width, horizon + 2), (56, 63, 74), -1)
        for x in range(60, width - 80, 210):
            cv2.rectangle(image, (x, 74), (x + 160, 274), (35, 42, 52), -1)
            cv2.rectangle(image, (x, 74), (x + 160, 274), (49, 57, 69), 2, cv2.LINE_AA)
            cv2.line(image, (x + 8, 264), (x + 152, 264), (63, 72, 86), 2, cv2.LINE_AA)

        # Pizarra y puerta.
        cv2.rectangle(image, (56, 92), (330, 250), (174, 181, 184), -1)
        cv2.rectangle(image, (56, 92), (330, 250), (204, 210, 212), 3, cv2.LINE_AA)
        cv2.putText(
            image,
            "LABORATORIO P",
            (80, 132),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.62,
            (70, 76, 80),
            2,
            cv2.LINE_AA,
        )
        for idx, length in enumerate((150, 120, 180)):
            cv2.line(
                image,
                (82, 165 + idx * 22),
                (82 + length, 165 + idx * 22),
                (118, 126, 130),
                2,
                cv2.LINE_AA,
            )

        cv2.rectangle(image, (width - 172, 76), (width - 38, horizon - 4), (29, 35, 45), -1)
        cv2.rectangle(
            image, (width - 172, 76), (width - 38, horizon - 4), (62, 70, 84), 3, cv2.LINE_AA
        )
        cv2.circle(image, (width - 58, 232), 4, (90, 190, 200), -1, cv2.LINE_AA)

        # Lámparas del techo.
        for cx in (250, 710):
            cv2.ellipse(image, (cx, 34), (86, 16), 0, 0, 360, (86, 96, 108), -1, cv2.LINE_AA)
            cv2.ellipse(image, (cx, 30), (76, 10), 0, 0, 360, (172, 196, 205), -1, cv2.LINE_AA)

        # Escritorios laterales, fuera de la zona de conteo.
        cv2.fillPoly(
            image,
            [np.array([(0, 390), (126, 370), (182, 540), (0, 540)], dtype=np.int32)],
            (38, 44, 54),
        )
        cv2.line(image, (0, 390), (126, 370), (63, 72, 84), 3, cv2.LINE_AA)
        cv2.fillPoly(
            image,
            [np.array([(width, 390), (width - 126, 370), (width - 182, 540), (width, 540)], dtype=np.int32)],
            (38, 44, 54),
        )
        cv2.line(image, (width, 390), (width - 126, 370), (63, 72, 84), 3, cv2.LINE_AA)
        cv2.putText(
            image,
            "ZONA DE CONTEO",
            (width // 2 - 92, horizon + 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (78, 88, 100),
            1,
            cv2.LINE_AA,
        )

        # Viñeta suave para dar profundidad.
        overlay = np.zeros_like(image)
        cv2.circle(
            overlay,
            (width // 2, height // 2),
            int(width * 0.72),
            (18, 22, 30),
            thickness=-1,
            lineType=cv2.LINE_AA,
        )
        image = cv2.addWeighted(image, 0.90, overlay, 0.10, 0)
        return image

    # ------------------------------------------------------------------
    # Animación
    # ------------------------------------------------------------------
    @staticmethod
    def _draw_person(
        image: np.ndarray, person: DemoPerson, elapsed: float, frame_width: int
    ) -> None:
        feet_x = person.x
        feet_y = person.y
        height = person.height
        width = person.width
        scale = person.scale
        stride = math.sin(elapsed * 7.0 * (abs(person.speed) / 70.0) + person.phase)
        swing = 13.0 * scale * stride
        direction = person.direction

        hip_y = feet_y - height * 0.42
        shoulder_y = feet_y - height * 0.78
        head_radius = max(8, int(12.0 * scale))
        head_center = (int(feet_x), int(shoulder_y - head_radius * 1.15))

        # Sombra.
        cv2.ellipse(
            image,
            (int(feet_x), int(feet_y + 3)),
            (int(width * 0.9), max(4, int(8 * scale))),
            0,
            0,
            360,
            (20, 24, 30),
            -1,
            cv2.LINE_AA,
        )

        # Piernas.
        leg_color = (42, 48, 58)
        for sign in (-1, 1):
            start = (int(feet_x + sign * width * 0.16), int(hip_y))
            end = (
                int(feet_x + sign * width * 0.18 + swing * sign),
                int(feet_y - 2),
            )
            cv2.line(image, start, end, leg_color, max(5, int(9 * scale)), cv2.LINE_AA)
            cv2.circle(image, end, max(3, int(5 * scale)), (28, 32, 40), -1, cv2.LINE_AA)

        # Brazos.
        arm_color = person.color
        for sign in (-1, 1):
            shoulder = (int(feet_x + sign * width * 0.41), int(shoulder_y + 6 * scale))
            elbow = (
                int(feet_x + sign * width * 0.55),
                int(hip_y - 8 * scale - swing * 0.35 * sign),
            )
            hand = (
                int(feet_x + sign * width * 0.46 + swing * 0.35 * sign),
                int(hip_y + 10 * scale),
            )
            cv2.line(image, shoulder, elbow, arm_color, max(4, int(7 * scale)), cv2.LINE_AA)
            cv2.line(image, elbow, hand, arm_color, max(4, int(6 * scale)), cv2.LINE_AA)
            cv2.circle(image, hand, max(2, int(3.6 * scale)), (132, 170, 205), -1, cv2.LINE_AA)

        # Torso con hombros redondeados.
        torso = np.array(
            [
                (int(feet_x - width * 0.40), int(shoulder_y)),
                (int(feet_x + width * 0.40), int(shoulder_y)),
                (int(feet_x + width * 0.33), int(hip_y + 4 * scale)),
                (int(feet_x - width * 0.33), int(hip_y + 4 * scale)),
            ],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(image, torso, person.color, cv2.LINE_AA)
        cv2.circle(
            image,
            (int(feet_x), int(shoulder_y)),
            max(5, int(13 * scale)),
            person.color,
            -1,
            cv2.LINE_AA,
        )

        # Cuello, cabeza y cabello.
        cv2.line(
            image,
            (int(feet_x), int(shoulder_y - 2)),
            (int(feet_x), int(shoulder_y - 8)),
            (138, 174, 205),
            max(5, int(8 * scale)),
            cv2.LINE_AA,
        )
        cv2.circle(image, head_center, head_radius, (136, 174, 209), -1, cv2.LINE_AA)
        hair_height = max(4, int(head_radius * 0.55))
        cv2.ellipse(
            image,
            (head_center[0], head_center[1] - int(head_radius * 0.25)),
            (head_radius, hair_height),
            0,
            180,
            360,
            (34, 38, 46),
            -1,
            cv2.LINE_AA,
        )

        # Gafete del laboratorio.
        badge_x = int(feet_x + direction * width * 0.18)
        cv2.rectangle(
            image,
            (badge_x - max(4, int(5 * scale)), int(shoulder_y + 12 * scale)),
            (badge_x + max(4, int(5 * scale)), int(shoulder_y + 26 * scale)),
            (220, 226, 232),
            -1,
            cv2.LINE_AA,
        )

    def next_frame(self) -> np.ndarray:
        now = time.perf_counter()
        delta = min(0.12, max(0.0, now - self._last_time))
        self._last_time = now
        self._elapsed += delta

        frame = self._background.copy()
        width = self.width
        boxes: list[Box] = []

        for person in sorted(self.people, key=lambda item: item.y):
            person.x += person.speed * delta
            margin = person.width
            if person.speed > 0 and person.x > width + margin:
                replacement = self._make_person(-margin, -1)
                person.x, person.y, person.speed = replacement.x, replacement.y, replacement.speed
                person.scale, person.color, person.phase = (
                    replacement.scale,
                    replacement.color,
                    replacement.phase,
                )
            elif person.speed < 0 and person.x < -margin:
                replacement = self._make_person(width + margin, 1)
                person.x, person.y, person.speed = replacement.x, replacement.y, replacement.speed
                person.scale, person.color, person.phase = (
                    replacement.scale,
                    replacement.color,
                    replacement.phase,
                )

            self._draw_person(frame, person, self._elapsed, width)
            boxes.append(person.bounding_box())

        self._boxes = [
            (
                max(0, box[0]),
                max(0, box[1]),
                min(box[2], width - max(0, box[0])),
                min(box[3], self.height - max(0, box[1])),
            )
            for box in boxes
        ]
        # Un borde de color identifica el modo demostración.
        cv2.rectangle(frame, (0, 0), (width - 1, self.height - 1), (34, 211, 238), 2)
        return frame

    def boxes(self) -> list[Box]:
        return list(self._boxes)

    def background_frame(self) -> np.ndarray:
        return self._background.copy()


class DemoPersonDetector(BaseDetector):
    """Detector del modo demostración basado en la escena sintética."""

    name = "demo"
    label = "Demostración sintética"

    def __init__(self, scene: DemoScene) -> None:
        self.scene = scene

    def detect(self, frame: np.ndarray) -> list[Box]:
        return self.scene.boxes()
