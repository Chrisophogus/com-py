import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

import colours_of_motion_circle as circle
import colours_of_motion_donut as donut
import colours_of_motion_radial as radial
import colours_of_motion_vertical as vertical


class RendererTests(unittest.TestCase):
    def test_radial_pipeline_uses_requested_dimensions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = root / "frames"
            frames.mkdir()
            Image.new("RGB", (3, 3), (255, 0, 0)).save(frames / "frame_0001.png")
            Image.new("RGB", (3, 3), (0, 255, 0)).save(frames / "frame_0002.png")
            timeline = root / "timeline.png"
            output = root / "radial.png"

            radial.build_horizontal_timeline(frames, timeline, line_height=3, stripe_width=2)
            radial.build_radial_image(timeline, output, resolution=12)

            with Image.open(timeline) as image:
                self.assertEqual(image.size, (4, 3))
            with Image.open(output) as image:
                self.assertEqual(image.size, (12, 12))

    def test_vertical_renders_cover_the_full_height(self):
        metadata = [
            {"color": [255, 0, 0], "brightness": 76.0},
            {"color": [0, 255, 0], "brightness": 149.0},
            {"color": [0, 0, 255], "brightness": 29.0},
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            classic = root / "classic.png"
            cinematic = root / "cinematic.png"

            vertical.build_vertical_classic(metadata, classic, target_width=8, target_height=7)
            vertical.build_vertical_cinematic(metadata, cinematic, target_width=12, target_height=7)

            with Image.open(classic) as image:
                self.assertEqual(image.size, (8, 7))
            with Image.open(cinematic) as image:
                self.assertEqual(image.size, (12, 7))
                self.assertTrue(any(sum(pixel) > 0 for pixel in list(image.getdata())[-12:]))

    def test_circle_renderer_validates_and_writes_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path = root / "data.json"
            metadata_path.write_text(
                json.dumps([{"color": [255, 0, 0]}, {"color": [0, 0, 255]}]),
                encoding="utf-8",
            )
            output = root / "circle.png"

            circle.build_circle_image(metadata_path, output, resolution=32, supersample=1)

            with Image.open(output) as image:
                self.assertEqual(image.size, (32, 32))
            with self.assertRaises(ValueError):
                circle.build_circle_image(metadata_path, output, resolution=0)

    def test_donut_strip_order_is_numeric(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("strip_10000.png", "strip_9999.png", "strip_10001.png", "other.png"):
                (root / name).touch()

            ordered = [Path(path).name for path in donut.list_strip_paths(root)]

        self.assertEqual(ordered, ["strip_9999.png", "strip_10000.png", "strip_10001.png"])

    def test_donut_renderer_writes_small_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            strips = root / "strips"
            strips.mkdir()
            for index, colour in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255)), start=1):
                Image.new("RGB", (1, 4), colour).save(strips / f"strip_{index:04d}.png")
            output = root / "donut.png"

            donut.build_donut_poster(strips, output, resolution=32)

            with Image.open(output) as image:
                self.assertEqual(image.size, (32, 32))


if __name__ == "__main__":
    unittest.main()
