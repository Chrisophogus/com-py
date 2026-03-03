# Colours of Motion + Ozonelab Poster Pipeline

This project builds film colour visualisations from extracted frames, then composes print-style posters using a circular colour fingerprint plus TMDB-enriched metadata.

## What It Produces

For each film folder, the pipeline can generate:

- `vertical_classic.png`
- `vertical_cinematic.png`
- `linear_hq.png`
- `radial_hq.png`
- `circle_full.png`
- `circle_donut_poster.png` (only if `circle_data/<film>/strip_*.png` exists)
- `circle_full_ozonelab_light.png`
- `circle_full_ozonelab_dark.png`
- `dotstrip_light.png`
- `dotstrip_dark.png`

## Current Scripts

- `colours_of_motion_processing.py`
  - interactive source processing (frame extraction + metadata / strip extraction)
- `colours_of_motion_radial.py`
  - builds `linear_hq.png` and `radial_hq.png`
- `colours_of_motion_vertical.py`
  - builds `vertical_classic.png` and `vertical_cinematic.png`
- `colours_of_motion_circle.py`
  - builds `circle_full.png` from `frames/<film>/data.json`
- `colours_of_motion_donut.py`
  - builds `circle_donut_poster.png` from `circle_data/<film>/strip_*.png`
- `ozonelab_style.py`
  - builds final light/dark posters with TMDB-backed metadata and encoded dot strips

## Project Layout

```text
com-py/
├── frames/<film>/                # frame_*.jpg + data.json
├── circle_data/<film>/           # strip_*.png for donut generation
├── outputs/<film>/               # all rendered assets
├── metadata/poster_metadata.json # shared metadata catalog for all films
├── logs/tmdb_run_*.jsonl         # per-run TMDB request/response logs
├── .env                          # local secrets (ignored)
└── *.py                          # generation scripts
```

## Setup

### 1) Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pillow numpy opencv-python
```

Install `ffmpeg` (required for extraction scripts):

```bash
brew install ffmpeg
```

### 2) Environment Variables

Create `.env`:

```env
TMDB_API_KEY=
TMDB_READ_ACCESS_TOKEN=your_tmdb_read_access_token
```

Either `TMDB_API_KEY` (v3 key) or `TMDB_READ_ACCESS_TOKEN` (v4 bearer token) is supported.

## Typical Workflow

### A) Generate base visual assets

Run the generation scripts (interactive):

```bash
.venv/bin/python colours_of_motion_processing.py
.venv/bin/python colours_of_motion_vertical.py --poster_mode
.venv/bin/python colours_of_motion_radial.py --poster_mode
.venv/bin/python colours_of_motion_circle.py --poster_mode
.venv/bin/python colours_of_motion_donut.py --poster_mode
```

### B) Refresh shared metadata only (no image rendering)

```bash
.venv/bin/python ozonelab_style.py --input "outputs/Aliens (1986) - tt0090605/circle_full.png" --refresh-metadata --metadata-only
```

### C) Render final Ozonelab posters

```bash
.venv/bin/python ozonelab_style.py --input "outputs/Aliens (1986) - tt0090605/circle_full.png" --theme both
```

## Ozonelab Metadata Model

Stored in `metadata/poster_metadata.json` as a shared catalog:

```json
{
  "films": {
    "tt0090605": {
      "source": "tmdb|local",
      "schema_version": 2,
      "tmdb_id": 679,
      "imdb_id": "tt0090605",
      "title": "Aliens",
      "year": 1986,
      "release_date": "1986-08-29T00:00:00.000Z",
      "runtime_min": 137,
      "aspect_ratio": "2.20:1",
      "production_category": "MOTION PICTURE",
      "project_resolution": "FILM PROJECT",
      "color_profile": "COLOUR",
      "tagline": "This time it's war.",
      "overview": "....",
      "headline": "This time it's war.",
      "summary": "...."
    }
  }
}
```

Notes:

- `tagline` and `overview` are explicit TMDB fields.
- `headline` and `summary` are the render fields used in posters.
- Release date is formatted UK-style in output (`DD.MM.YYYY`).
- Refresh failures preserve existing metadata (no destructive fallback overwrite).

## Dot Numbering Strip (Encoded Binary)

`ozonelab_style.py` replaces the previous decorative dots with an encoded two-row dot strip:

- `A = frames_processed` (actual frames used)
- `B = runtime_seconds` (`runtime_min * 60`, or `0` if runtime missing)

Bit rendering:

- `1` -> top row dot
- `0` -> bottom row dot
- MSB -> LSB, left to right
- stream format:
  - `[lenA:8][A bits] | [lenB:8][B bits]`
  - `|` is a wider horizontal gap

Theme assets:

- `dotstrip_light.png` (black dots on transparent)
- `dotstrip_dark.png` (white dots on transparent)

## TMDB Logging

Every run writes a per-run log:

- `logs/tmdb_run_<timestamp>.jsonl`

Log entries include:

- request path + params (sanitized)
- auth mode (`api_key` or `bearer`)
- full response payload on success
- structured HTTP / network errors

## Troubleshooting

- `nodename nor servname provided, or not known`
  - DNS/network resolution issue to `api.themoviedb.org`, not a rate-limit error.
- Missing runtime/release/tagline/summary in metadata
  - run `--refresh-metadata --metadata-only` in a terminal with internet access.

## Example Outputs

### Aliens (1986) poster variants

- Light:
  ![Aliens light](outputs/Aliens%20(1986)%20-%20tt0090605/circle_full_ozonelab_light.png)
- Dark:
  ![Aliens dark](outputs/Aliens%20(1986)%20-%20tt0090605/circle_full_ozonelab_dark.png)

### Base visual assets (Aliens)

- ![Linear](outputs/Aliens%20(1986)%20-%20tt0090605/linear_hq.png)
- ![Radial](outputs/Aliens%20(1986)%20-%20tt0090605/radial_hq.png)
- ![Circle Full](outputs/Aliens%20(1986)%20-%20tt0090605/circle_full.png)
- ![Vertical Cinematic](outputs/Aliens%20(1986)%20-%20tt0090605/vertical_cinematic.png)

## Attribution

Concept inspired by [The Colours of Motion](https://thecolorsofmotion.com/).
Poster style reference inspired by [TheOzoneLab](https://www.etsy.com/shop/theozonelab/).
