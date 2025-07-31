import os
import subprocess
import json
from PIL import Image
import numpy as np

# === CONFIGURATION ===
FPS = 0.1  # frames per second for sampling
FRAME_ROOT = "frames"
PROCESSED_FILE = "processed_files.json"


# === FRAME EXTRACTION ===
def extract_frames(video_path, frame_dir, fps=FPS):
    """Extracts HDR frames with tone mapping using ffmpeg."""
    os.makedirs(frame_dir, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-an",
        "-sn",
        "-i", video_path,
        "-vf", (
            f"fps={fps},"
            "zscale=t=linear:npl=100,"
            "format=gbrpf32le,"
            "zscale=p=bt709,"
            "tonemap=hable,"
            "zscale=t=bt709,"
            "format=yuv420p"
        ),
        "-q:v", "1",
        "-vsync", "0",
        "-frame_pts", "1",
        "-fps_mode", "vfr",
        "-loglevel", "warning",
        "-hide_banner",
        "-stats",
        os.path.join(frame_dir, "frame_%04d.jpg")
    ]

    print(f"[>] Extracting frames:\n{' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[✓] Frame extraction complete.")


# === AVERAGE COLOR ===
def average_color(image_path):
    """Calculates average RGB color for an image."""
    img = Image.open(image_path).convert('RGB')
    np_img = np.array(img)
    avg = np_img.mean(axis=(0, 1))
    return [int(c) for c in avg]  # Convert np.int64 to int


# === PROCESS METADATA ===
def process_frames(frame_dir):
    """Generates metadata for all frames."""
    print("[>] Processing frame metadata...")
    frame_files = sorted([
        f for f in os.listdir(frame_dir)
        if f.lower().endswith(('.jpg', '.jpeg', '.png'))
    ])

    metadata = []
    for i, file in enumerate(frame_files):
        path = os.path.join(frame_dir, file)
        color = average_color(path)
        metadata.append({
            "file": file,
            "average_color": color
        })

        if i % 100 == 0 and i != 0:
            print(f"  Processed {i} frames...")

    print(f"[✓] Processed {len(metadata)} frames")
    return metadata


# === SAVE METADATA ===
def save_metadata(metadata, frame_dir):
    """Saves metadata to a JSON file inside frame directory."""
    out_path = os.path.join(frame_dir, "data.json")
    with open(out_path, "w") as f:
        json.dump(metadata, f, indent=2)
    print(f"[✓] Saved metadata to {out_path}")


# === TRACK PROCESSED FILES ===
def load_processed():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_processed(video_path, folder_name):
    data = {
        "last_video": {
            "path": video_path,
            "folder": folder_name
        }
    }
    with open(PROCESSED_FILE, 'w') as f:
        json.dump(data, f, indent=2)


# === MAIN ===
def main():
    processed = load_processed()

    # Reuse last video if available
    if "last_video" in processed:
        last_video = processed["last_video"]["path"]
        last_folder = processed["last_video"]["folder"]
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
    os.makedirs(frame_dir, exist_ok=True)

    # Only extract frames if new video or folder is empty
    if not reuse or not os.listdir(frame_dir):
        extract_frames(video_path, frame_dir, FPS)

    # Save processed file info
    save_processed(video_path, folder_name)

    # Build metadata
    metadata = process_frames(frame_dir)
    save_metadata(metadata, frame_dir)

    print("[✓] Processing complete. Frames and metadata are ready.")


if __name__ == "__main__":
    main()