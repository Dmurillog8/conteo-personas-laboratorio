"""Regresiones de precisión del conteo.

Casos observados en pruebas reales con cámara web:
* una sola persona se contaba como 3 (cuerpo + cabeza + piernas);
* una persona parada sobre la línea sumaba entradas/salidas repetidas.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from django.test import SimpleTestCase

from apps.monitoring.services.counter import PeopleCounter
from apps.monitoring.services.detectors import (
    DetectorUnavailable,
    DnnPersonDetector,
    default_model_path,
    merge_fragments,
    suppress_contained,
)
from apps.monitoring.services.tracker import CentroidTracker

from .test_counter import SequenceDetector


def _frame(width=640, height=480):
    return np.zeros((height, width, 3), dtype=np.uint8)


class FragmentTests(SimpleTestCase):
    def test_suppress_contained_removes_head_and_legs(self):
        body = (190, 120, 130, 290)
        head = (225, 120, 40, 90)
        legs = (230, 330, 40, 80)
        kept, _ = suppress_contained([head, body, legs], [0.9, 0.8, 0.7])
        self.assertEqual(kept, [body])

    def test_suppress_contained_keeps_two_people_side_by_side(self):
        boxes = [(100, 100, 80, 220), (200, 110, 80, 210)]
        kept, _ = suppress_contained(boxes, [0.9, 0.9])
        self.assertEqual(len(kept), 2)

    def test_merge_fragments_joins_stacked_pieces(self):
        head = (230, 100, 40, 50)
        torso = (215, 160, 70, 120)
        legs = (225, 290, 50, 110)
        merged = merge_fragments([head, torso, legs], gap_x=10, gap_y=20)
        self.assertEqual(len(merged), 1)
        x, y, w, h = merged[0]
        self.assertEqual((x, y), (215, 100))
        self.assertEqual(y + h, 400)


class OnePersonTests(SimpleTestCase):
    def test_fragmented_detections_count_as_one_person(self):
        body = (190, 120, 130, 290)
        head = (225, 120, 40, 90)
        legs = (230, 330, 40, 80)
        frames = []
        for step in range(30):
            boxes = [body]
            # Fragmentos que aparecen y desaparecen como en MOG2.
            if step % 2 == 0:
                boxes.append(head)
            if step % 3 == 0:
                boxes.append(legs)
            frames.append(boxes)
        counter = PeopleCounter(
            SequenceDetector(frames), min_hits=3, detect_every=1, max_disappeared=10
        )
        stats = None
        for _ in frames:
            _, stats, _ = counter.process(_frame())
        self.assertEqual(stats.current, 1)
        self.assertEqual(stats.unique, 1)
        self.assertEqual(stats.peak, 1)

    def test_person_standing_on_the_line_does_not_add_counts(self):
        # Centro oscilando alrededor de la línea (x=320) con ruido de ±12 px.
        rng = np.random.default_rng(4)
        frames = [[(int(300 + rng.integers(-12, 13)), 150, 40, 120)] for _ in range(60)]
        counter = PeopleCounter(SequenceDetector(frames), min_hits=2, detect_every=1)
        for _ in frames:
            counter.process(_frame())
        self.assertEqual(counter.entries + counter.exits, 0)

    def test_round_trip_counts_one_entry_and_one_exit(self):
        forward = list(range(180, 440, 15))
        path = forward + forward[::-1]
        frames = [[(x, 150, 60, 160)] for x in path]
        counter = PeopleCounter(SequenceDetector(frames), min_hits=2, detect_every=1)
        for _ in frames:
            counter.process(_frame())
        self.assertEqual(counter.entries, 1)
        self.assertEqual(counter.exits, 1)

    def test_large_close_person_keeps_identifier_with_fast_motion(self):
        # Persona cerca de la cámara: caja grande que se desplaza 70 px por ciclo.
        tracker = CentroidTracker(min_hits=2)
        for step in range(8):
            tracker.update([(60 + step * 70, 40, 180, 400)], now=step * 0.1)
        self.assertEqual(tracker.total_confirmed, 1)
        self.assertEqual(len(tracker.tracks), 1)

    def test_occupancy_does_not_flicker_on_single_missed_detection(self):
        person = (100, 100, 60, 160)
        frames = [[person]] * 6 + [[]] + [[person]] * 3 + [[person, (400, 100, 60, 160)]] + [[person]] * 3
        counter = PeopleCounter(SequenceDetector(frames), min_hits=2, detect_every=1)
        values = []
        for _ in frames:
            _, stats, _ = counter.process(_frame())
            values.append(stats.current)
        self.assertEqual(values[-8:], [1] * 8)


class DnnDetectorTests(SimpleTestCase):
    def _detector(self):
        if not default_model_path().exists():
            self.skipTest("Modelo YOLO no descargado (python scripts/download_models.py)")
        # Un archivo presente pero ilegible/corrupto debe fallar, no ocultarse como omitido.
        return DnnPersonDetector()

    def test_empty_frame_has_no_people(self):
        detector = self._detector()
        self.assertEqual(detector.detect(_frame()), [])

    def test_boxes_are_inside_frame(self):
        detector = self._detector()
        rng = np.random.default_rng(1)
        frame = rng.integers(0, 255, (360, 640, 3), dtype=np.uint8)
        for x, y, w, h in detector.detect(frame):
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, 640)
            self.assertLessEqual(y + h, 360)

    def test_model_loads_and_runs_from_unicode_path(self):
        self._detector()
        with TemporaryDirectory(prefix="labcount-construcción-") as folder:
            path = Path(folder) / "detección-personas.onnx"
            path.write_bytes(default_model_path().read_bytes())
            detector = DnnPersonDetector(model_path=path)
            self.assertEqual(detector.detect(_frame()), [])

    def test_corrupt_model_reports_unavailable(self):
        with TemporaryDirectory() as folder:
            path = Path(folder) / "invalid.onnx"
            path.write_bytes(b"not an ONNX model")
            with self.assertRaises(DetectorUnavailable):
                DnnPersonDetector(model_path=path)
