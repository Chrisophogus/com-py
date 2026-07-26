import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image

import colours_of_motion_shots as shots


class ShotTests(unittest.TestCase):
    def test_short_first_shot_merges_forward(self):
        self.assertEqual(shots.merge_short_boundaries([0, 2, 10], 10, 6), [0, 10])

    def test_short_middle_and_final_shots_merge(self):
        self.assertEqual(shots.merge_short_boundaries([0, 10, 12, 30], 30, 6), [0, 12, 30])
        self.assertEqual(shots.merge_short_boundaries([0, 10, 12], 12, 6), [0, 12])

    def test_detection_fails_on_unreadable_frame(self):
        with mock.patch("colours_of_motion_shots.cv2.imread", return_value=None):
            with self.assertRaisesRegex(ValueError, "Could not read frame"):
                shots.detect_shot_boundaries([Path("missing.png")])

    def test_detection_finds_synthetic_cut(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for index, colour in enumerate([(255, 0, 0)] * 4 + [(0, 0, 255)] * 4):
                path = root / f"frame_{index:04d}.png"
                Image.new("RGB", (8, 8), colour).save(path)
                paths.append(path)

            result = shots.detect_shot_boundaries(paths, threshold=0.1, min_shot_len=2, hist_bins=4)

        self.assertEqual([shot["frame_count"] for shot in result], [4, 4])

    def test_palette_strip_validates_width(self):
        palette = [
            {"frame_count": 1, "representative_rgb": [255, 0, 0]},
            {"frame_count": 1, "representative_rgb": [0, 0, 255]},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "palette.png"
            shots.save_shot_palette_strip(palette, output, width=4, height=2)
            with Image.open(output) as image:
                self.assertEqual(image.size, (4, 2))
            with self.assertRaises(ValueError):
                shots.save_shot_palette_strip(palette, output, width=1, height=2)


if __name__ == "__main__":
    unittest.main()
