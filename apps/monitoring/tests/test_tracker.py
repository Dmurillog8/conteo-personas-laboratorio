from django.test import SimpleTestCase

from apps.monitoring.services.tracker import CentroidTracker


class CentroidTrackerTests(SimpleTestCase):
    def test_requires_several_hits_to_confirm(self):
        tracker = CentroidTracker(min_hits=3)
        rect = (100, 100, 40, 100)

        tracker.update([rect], now=0.0)
        self.assertEqual(len(tracker.tracks), 1)
        self.assertFalse(next(iter(tracker.tracks.values())).confirmed)
        self.assertEqual(tracker.total_confirmed, 0)

        tracker.update([rect], now=0.1)
        tracker.update([rect], now=0.2)
        track = next(iter(tracker.tracks.values()))
        self.assertTrue(track.confirmed)
        self.assertEqual(tracker.total_confirmed, 1)

    def test_keeps_identifier_while_person_moves(self):
        tracker = CentroidTracker(min_hits=1, max_distance=120)
        for index in range(6):
            tracker.update([(100 + index * 8, 100, 40, 100)], now=index * 0.1)
        self.assertEqual(len(tracker.tracks), 1)
        self.assertEqual(len(tracker.tracks), len({track.id for track in tracker.tracks.values()}))

    def test_removes_track_after_disappearing(self):
        tracker = CentroidTracker(min_hits=1, max_disappeared=2)
        tracker.update([(100, 100, 40, 100)], now=0.0)
        tracker.update([], now=0.1)
        tracker.update([], now=0.2)
        self.assertEqual(len(tracker.tracks), 1)
        tracker.update([], now=0.3)
        self.assertEqual(len(tracker.tracks), 0)

    def test_unique_counter_is_not_duplicated(self):
        tracker = CentroidTracker(min_hits=2)
        boxes = [(100, 100, 40, 100), (400, 120, 40, 100)]
        for index in range(6):
            tracker.update(boxes, now=index * 0.1)
        self.assertEqual(tracker.total_confirmed, 2)
        self.assertEqual(len(tracker.active_tracks()), 2)

    def test_active_tracks_tolerates_small_gaps(self):
        tracker = CentroidTracker(min_hits=1, max_disappeared=10)
        tracker.update([(100, 100, 40, 100)], now=0.0)
        tracker.update([], now=0.1)
        self.assertEqual(len(tracker.active_tracks(max_missed=1)), 1)
        tracker.update([], now=0.2)
        tracker.update([], now=0.3)
        self.assertEqual(len(tracker.active_tracks(max_missed=1)), 0)
