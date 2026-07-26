import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from PIL import Image

import ozonelab_style as ozonelab


class OzonelabTests(unittest.TestCase):
    def test_binary_stream_and_dots(self):
        stream = ozonelab.build_stream(5, 2)
        self.assertEqual(stream, "00000011101|0000001010")
        dots = ozonelab.stream_to_dots(stream, x0=0, dx=2, y_top=1, y_bottom=3, gap_mult=2)
        self.assertEqual(len(dots), len(stream) - 1)
        with self.assertRaises(ValueError):
            ozonelab.build_stream(-1, 0)

    def test_release_date_validation(self):
        self.assertEqual(ozonelab.format_release_date("2026-07-19T12:00:00Z"), "19.07.2026")
        self.assertEqual(ozonelab.format_release_date("2026-99-99"), "")

    def test_tmdb_year_comes_from_release_date(self):
        metadata = ozonelab.build_metadata_from_tmdb(
            {"title": "Wrong Folder Year", "year": 1999, "imdb_id": "tt1234567"},
            {
                "id": 1,
                "title": "Film",
                "release_date": "2001-02-03",
                "release_dates": {"results": []},
                "external_ids": {"imdb_id": "tt1234567"},
                "genres": [],
            },
        )
        self.assertEqual(metadata["year"], 2001)

    def test_refresh_without_match_preserves_existing_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            metadata_path = root / "poster_metadata.json"
            metadata_path.write_text(
                json.dumps(
                    {
                        "films": {
                            "tt1234567": {
                                "title": "Existing",
                                "year": 2000,
                                "headline": "Keep me",
                                "summary": "Existing summary",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            args = SimpleNamespace(
                metadata=str(metadata_path),
                refresh_metadata=True,
                tmdb_log_file=None,
                tmdb_api_key=None,
                tmdb_read_token=None,
            )
            input_path = root / "Film (2000) - tt1234567" / "circle_full.png"

            with mock.patch.dict(os.environ, {"TMDB_API_KEY": "test-key"}), mock.patch(
                "ozonelab_style.fetch_tmdb_metadata", return_value=None
            ):
                metadata, _ = ozonelab.resolve_metadata(args, input_path)

        self.assertEqual(metadata["headline"], "Keep me")
        self.assertEqual(metadata["summary"], "Existing summary")

    def test_custom_output_paths_respect_theme(self):
        input_path = "outputs/Film/circle_full.png"
        self.assertEqual(
            ozonelab.output_paths(input_path, "custom.png", "dark"),
            [Path("custom.png")],
        )
        self.assertEqual(
            ozonelab.output_paths(input_path, "custom.png", "both"),
            [Path("custom_light.png"), Path("custom_dark.png")],
        )

    def test_dotstrip_render_writes_png(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "dots.png"
            ozonelab.render_dotstrip_png("10|01", output, dot_radius=2, dx=4, row_gap=5, gap_mult=2)
            with Image.open(output) as image:
                self.assertEqual(image.format, "PNG")
                self.assertGreater(image.width, 0)


if __name__ == "__main__":
    unittest.main()
