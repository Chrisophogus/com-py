import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

FRAME_ROOT = "frames"
OUTPUT_ROOT = "outputs"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Detect shot boundaries and build per-shot palette outputs."
    )
    parser.add_argument(
        "--folder",
        default=None,
        help="Film folder name under frames/. If omitted, prompts for selection.",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.38,
        help="Bhattacharyya histogram distance threshold for hard cuts.",
    )
    parser.add_argument(
        "--min-shot-len",
        type=int,
        default=6,
        help="Minimum frames per shot; very short cuts are merged.",
    )
    parser.add_argument(
        "--hist-bins",
        type=int,
        default=8,
        help="Histogram bins per channel used for boundary detection.",
    )
    parser.add_argument(
        "--strip-width",
        type=int,
        default=3600,
        help="Output shot palette strip width.",
    )
    parser.add_argument(
        "--strip-height",
        type=int,
        default=280,
        help="Output shot palette strip height.",
    )
    return parser.parse_args()


def list_folders(base_path):
    return sorted(
        [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
    )


def select_folder(base_path):
    folders = list_folders(base_path)
    if not folders:
        raise FileNotFoundError(f"No folders found in {base_path}")

    print("Available films:")
    for i, folder in enumerate(folders, start=1):
        print(f"  {i}. {folder}")
    choice = input("Select folder number: ").strip()
    if not choice.isdigit():
        raise ValueError("Invalid folder selection.")
    idx = int(choice) - 1
    if idx < 0 or idx >= len(folders):
        raise ValueError("Invalid folder selection.")
    return folders[idx]


def frame_files_for_folder(frame_dir):
    files = sorted(
        [
            p
            for p in Path(frame_dir).iterdir()
            if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg", ".png"}
        ]
    )
    if not files:
        raise FileNotFoundError(f"No frame files found in {frame_dir}")
    return files


def calc_hist_bhattacharyya(image_bgr, bins):
    hist = cv2.calcHist([image_bgr], [0, 1, 2], None, [bins, bins, bins], [0, 256, 0, 256, 0, 256])
    cv2.normalize(hist, hist)
    return hist


def detect_shot_boundaries(frame_paths, threshold=0.38, min_shot_len=6, hist_bins=8):
    hists = []
    avg_cols = []
    for path in frame_paths:
        frame = cv2.imread(str(path))
        if frame is None:
            continue
        hists.append(calc_hist_bhattacharyya(frame, hist_bins))
        avg_cols.append(frame.mean(axis=(0, 1))[::-1])  # RGB

    if not hists:
        raise RuntimeError("No valid frames loaded for shot detection.")

    boundaries = [0]
    distances = [0.0]
    for i in range(1, len(hists)):
        d = cv2.compareHist(hists[i - 1], hists[i], cv2.HISTCMP_BHATTACHARYYA)
        distances.append(float(d))
        if d >= threshold:
            boundaries.append(i)
    if boundaries[-1] != len(hists):
        boundaries.append(len(hists))

    # Merge shots shorter than min_shot_len into previous shot.
    merged = [boundaries[0]]
    for b in boundaries[1:]:
        if b - merged[-1] < min_shot_len and len(merged) > 1:
            continue
        merged.append(b)
    if merged[-1] != len(hists):
        merged[-1] = len(hists)

    shots = []
    for i in range(len(merged) - 1):
        start_idx = merged[i]
        end_idx = merged[i + 1]
        cols = np.array(avg_cols[start_idx:end_idx], dtype=np.float32)
        rep_rgb = [int(x) for x in np.clip(cols.mean(axis=0), 0, 255)]
        shots.append(
            {
                "shot_index": i,
                "start_frame_index": start_idx,
                "end_frame_index_exclusive": end_idx,
                "frame_count": end_idx - start_idx,
                "representative_rgb": rep_rgb,
                "avg_transition_distance": float(np.mean(distances[start_idx:end_idx])) if end_idx > start_idx else 0.0,
            }
        )
    return shots


def save_shot_palette_strip(shots, output_path, width=3600, height=280):
    total_frames = sum(s["frame_count"] for s in shots)
    if total_frames <= 0:
        raise ValueError("No shot frame counts available to render strip.")

    img = np.zeros((height, width, 3), dtype=np.uint8)
    x = 0
    for i, shot in enumerate(shots):
        w = int(round((shot["frame_count"] / total_frames) * width))
        if i == len(shots) - 1:
            w = width - x
        w = max(1, w)
        color = np.array(shot["representative_rgb"], dtype=np.uint8)
        img[:, x : min(width, x + w), :] = color
        x += w
        if x >= width:
            break

    Image.fromarray(img).save(output_path, "PNG", optimize=False, compress_level=1)


def main():
    args = parse_args()
    folder = args.folder or select_folder(FRAME_ROOT)
    frame_dir = Path(FRAME_ROOT) / folder
    out_dir = Path(OUTPUT_ROOT) / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    frames = frame_files_for_folder(frame_dir)
    print(f"[>] Detecting shots for {folder} ({len(frames)} frames)")
    shots = detect_shot_boundaries(
        frames,
        threshold=args.threshold,
        min_shot_len=args.min_shot_len,
        hist_bins=args.hist_bins,
    )

    json_path = out_dir / "shot_palettes.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "film_folder": folder,
                "total_frames": len(frames),
                "shot_count": len(shots),
                "threshold": args.threshold,
                "min_shot_len": args.min_shot_len,
                "hist_bins": args.hist_bins,
                "shots": shots,
            },
            f,
            indent=2,
            ensure_ascii=True,
        )
    print(f"[✓] Saved shot metadata: {json_path}")

    strip_path = out_dir / "shot_palette_strip.png"
    save_shot_palette_strip(shots, strip_path, width=args.strip_width, height=args.strip_height)
    print(f"[✓] Saved shot palette strip: {strip_path}")


if __name__ == "__main__":
    main()
