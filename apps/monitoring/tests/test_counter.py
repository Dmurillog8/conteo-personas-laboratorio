import unittest

import numpy as np
from django.test import SimpleTestCase

from apps.monitoring.services.counter import PeopleCounter
from apps.monitoring.services.detectors import BaseDetector


class SequenceDetector(BaseDetector):
    name = "sequence"
    label = "Secuencia de prueba"

    def __init__(self, boxes_per_frame):
        self.boxes_per_frame = list(boxes_per_frame)
        self.index = 0

    def detect(self, frame):
        if self.index >= len(self.boxes_per_frame):
            return []
        boxes = self.boxes_per_frame[self.index]
        self.index += 1
        return boxes


class CounterTests(SimpleTestCase):
    def _frame(self, width=640, height=480):
        return np.zeros((height, width, 3), dtype=np.uint8)

    def _counter(self, boxes, orientation="vertical", min_hits=1):
        detector = SequenceDetector(boxes)
        return PeopleCounter(
            detector=detector,
            line_orientation=orientation,
            line_position=0.5,
            min_hits=min_hits,
            max_disappeared=6,
            presence_max_missed=2,
            detect_every=1,
        )

    def test_counts_entry_crossing_vertical_line(self):
        # El centro pasa de x=270 a x=330 (línea en x=320).
        boxes = [[(x, 150, 40, 120)] for x in range(250, 391, 20)]
        counter = self._counter(boxes)
        last_stats = None
        for _ in range(len(boxes) + 3):
            _, last_stats, _ = counter.process(self._frame())
        self.assertIsNotNone(last_stats)
        self.assertEqual(counter.entries, 1)
        self.assertEqual(counter.exits, 0)
        self.assertEqual(last_stats.unique, 1)
        self.assertEqual(last_stats.entries, 1)

    def test_counts_exit_crossing_vertical_line(self):
        boxes = [[(x, 150, 40, 120)] for x in range(390, 249, -20)]
        counter = self._counter(boxes)
        for _ in range(len(boxes) + 3):
            _, last_stats, _ = counter.process(self._frame())
        self.assertEqual(counter.exits, 1)
        self.assertEqual(counter.entries, 0)
        self.assertEqual(last_stats.exits, 1)

    def test_horizontal_line_direction(self):
        boxes = [[(200, y, 60, 100)] for y in range(180, 321, 20)]
        counter = self._counter(boxes, orientation="horizontal")
        for _ in range(len(boxes) + 3):
            _, last_stats, _ = counter.process(self._frame())
        self.assertEqual(counter.entries, 1)
        self.assertEqual(last_stats.entries, 1)

    def test_does_not_count_the_same_crossing_twice(self):
        # La persona avanza de forma realista, cruza una vez y permanece
        # al otro lado de la línea: no debe registrarse una segunda entrada.
        positions = [250, 285, 315, 345, 350, 350, 350]
        boxes = [[(x, 150, 40, 120)] for x in positions]
        counter = self._counter(boxes)
        for _ in range(len(boxes)):
            counter.process(self._frame())
        self.assertEqual(counter.entries, 1)
        self.assertEqual(counter.exits, 0)
        self.assertEqual(counter.tracker.total_confirmed, 1)

    def test_occupancy_returns_to_zero_after_leaving(self):
        boxes = [[(250, 150, 40, 120)]]
        counter = self._counter(boxes)
        _, stats, _ = counter.process(self._frame())
        self.assertEqual(stats.current, 1)
        for _ in range(10):
            _, stats, _ = counter.process(self._frame())
        self.assertEqual(stats.current, 0)

    def test_annotated_frame_keeps_dimensions(self):
        boxes = [[(200, 150, 40, 120)]]
        counter = self._counter(boxes)
        annotated, stats, crossings = counter.process(self._frame())
        self.assertEqual(annotated.shape, (480, 640, 3))
        self.assertEqual(annotated.dtype, np.uint8)
        self.assertIsInstance(stats.as_dict(), dict)
        self.assertIsInstance(crossings, list)

    def test_line_position_is_clamped(self):
        counter = PeopleCounter(SequenceDetector([]), line_position=5)
        self.assertEqual(counter.line_position, 0.9)
        counter = PeopleCounter(SequenceDetector([]), line_position=-2)
        self.assertEqual(counter.line_position, 0.1)


if __name__ == "__main__":
    unittest.main()
