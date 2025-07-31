import os
import subprocess
import json
from PIL import Image
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

# === RADIAL IMAGE BUILDER ===
def build_radial_image(image_path, output_path, resolution=3000):
    print("[>] Building radial image...")
    src = cv2.imread(image_path)
    if src is None:
        raise ValueError(f"Could not read image: {image_path}")

    result = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for y_pos in range(resolution):
        for x_pos in range(resolution):
            distance = np.sqrt(x_pos * x_pos + y_pos * y_pos)
            max_dist = np.sqrt(resolution**2 + resolution**2)
            norm_dist = distance / max_dist
            if norm_dist <= 1.0:
                src_x = int(norm_dist * (src.shape[1] - 1))
                src_y = src.shape[0] // 2
                result[y_pos, x_pos] = src[src_y, src_x]
            else:
                result[y_pos, x_pos] = [50, 50, 50]

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
def main():
    processed = load_processed()
    if processed:
        last_video, last_folder = list(processed.items())[-1]
        reuse = input(f"Reuse last video? ({last_video}) [y/n]: ").strip().lower()
    else:
        reuse = "n"

    if reuse == "y":
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

    poster_mode = input("Run in poster mode? (y/n): ").strip().lower() == "y"
    resolution = POSTER_RESOLUTION if poster_mode else QUICK_RESOLUTION

    already_processed = processed.get(video_path) == folder_name
    if already_processed:
        print("[!] Video previously processed – skipping frame extraction.")
    else:
        extract_frames(video_path, frame_dir, FPS)
        processed[video_path] = folder_name
        save_processed(processed)

    # Use horizontal file (existing from other script) or fallback to first frame
    horizontal_path = os.path.join(output_dir, "linear_hq.png")
    if not os.path.exists(horizontal_path):
        print("[!] No horizontal image found. Using first frame as source.")
        first_frame = sorted(os.listdir(frame_dir))[0]
        horizontal_path = os.path.join(frame_dir, first_frame)

    radial_out = os.path.join(output_dir, "radial_hq.png")
    build_radial_image(horizontal_path, radial_out, resolution)

if __name__ == "__main__":
    main()