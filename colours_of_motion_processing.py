import os
import subprocess
import json
from PIL import Image
import numpy as np

# === CONFIGURATION ===
FPS_STANDARD = 0.1   # 1 frame every 10 seconds
FPS_CIRCLE = 1       # 1 frame every second
STRIP_HEIGHT = 100   # Height of 1px-wide strips
PROCESSED_FILE = "processed_files.json"
FRAME_ROOT = "frames"
CIRCLE_ROOT = "circle_data"

# === FRAME EXTRACTION (STANDARD MODE) ===
def extract_frames(video_path, output_dir, fps):
    """Extract full frames using ffmpeg with HDR tone mapping."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-an", "-sn",
        "-i", video_path,
        "-map", "0:v",
        "-vf", (
            f"fps={fps},"
            "zscale=t=linear:npl=100,"
            "format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=hable,"
            "zscale=t=bt709,"
            "format=yuv420p"
        ),
        "-q:v", "1", "-fps_mode", "vfr",
        "-loglevel", "warning", "-hide_banner", "-stats",
        os.path.join(output_dir, "frame_%04d.jpg")
    ]
    print(f"[>] Extracting frames (standard): {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[✓] Frame extraction complete.")

# === METADATA (Standard mode) ===
def calculate_frame_data(image_path):
    img = Image.open(image_path).convert('RGB')
    np_img = np.array(img, dtype=np.float32)
    avg_color = np_img.mean(axis=(0, 1))
    brightness = (0.299 * avg_color[0]) + (0.587 * avg_color[1]) + (0.114 * avg_color[2])
    max_c, min_c = np.max(avg_color), np.min(avg_color)
    saturation = (max_c - min_c) / (max_c + 1e-5)
    return {
        "frame": os.path.basename(image_path),
        "color": [int(avg_color[0]), int(avg_color[1]), int(avg_color[2])],
        "brightness": float(brightness),
        "saturation": float(saturation)
    }

def save_metadata(metadata, frame_dir):
    output_file = os.path.join(frame_dir, "data.json")
    with open(output_file, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"[✓] Metadata saved to {output_file}")

# === CIRCLE MODE EXTRACTION (Direct HDR Tone-Mapped Strips) ===
def extract_circle_strips(video_path, output_dir, fps=1, strip_height=100):
    """Extract 1px-wide tone-mapped strips directly using ffmpeg."""
    os.makedirs(output_dir, exist_ok=True)
    cmd = [
        "ffmpeg", "-an", "-sn",
        "-i", video_path,
        "-map", "0:v",
        "-vf", (
            f"fps={fps},"
            "zscale=t=linear:npl=100,"
            "format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=hable,"
            "zscale=t=bt709,"
            "format=yuv420p,"
            f"scale=1:{strip_height}"
        ),
        "-q:v", "1", "-fps_mode", "vfr",
        "-loglevel", "warning", "-hide_banner", "-stats",
        os.path.join(output_dir, "strip_%04d.png")
    ]
    print(f"[>] Extracting 1px strips (circle mode): {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[✓] 1px strips extraction complete.")

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
    reuse = "n"
    video_path = ""
    folder_name = ""

    # Reuse last video
    if "last_video" in processed:
        video_path = processed["last_video"]["path"]
        folder_name = processed["last_video"]["folder"]
        reuse = input(f"Reuse last video? ({video_path}) [y/n]: ").strip().lower()

    if reuse != "y":
        video_path = input("Enter full path to video file: ").strip()
        if not os.path.exists(video_path):
            print("[✗] Video not found.")
            return
        folder_name = input("Enter folder name (e.g. 'Aliens (1986) - tt0090605'): ").strip()

    # Choose mode
    mode = input("Choose mode: [1] Standard (radial/vertical) [2] Circle (donut poster): ").strip()
    mode = "2" if mode == "2" else "1"

    if mode == "1":
        frame_dir = os.path.join(FRAME_ROOT, folder_name)
        os.makedirs(frame_dir, exist_ok=True)
        if processed.get("last_video", {}).get("folder") == folder_name and os.listdir(frame_dir):
            print("[!] Video previously processed – skipping extraction.")
        else:
            extract_frames(video_path, frame_dir, FPS_STANDARD)
        print("[>] Processing metadata...")
        metadata = []
        for i, file in enumerate(sorted(os.listdir(frame_dir)), 1):
            if file.lower().endswith(('.jpg', '.jpeg', '.png')):
                data = calculate_frame_data(os.path.join(frame_dir, file))
                metadata.append(data)
                if i % 100 == 0:
                    print(f"  Processed {i} frames...")
        save_metadata(metadata, frame_dir)

    else:
        circle_dir = os.path.join(CIRCLE_ROOT, folder_name)
        os.makedirs(circle_dir, exist_ok=True)
        if os.listdir(circle_dir):
            print("[!] Circle data already processed – skipping extraction.")
        else:
            extract_circle_strips(video_path, circle_dir, FPS_CIRCLE, STRIP_HEIGHT)

    # Save last video info
    processed["last_video"] = {"path": video_path, "folder": folder_name}
    save_processed(processed)
    print("[✓] Processing complete.")

if __name__ == "__main__":
    main()