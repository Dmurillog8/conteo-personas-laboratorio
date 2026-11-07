import cv2
import numpy as np
from django.test import SimpleTestCase

from apps.monitoring.services.counter import PeopleCounter
from apps.monitoring.services.demo import DemoPersonDetector, DemoScene
from apps.monitoring.services.detectors import (
    HybridPersonDetector,
    HogPersonDetector,
    MotionPersonDetector,
)


class DemoTests(SimpleTestCase):
    def test_demo_scene_generates_valid_frames_and_boxes(self):
        scene = DemoScene(people=5, seed=3)
        frame = scene.next_frame()
        self.assertEqual(frame.shape, (540, 960, 3))
        self.assertEqual(frame.dtype, np.uint8)
        boxes = scene.boxes()
        self.assertEqual(len(boxes), 5)
        for x, y, w, h in boxes:
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)

    def test_demo_counter_detects_and_tracks_people(self):
        scene = DemoScene(people=4, seed=11)
        detector = DemoPersonDetector(scene)
        counter = PeopleCounter(
            detector=detector,
            min_hits=2,
            detect_every=1,
            max_disappeared=10,
        )
        last_stats = None
        for _ in range(40):
            frame = scene.next_frame()
            _, last_stats, _ = counter.process(frame)
        self.assertIsNotNone(last_stats)
        self.assertGreaterEqual(last_stats.current, 3)
        self.assertGreaterEqual(last_stats.unique, 4)
        self.assertGreaterEqual(last_stats.peak, 3)

    def test_demo_detector_returns_scene_boxes(self):
        scene = DemoScene(people=3, seed=5)
        detector = DemoPersonDetector(scene)
        scene.next_frame()
        self.assertEqual(detector.detect(scene.next_frame()), scene.boxes())


class DetectorTests(SimpleTestCase):
    def test_hog_detector_is_available(self):
        detector = HogPersonDetector()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        boxes = detector.detect(frame)
        self.assertIsInstance(boxes, list)

    def test_motion_detector_finds_moving_object(self):
        height, width = 480, 640
        texture = np.full((height, width, 3), 32, dtype=np.uint8)
        for x in range(0, width, 80):
            cv2.line(texture, (x, 0), (x, height), (55, 60, 70), 2)
        cv2.rectangle(texture, (40, 40), (240, 160), (70, 76, 84), -1)
        cv2.rectangle(texture, (420, 250), (590, 400), (66, 72, 80), -1)

        detector = MotionPersonDetector(warmup_frames=12)
        for _ in range(16):
            boxes = detector.detect(texture)
        self.assertEqual(boxes, [])

        found = []
        for offset in range(6):
            frame = texture.copy()
            x = 100 + offset * 30
            cv2.rectangle(frame, (x, 190), (x + 46, 330), (210, 210, 210), -1)
            cv2.circle(frame, (x + 23, 178), 14, (200, 200, 200), -1)
            found.extend(detector.detect(frame))
        self.assertGreaterEqual(len(found), 1, "MOG2 debería detectar el objeto en movimiento")

    def test_motion_detector_returns_boxes_inside_frame(self):
        detector = MotionPersonDetector(warmup_frames=1)
        frame = np.zeros((360, 640, 3), dtype=np.uint8)
        detector.detect(frame)
        for step in range(5):
            frame = np.zeros((360, 640, 3), dtype=np.uint8)
            cv2.rectangle(frame, (100 + step * 20, 100), (150 + step * 20, 280), (230, 230, 230), -1)
            boxes = detector.detect(frame)
        for x, y, w, h in boxes:
            self.assertGreaterEqual(x, 0)
            self.assertGreaterEqual(y, 0)
            self.assertLessEqual(x + w, 640)
            self.assertLessEqual(y + h, 360)

    def test_hybrid_detector_applies_nms_with_several_boxes(self):
        """Regresión: el modo híbrido fallaba al aplicar NMS con 2+ cajas."""
        height, width = 480, 640
        texture = np.full((height, width, 3), 30, dtype=np.uint8)
        for x in range(0, width, 80):
            cv2.line(texture, (x, 0), (x, height), (52, 58, 68), 2)

        detector = HybridPersonDetector()
        detector.motion.warmup_frames = 3

        boxes: list = []
        for step in range(24):
            frame = texture.copy()
            for index in range(3):
                x = 40 + index * 190 + step * 5
                cv2.rectangle(frame, (x, 180), (x + 48, 330), (215, 215, 215), -1)
                cv2.circle(frame, (x + 24, 168), 14, (205, 205, 205), -1)
            boxes = detector.detect(frame)

        self.assertIsInstance(boxes, list)
        for x, y, w, h in boxes:
            self.assertGreaterEqual(x, 0)
            self.assertLessEqual(x + w, width)
            self.assertLessEqual(y + h, height)

    def test_nms_suppresses_overlapping_boxes(self):
        from apps.monitoring.services.detectors import _nms

        boxes = [(100, 100, 80, 160), (110, 105, 80, 160), (400, 100, 80, 160)]
        kept = _nms(boxes, [0.9, 0.8, 0.7], 0.4)
        self.assertLessEqual(len(kept), len(boxes))
        self.assertTrue(all(box in boxes for box in kept))
