import os
import subprocess
import json
import argparse
import numpy as np
import cv2

# === CONFIGURATION ===
FPS = 0.1
PROCESSED_FILE = "processed_files.json"
FRAME_ROOT = "frames"
OUTPUT_ROOT = "outputs"

# Poster mode defaults
POSTER_RESOLUTION = 5000  # High-quality radial
QUICK_RESOLUTION = 3000   # Fast preview
QUICK_LINE_HEIGHT = 120
HQ_LINE_HEIGHT = 600
QUICK_STRIPE_WIDTH = 2
HQ_STRIPE_WIDTH = 4

# === FRAME EXTRACTION ===
def extract_frames(video_path, frame_dir, fps=FPS):
    """Extracts HDR frames with tone mapping using ffmpeg."""
    os.makedirs(frame_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-an", "-sn", "-i", video_path,
        "-vf", (
            f"fps={fps},"
            "zscale=t=linear:npl=100,"
            "format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=hable,"
            "zscale=t=bt709,"
            "format=yuv420p"
        ),
        "-q:v", "1", "-vsync", "0", "-frame_pts", "1", "-fps_mode", "vfr",
        "-loglevel", "warning", "-hide_banner", "-stats",
        os.path.join(frame_dir, "frame_%04d.jpg")
    ]
    print(f"[>] Extracting frames with tone mapping:\n{' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[✓] HDR tone-mapped frame extraction complete.")

def build_horizontal_timeline(frame_dir, output_path, line_height=HQ_LINE_HEIGHT, stripe_width=HQ_STRIPE_WIDTH):
    """Build a horizontal average-colour timeline from extracted frames."""
    frame_files = sorted(
        f for f in os.listdir(frame_dir)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not frame_files:
        raise ValueError("No frame images found to build horizontal timeline.")

    colours = []
    for file in frame_files:
        path = os.path.join(frame_dir, file)
        frame = cv2.imread(path)
        if frame is None:
            continue
        # cv2 uses BGR; keep BGR throughout to avoid channel swapping later.
        avg_bgr = frame.mean(axis=(0, 1))
        colours.append(avg_bgr.astype(np.uint8))

    if not colours:
        raise ValueError("No valid frame images found to build horizontal timeline.")

    width = max(1, len(colours) * stripe_width)
    timeline = np.zeros((line_height, width, 3), dtype=np.uint8)
    for i, colour in enumerate(colours):
        start_x = i * stripe_width
        end_x = start_x + stripe_width
        timeline[:, start_x:end_x] = colour

    cv2.imwrite(output_path, timeline)
    print(f"[✓] Saved horizontal timeline: {output_path}")

# === RADIAL IMAGE BUILDER ===
def build_radial_image(image_path, output_path, resolution=3000):
    print("[>] Building radial image...")
    src = cv2.imread(image_path)
    if src is None:
        raise ValueError(f"Could not read image: {image_path}")

    # Sample slightly in from both ends to avoid first/last-frame edge artifacts.
    sample_start = 0.005
    sample_end = 0.995
    src_mid_y = src.shape[0] // 2

    y_grid, x_grid = np.indices((resolution, resolution), dtype=np.float32)
    max_dist = np.hypot(resolution - 1, resolution - 1)
    norm_dist = np.sqrt(x_grid * x_grid + y_grid * y_grid) / max_dist
    norm_dist = np.clip(norm_dist, 0.0, 1.0)
    norm_dist = sample_start + (sample_end - sample_start) * norm_dist

    src_x = np.clip((norm_dist * (src.shape[1] - 1)).astype(np.int32), 0, src.shape[1] - 1)
    result = src[src_mid_y, src_x]

    cv2.imwrite(output_path, result)
    print(f"[✓] Saved radial image: {output_path}")

# === TRACKING PROCESSED FILES ===
def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_processed(data):
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# === MAIN ===
def parse_args():
    parser = argparse.ArgumentParser(description="Generate radial Colours of Motion output.")
    parser.add_argument(
        "--poster_mode",
        action="store_true",
        help="Use high-resolution output without interactive prompt.",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    processed = load_processed()
    last_video = None
    last_folder = None
    if processed:
        if "last_video" in processed:
            last_video = processed["last_video"].get("path")
            last_folder = processed["last_video"].get("folder")
        else:
            last_video, last_folder = list(processed.items())[-1]
        reuse = input(f"Reuse last video? ({last_video}) [y/n]: ").strip().lower()
    else:
        reuse = "n"

    if reuse == "y" and last_video and last_folder:
        video_path = last_video
        folder_name = last_folder
    else:
        video_path = input("Enter full path to video file: ").strip()
        if not os.path.exists(video_path):
            print("[✗] Video not found.")
            return
        folder_name = input("Enter folder name (e.g. 'Aliens (1986) - tt0090605'): ").strip()

    frame_dir = os.path.join(FRAME_ROOT, folder_name)
    output_dir = os.path.join(OUTPUT_ROOT, folder_name)
    os.makedirs(output_dir, exist_ok=True)

    if args.poster_mode:
        poster_mode = True
    else:
        poster_mode = input("Run in poster mode? (y/n): ").strip().lower() == "y"
    resolution = POSTER_RESOLUTION if poster_mode else QUICK_RESOLUTION
    line_height = HQ_LINE_HEIGHT if poster_mode else QUICK_LINE_HEIGHT
    stripe_width = HQ_STRIPE_WIDTH if poster_mode else QUICK_STRIPE_WIDTH

    already_processed = False
    if processed.get(video_path) == folder_name:
        already_processed = True
    elif processed.get("last_video", {}).get("path") == video_path and processed.get("last_video", {}).get("folder") == folder_name:
        already_processed = True
    if already_processed:
        print("[!] Video previously processed – skipping frame extraction.")
    else:
        extract_frames(video_path, frame_dir, FPS)
        processed[video_path] = folder_name
        processed["last_video"] = {"path": video_path, "folder": folder_name}
        save_processed(processed)

    # Use existing horizontal timeline or build one from extracted frames.
    horizontal_path = os.path.join(output_dir, "linear_hq.png")
    if not os.path.exists(horizontal_path):
        print("[!] No horizontal timeline found. Building linear_hq.png from frame averages.")
        try:
            build_horizontal_timeline(frame_dir, horizontal_path, line_height, stripe_width)
        except ValueError as e:
            print(f"[✗] {e}")
            return

    radial_out = os.path.join(output_dir, "radial_hq.png")
    build_radial_image(horizontal_path, radial_out, resolution)

if __name__ == "__main__":
    main()
