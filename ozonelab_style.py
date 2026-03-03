import argparse
import json
import math
import os
import re
import urllib.parse
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


LIGHT_THEME = {
    "bg": (245, 243, 239),
    "fg": (24, 24, 24),
    "muted": (42, 42, 42),
    "frame_outer": (28, 28, 28),
    "frame_inner": (250, 250, 248),
}

DARK_THEME = {
    "bg": (25, 27, 31),
    "fg": (240, 240, 236),
    "muted": (210, 210, 206),
    "frame_outer": (236, 236, 232),
    "frame_inner": (25, 27, 31),
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build an Ozonelab-style poster from an existing circle_full.png."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to circle_full.png",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output PNG path. If omitted, writes *_ozonelab_light.png and/or *_ozonelab_dark.png",
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark", "both"],
        default="both",
        help="Poster theme variant to render.",
    )
    parser.add_argument("--width", type=int, default=3600, help="Poster width in pixels.")
    parser.add_argument("--height", type=int, default=5400, help="Poster height in pixels.")
    parser.add_argument(
        "--title",
        default=None,
        help="Override main poster headline.",
    )
    parser.add_argument(
        "--subtitle",
        default=None,
        help="Override supporting text below the title.",
    )
    parser.add_argument(
        "--metadata",
        default=None,
        help="Path to shared metadata catalog JSON (defaults to metadata/poster_metadata.json).",
    )
    parser.add_argument(
        "--refresh-metadata",
        action="store_true",
        help="Refresh metadata from TMDB and overwrite local metadata JSON.",
    )
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Only resolve/refresh metadata and skip poster rendering.",
    )
    parser.add_argument(
        "--tmdb-api-key",
        default=None,
        help="TMDB v3 API key (falls back to TMDB_API_KEY env var).",
    )
    parser.add_argument(
        "--tmdb-read-token",
        default=None,
        help="TMDB v4 read access token (falls back to TMDB_READ_ACCESS_TOKEN env var).",
    )
    parser.add_argument(
        "--tmdb-log-file",
        default=None,
        help="Path for TMDB request/response debug log (JSONL). Defaults to logs/tmdb_run_<timestamp>.jsonl",
    )
    return parser.parse_args()


LEGACY_ALIEN_HEADLINE = "IN SPACE NO ONE CAN HEAR YOU SCREAM"
LEGACY_ALIEN_SUMMARY = (
    "AFTER A SPACE MERCHANT VESSEL RECEIVES AN UNKNOWN TRANSMISSION AS A DISTRESS CALL, "
    "ONE OF THE CREW IS ATTACKED BY A MYSTERIOUS LIFE FORM AND THEY SOON REALIZE THAT "
    "ITS LIFE CYCLE HAS MERELY BEGUN."
)
DEFAULT_HEADLINE = "UNTITLED"
DEFAULT_SUMMARY = ""
SCHEMA_VERSION = 2


def load_dotenv(path=".env"):
    env_path = Path(path)
    if not env_path.exists():
        return
    with env_path.open("r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            if key and key not in os.environ:
                os.environ[key] = value


def parse_film_hint(input_path):
    folder = input_path.parent.name
    imdb_match = re.search(r"(tt\d{6,10})", folder)
    imdb_id = imdb_match.group(1) if imdb_match else None

    main_part = folder.split(" - ")[0].strip()
    year_match = re.search(r"\((\d{4})\)", main_part)
    year = int(year_match.group(1)) if year_match else None
    title = re.sub(r"\(\d{4}\)", "", main_part).strip() or main_part
    return {"folder": folder, "title": title, "year": year, "imdb_id": imdb_id}


def format_release_date(date_str):
    if not date_str:
        return ""
    # Accept both YYYY-MM-DD and full ISO timestamps from TMDB release_dates.
    core = date_str[:10]
    if len(core) != 10 or core[4] != "-" or core[7] != "-":
        return ""
    yyyy, mm, dd = core.split("-")
    return f"{dd}.{mm}.{yyyy}"


def tmdb_log(log_path, event, payload):
    if not log_path:
        return
    path = Path(log_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "payload": payload,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=True) + "\n")


def tmdb_get(path, params, api_key=None, read_token=None, log_path=None):
    params = dict(params)
    safe_params = dict(params)
    if api_key:
        params["api_key"] = api_key
    url = f"https://api.themoviedb.org/3{path}?{urllib.parse.urlencode(params)}"
    headers = {"accept": "application/json", "user-agent": "com-py/ozonelab-style"}
    if read_token:
        headers["Authorization"] = f"Bearer {read_token}"

    tmdb_log(
        log_path,
        "request",
        {
            "path": path,
            "params": safe_params,
            "url_no_secret": f"https://api.themoviedb.org/3{path}",
            "auth_mode": "bearer" if read_token else ("api_key" if api_key else "none"),
        },
    )
    try:
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            tmdb_log(
                log_path,
                "response",
                {
                    "path": path,
                    "status": getattr(response, "status", None),
                    "keys": sorted(list(data.keys())) if isinstance(data, dict) else None,
                    "body": data,
                },
            )
            return data
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            body = "<unreadable>"
        tmdb_log(
            log_path,
            "http_error",
            {
                "path": path,
                "params": safe_params,
                "status": exc.code,
                "reason": str(exc.reason),
                "body": body,
            },
        )
        raise
    except Exception as exc:
        tmdb_log(log_path, "error", {"path": path, "params": safe_params, "error": str(exc)})
        raise


def fetch_tmdb_metadata(hint, api_key=None, read_token=None, log_path=None):
    movie = None
    if hint.get("imdb_id"):
        found = tmdb_get(
            f"/find/{hint['imdb_id']}",
            {"external_source": "imdb_id", "language": "en-GB"},
            api_key=api_key,
            read_token=read_token,
            log_path=log_path,
        )
        candidates = found.get("movie_results", [])
        if candidates:
            movie = candidates[0]

    if movie is None and hint.get("title"):
        search_params = {"query": hint["title"], "language": "en-GB"}
        if hint.get("year"):
            search_params["year"] = hint["year"]
        found = tmdb_get(
            "/search/movie",
            search_params,
            api_key=api_key,
            read_token=read_token,
            log_path=log_path,
        )
        candidates = found.get("results", [])
        if candidates:
            movie = candidates[0]

    if not movie:
        return None

    details = tmdb_get(
        f"/movie/{movie['id']}",
        {"append_to_response": "external_ids,release_dates", "language": "en-GB"},
        api_key=api_key,
        read_token=read_token,
        log_path=log_path,
    )
    return details


def preferred_release_date(details):
    release_dates = (details.get("release_dates") or {}).get("results") or []

    def country_date(country_code):
        for block in release_dates:
            if block.get("iso_3166_1") != country_code:
                continue
            dates = []
            for item in block.get("release_dates") or []:
                raw = item.get("release_date")
                if raw:
                    dates.append(raw)
            if dates:
                return sorted(dates)[0]
        return None

    return (
        country_date("GB")
        or country_date("US")
        or details.get("release_date")
        or ""
    )


def build_metadata_from_tmdb(hint, details):
    release_date_raw = preferred_release_date(details)
    runtime = details.get("runtime")
    aspect_value = details.get("aspect_ratio")
    aspect = f"{float(aspect_value):.2f}:1" if isinstance(aspect_value, (int, float)) and aspect_value else "2.20:1"

    title = details.get("title") or hint.get("title") or "UNTITLED"
    tagline = details.get("tagline") or ""
    overview = details.get("overview") or ""
    headline = tagline or title or DEFAULT_HEADLINE
    summary = overview
    genres = details.get("genres") or []
    category = "DOCUMENTARY" if any((g.get("name") or "").lower() == "documentary" for g in genres) else "MOTION PICTURE"

    return {
        "source": "tmdb",
        "tmdb_id": details.get("id"),
        "imdb_id": (details.get("external_ids") or {}).get("imdb_id") or hint.get("imdb_id"),
        "title": title,
        "year": hint.get("year"),
        "schema_version": SCHEMA_VERSION,
        "release_date": release_date_raw,
        "runtime_min": runtime,
        "aspect_ratio": aspect,
        "production_category": category,
        "project_resolution": "FILM PROJECT",
        "color_profile": "COLOUR",
        "tagline": tagline,
        "overview": overview,
        "headline": headline,
        "summary": summary,
    }


def build_fallback_metadata(hint):
    fallback_title = hint.get("title") or "UNTITLED"
    return {
        "source": "local",
        "tmdb_id": None,
        "imdb_id": hint.get("imdb_id"),
        "title": fallback_title,
        "year": hint.get("year"),
        "schema_version": SCHEMA_VERSION,
        "release_date": None,
        "runtime_min": None,
        "aspect_ratio": "2.20:1",
        "production_category": "MOTION PICTURE",
        "project_resolution": "FILM PROJECT",
        "color_profile": "COLOUR",
        "tagline": "",
        "overview": "",
        "headline": fallback_title.upper(),
        "summary": "",
    }


def normalize_metadata_entry(entry, hint):
    metadata = dict(entry or {})
    title = metadata.get("title") or hint.get("title") or "UNTITLED"
    tagline = metadata.get("tagline")
    overview = metadata.get("overview")
    headline = metadata.get("headline")
    summary = metadata.get("summary")

    if tagline is None:
        tagline = ""
    if overview is None:
        overview = ""
    if headline is None or str(headline).strip() == "":
        headline = tagline or title or DEFAULT_HEADLINE
    if summary is None:
        summary = overview

    metadata.setdefault("source", "local")
    metadata.setdefault("tmdb_id", None)
    metadata.setdefault("imdb_id", hint.get("imdb_id"))
    metadata["title"] = title
    metadata.setdefault("year", hint.get("year"))
    metadata.setdefault("release_date", None)
    metadata.setdefault("runtime_min", None)
    metadata.setdefault("aspect_ratio", "2.20:1")
    metadata.setdefault("production_category", "MOTION PICTURE")
    metadata.setdefault("project_resolution", "FILM PROJECT")
    metadata.setdefault("color_profile", "COLOUR")
    metadata["tagline"] = tagline
    metadata["overview"] = overview
    metadata["headline"] = headline
    metadata["summary"] = summary
    metadata["schema_version"] = SCHEMA_VERSION
    return metadata


def generate_meta_row(metadata):
    category = str(metadata.get("production_category") or "MOTION PICTURE").upper()
    project_resolution = str(metadata.get("project_resolution") or "FILM PROJECT").upper()
    color_profile = str(metadata.get("color_profile") or "COLOUR").upper()
    aspect_ratio = str(metadata.get("aspect_ratio") or "2.20:1")

    runtime = metadata.get("runtime_min")
    if isinstance(runtime, (int, float)) and runtime > 0:
        runtime_text = f"{int(round(runtime))}MIN"
    else:
        runtime_text = "N/A"

    release_date = format_release_date(str(metadata.get("release_date") or ""))
    if not release_date:
        year = metadata.get("year")
        release_date = f"01.01.{year}" if year else "N/A"

    return [
        category,
        project_resolution,
        color_profile,
        aspect_ratio,
        runtime_text,
        release_date,
    ]


def sanitize_mixed_legacy_copy(metadata_entry, film_key):
    imdb_id = metadata_entry.get("imdb_id") or film_key
    if imdb_id == "tt0078748":
        return metadata_entry

    changed = False
    title = metadata_entry.get("title") or "UNTITLED"
    if metadata_entry.get("headline", "").strip().upper() == LEGACY_ALIEN_HEADLINE.upper():
        metadata_entry["headline"] = title.upper()
        changed = True
    if metadata_entry.get("summary", "").strip().upper() == LEGACY_ALIEN_SUMMARY.upper():
        metadata_entry["summary"] = ""
        changed = True
    if changed:
        metadata_entry["source"] = metadata_entry.get("source", "local")
    return metadata_entry


def resolve_metadata(args, input_path):
    hint = parse_film_hint(input_path)
    metadata_path = Path(args.metadata) if args.metadata else Path("metadata") / "poster_metadata.json"
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    film_key = hint.get("imdb_id") or hint.get("folder") or hint.get("title") or "unknown"
    catalog = {"films": {}}
    if metadata_path.exists():
        with metadata_path.open("r", encoding="utf-8") as f:
            raw = f.read()
        loaded = None
        try:
            loaded = json.loads(raw)
        except json.JSONDecodeError:
            # Salvage first valid JSON object if file has trailing junk from manual edits.
            try:
                loaded, _ = json.JSONDecoder().raw_decode(raw)
                print(f"[!] Metadata file had trailing invalid data; recovered first JSON object: {metadata_path}")
            except Exception:
                loaded = None
        if isinstance(loaded, dict) and "films" in loaded and isinstance(loaded["films"], dict):
            catalog = loaded
        elif isinstance(loaded, dict):
            # Backward compatibility with old single-film metadata files.
            catalog = {"films": {film_key: loaded}}

    # Migrate all stored entries to explicit schema fields.
    films = catalog.get("films", {})
    for key, entry in list(films.items()):
        hint_for_entry = {
            "title": entry.get("title"),
            "year": entry.get("year"),
            "imdb_id": entry.get("imdb_id") or key,
            "folder": key,
        }
        films[key] = normalize_metadata_entry(entry, hint_for_entry)

    existing = catalog.get("films", {}).get(film_key)

    if not args.refresh_metadata and existing is not None:
        existing = sanitize_mixed_legacy_copy(existing, film_key)
        existing = normalize_metadata_entry(existing, hint)
        catalog["films"][film_key] = existing
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(catalog, f, indent=2, ensure_ascii=True)
        return existing, metadata_path

    metadata = None
    tmdb_log_path = args.tmdb_log_file
    api_key = args.tmdb_api_key or os.getenv("TMDB_API_KEY")
    read_token = args.tmdb_read_token or os.getenv("TMDB_READ_ACCESS_TOKEN")
    if api_key or read_token:
        try:
            details = fetch_tmdb_metadata(
                hint,
                api_key=api_key,
                read_token=read_token,
                log_path=tmdb_log_path,
            )
            if details:
                metadata = build_metadata_from_tmdb(hint, details)
        except Exception as exc:
            if existing is not None:
                print(f"[!] TMDB lookup failed, keeping existing metadata for {film_key}: {exc}")
                metadata = normalize_metadata_entry(existing, hint)
            else:
                print(f"[!] TMDB lookup failed, using local fallback metadata: {exc}")
    else:
        tmdb_log(
            tmdb_log_path,
            "skipped",
            {"reason": "missing_tmdb_credentials", "film_key": film_key},
        )
        if existing is not None:
            metadata = normalize_metadata_entry(existing, hint)

    if metadata is None:
        metadata = build_fallback_metadata(hint)
    metadata = normalize_metadata_entry(metadata, hint)

    catalog.setdefault("films", {})
    catalog["films"][film_key] = metadata
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=2, ensure_ascii=True)
    print(f"[✓] Metadata cached at: {metadata_path} (film key: {film_key})")
    return metadata, metadata_path


def get_font(size, bold=False):
    # Prefer condensed/impact-like fonts for closer poster typography.
    candidates = []
    if bold:
        candidates = [
            "/System/Library/Fonts/Supplemental/Impact.ttf",
            "/System/Library/Fonts/Supplemental/Arial Narrow Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Library/Fonts/Arial Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf",
        ]
    else:
        candidates = [
            "/System/Library/Fonts/Supplemental/Arial Narrow.ttf",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
        ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size=size)
    return ImageFont.load_default()


def fit_text(draw, text, max_width, initial_size, bold=True):
    size = initial_size
    while size > 12:
        font = get_font(size=size, bold=bold)
        width = draw.textbbox((0, 0), text, font=font)[2]
        if width <= max_width:
            return font
        size -= 2
    return get_font(size=12, bold=bold)


def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = []
    for word in words:
        test_line = " ".join(current + [word])
        test_width = draw.textbbox((0, 0), test_line, font=font)[2]
        if test_width <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines


def ring_from_circle(circle_img, diameter):
    src = circle_img.convert("RGB").resize((diameter, diameter), Image.LANCZOS)
    src_rgba = src.convert("RGBA")

    mask = Image.new("L", (diameter, diameter), 0)
    draw_mask = ImageDraw.Draw(mask)
    center = diameter // 2
    outer = diameter // 2 - 1
    inner = int(outer * 0.25)
    draw_mask.ellipse(
        (center - outer, center - outer, center + outer, center + outer),
        fill=255,
    )
    draw_mask.ellipse(
        (center - inner, center - inner, center + inner, center + inner),
        fill=0,
    )
    src_rgba.putalpha(mask)
    return src_rgba


def sample_ring_strip(circle_img, width, height):
    arr = np.array(circle_img.convert("RGB"))
    h, w, _ = arr.shape
    cx = (w - 1) / 2.0
    cy = (h - 1) / 2.0
    outer = min(cx, cy) * 0.98
    inner = outer * 0.25
    r0 = inner + (outer - inner) * 0.55

    samples = np.zeros((width, 3), dtype=np.float32)
    for x in range(width):
        angle = (x / width) * (2 * math.pi)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        # Average a small radial span for smoother strip colors.
        acc = np.zeros(3, dtype=np.float32)
        for t in (0.42, 0.50, 0.58):
            r = inner + (outer - inner) * t
            px = int(np.clip(round(cx + r * cos_a), 0, w - 1))
            py = int(np.clip(round(cy + r * sin_a), 0, h - 1))
            acc += arr[py, px]
        samples[x] = acc / 3.0

    strip_row = np.clip(samples, 0, 255).astype(np.uint8)[None, :, :]
    strip = np.repeat(strip_row, height, axis=0)
    return Image.fromarray(strip)


def add_paper_grain(img):
    w, h = img.size
    noise = np.random.normal(loc=0, scale=8, size=(h, w, 1)).astype(np.int16)
    base = np.array(img).astype(np.int16)
    mixed = np.clip(base + noise, 0, 255).astype(np.uint8)
    grain = Image.fromarray(mixed).filter(ImageFilter.GaussianBlur(radius=0.35))
    return grain


def draw_poster(circle_img, output_path, palette, title, subtitle, meta_row, width, height):
    img = Image.new("RGB", (width, height), palette["bg"])
    draw = ImageDraw.Draw(img)

    # Outer frame + inner border.
    frame = int(width * 0.03)
    border = max(6, int(width * 0.004))
    draw.rectangle((0, 0, width - 1, height - 1), fill=palette["frame_outer"])
    draw.rectangle(
        (frame, frame, width - frame, height - frame),
        fill=palette["frame_inner"],
        outline=palette["fg"],
        width=border,
    )

    left = frame + int(width * 0.08)
    right = width - frame - int(width * 0.08)
    inner_top = frame + int(height * 0.08)
    inner_bottom = height - frame - int(height * 0.07)
    content_w = right - left

    # Top metadata row.
    meta_y = inner_top
    meta = meta_row
    meta_font = get_font(int(width * 0.017), bold=False)
    for i, item in enumerate(meta):
        x = left + int((content_w / (len(meta) - 1)) * i)
        bb = draw.textbbox((0, 0), item, font=meta_font)
        draw.text((x - (bb[2] - bb[0]) / 2, meta_y), item, fill=palette["muted"], font=meta_font)

    # Circle placement.
    circle_d = int(width * 0.65)
    ring = ring_from_circle(circle_img, circle_d)
    cx = width // 2 - circle_d // 2
    cy = inner_top + int(height * 0.07)
    img.paste(ring, (cx, cy), ring)

    # Title block.
    title_y = cy + circle_d + int(height * 0.015)
    title_font = fit_text(draw, title.upper(), content_w, initial_size=int(width * 0.09), bold=True)
    title_text = title.upper()
    tb = draw.textbbox((0, 0), title_text, font=title_font)

    # Bottom color strip derived from circle colors.
    strip_h = int(height * 0.03)
    strip_y = inner_bottom - strip_h
    strip = sample_ring_strip(circle_img, content_w, strip_h)
    img.paste(strip, (left, strip_y))

    # Bottom dots row is explicitly anchored above the strip.
    dots_y = strip_y - int(height * 0.055)

    subtitle_top_gap = int(height * 0.014)
    subtitle_bottom_limit = dots_y - int(height * 0.030)
    title_h = tb[3] - tb[1]
    min_subtitle_h = int(height * 0.055)
    max_title_y = subtitle_bottom_limit - min_subtitle_h - subtitle_top_gap - title_h
    title_y = min(title_y, max_title_y)
    draw.text((width / 2 - (tb[2] - tb[0]) / 2, title_y), title_text, fill=palette["fg"], font=title_font)

    sub_y = title_y + title_h + subtitle_top_gap
    available_h = subtitle_bottom_limit - sub_y
    chosen_font = None
    chosen_lines = []
    chosen_line_h = 0
    preferred_font = int(width * 0.028)
    min_font = int(width * 0.016)
    subtitle_text = subtitle.upper()

    for size in range(preferred_font, min_font - 1, -1):
        candidate_font = get_font(size, bold=False)
        wrapped = wrap_text(draw, subtitle_text, candidate_font, content_w)
        line_h = draw.textbbox((0, 0), "A", font=candidate_font)[3] + int(height * 0.004)
        if available_h <= 0:
            break
        max_lines = int(available_h // line_h)
        if max_lines < 1:
            continue
        lines = wrapped[:max_lines]
        chosen_font = candidate_font
        chosen_lines = lines
        chosen_line_h = line_h
        if max_lines >= 2:
            break

    # Fallback: force a single line at minimum size if layout is very tight.
    if not chosen_lines and available_h > 0:
        chosen_font = get_font(min_font, bold=False)
        wrapped = wrap_text(draw, subtitle_text, chosen_font, content_w)
        if wrapped:
            chosen_lines = [wrapped[0]]
            chosen_line_h = draw.textbbox((0, 0), "A", font=chosen_font)[3] + int(height * 0.004)

    for line in chosen_lines:
        if sub_y + chosen_line_h > subtitle_bottom_limit:
            break
        sb = draw.textbbox((0, 0), line, font=chosen_font)
        draw.text((width / 2 - (sb[2] - sb[0]) / 2, sub_y), line, fill=palette["muted"], font=chosen_font)
        sub_y += chosen_line_h

    # Dot-code style decoration.
    dots_x = width // 2 - int(width * 0.085)
    dot_y = dots_y
    for i in range(18):
        r = int(width * 0.003) if i % 3 else int(width * 0.004)
        dx = dots_x + i * int(width * 0.012)
        dy = dot_y + (0 if i % 2 else int(height * 0.006))
        draw.ellipse((dx, dy, dx + r * 2, dy + r * 2), fill=palette["fg"])

    # Subtle paper grain for print-like finish.
    img = add_paper_grain(img)
    img.save(output_path, "PNG", optimize=False, compress_level=1)
    print(f"[✓] Saved poster: {output_path}")


def output_paths(input_path, output_path, theme):
    in_path = Path(input_path)
    base = in_path.with_suffix("")
    if output_path:
        return [Path(output_path)]
    if theme == "light":
        return [base.with_name(base.name + "_ozonelab_light.png")]
    if theme == "dark":
        return [base.with_name(base.name + "_ozonelab_dark.png")]
    return [
        base.with_name(base.name + "_ozonelab_light.png"),
        base.with_name(base.name + "_ozonelab_dark.png"),
    ]


def main():
    args = parse_args()
    load_dotenv()
    if not args.tmdb_log_file:
        run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.tmdb_log_file = str(Path("logs") / f"tmdb_run_{run_stamp}.jsonl")
    input_path = Path(args.input)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    metadata, metadata_path = resolve_metadata(args, input_path)
    if args.metadata_only:
        print(f"[✓] Metadata-only run complete: {metadata_path}")
        return

    circle = Image.open(input_path).convert("RGB")
    headline = (args.title or metadata.get("headline") or metadata.get("title") or DEFAULT_HEADLINE).upper()
    summary = args.subtitle or metadata.get("summary") or DEFAULT_SUMMARY
    meta_row = generate_meta_row(metadata)

    targets = output_paths(args.input, args.output, args.theme)
    for target in targets:
        target.parent.mkdir(parents=True, exist_ok=True)
        if "dark" in target.name.lower():
            palette = DARK_THEME
        elif "light" in target.name.lower():
            palette = LIGHT_THEME
        else:
            palette = LIGHT_THEME if args.theme != "dark" else DARK_THEME
        draw_poster(
            circle_img=circle,
            output_path=target,
            palette=palette,
            title=headline,
            subtitle=summary,
            meta_row=meta_row,
            width=args.width,
            height=args.height,
        )


if __name__ == "__main__":
    main()
