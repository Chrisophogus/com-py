import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

import colours_of_motion_processing as processing
import colours_of_motion_processing_experimental as experimental


class ProcessingTests(unittest.TestCase):
    def test_calculate_frame_data(self):
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "frame_0001.png"
            Image.new("RGB", (2, 2), (10, 20, 30)).save(image_path)

            result = processing.calculate_frame_data(image_path)

        self.assertEqual(result["frame"], "frame_0001.png")
        self.assertEqual(result["color"], [10, 20, 30])
        self.assertAlmostEqual(result["brightness"], 18.15, places=2)
        self.assertAlmostEqual(result["saturation"], 2 / 3, places=5)

    def test_source_match_requires_path_and_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            video_path = Path(directory) / "movie.mkv"
            processed = {"last_video": {"path": str(video_path), "folder": "Film"}}

            for module in (processing, experimental):
                self.assertTrue(module.source_matches_last_video(processed, str(video_path), "Film"))
                self.assertFalse(module.source_matches_last_video(processed, str(video_path), "Other"))
                self.assertFalse(module.source_matches_last_video(processed, str(video_path) + ".new", "Film"))

    def test_folder_name_validation_rejects_paths(self):
        for module in (processing, experimental):
            self.assertTrue(module.valid_folder_name("Film (2026)"))
            self.assertFalse(module.valid_folder_name(""))
            self.assertFalse(module.valid_folder_name("../Film"))
            self.assertFalse(module.valid_folder_name("."))

    def test_numbered_output_detection_requires_contiguous_sequence(self):
        with tempfile.TemporaryDirectory() as directory:
            output_dir = Path(directory)
            (output_dir / "notes.txt").write_text("incomplete", encoding="utf-8")
            self.assertFalse(processing.has_contiguous_numbered_outputs(output_dir, "strip_", (".png",)))

            (output_dir / "strip_final.png").touch()
            self.assertFalse(processing.has_contiguous_numbered_outputs(output_dir, "strip_", (".png",)))

            (output_dir / "strip_0001.png").touch()
            (output_dir / "strip_0003.png").touch()
            self.assertFalse(processing.has_contiguous_numbered_outputs(output_dir, "strip_", (".png",)))

            (output_dir / "strip_0002.png").touch()
            for module in (processing, experimental):
                self.assertTrue(module.has_contiguous_numbered_outputs(output_dir, "strip_", (".png",)))

    def test_staged_extraction_only_publishes_complete_outputs(self):
        for module in (processing, experimental):
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                output_dir = Path(directory) / "frames"
                output_dir.mkdir()

                def create_outputs(command, check):
                    staging_dir = Path(command[1])
                    (staging_dir / "frame_0001.jpg").touch()
                    (staging_dir / "frame_0002.jpg").touch()

                with patch.object(module.subprocess, "run", side_effect=create_outputs):
                    module.extract_to_new_directory(
                        output_dir,
                        "frame_",
                        module.IMAGE_SUFFIXES,
                        lambda staging_dir: ["fake-ffmpeg", staging_dir],
                    )

                self.assertEqual(
                    [path.name for path in output_dir.iterdir()],
                    ["frame_0001.jpg", "frame_0002.jpg"],
                )


if __name__ == "__main__":
    unittest.main()
