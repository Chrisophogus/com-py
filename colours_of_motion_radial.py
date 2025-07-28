import os
import subprocess
import json
from PIL import Image, ImageDraw
import numpy as np
import cv2

# === CONFIGURATION ===
FPS = 0.1
LINE_HEIGHT = 100
STRIPE_WIDTH = 4
RESOLUTION = 3000
PROCESSED_FILE = "processed_files.json"
FRAME_ROOT = "frames"
OUTPUT_ROOT = "outputs"

# === FRAME EXTRACTION ===
def extract_frames(video_path, frame_dir, fps=FPS):
    """
    Extracts HDR frames with tone mapping using ffmpeg.
    """
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

    print(f"[>] Extracting frames with tone mapping:\n{' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    print("[✓] HDR tone-mapped frame extraction complete.")

# === AVERAGE COLOUR ===
def average_color(image_path):
    img = Image.open(image_path).convert('RGB')
    np_img = np.array(img)
    avg = np_img.mean(axis=(0, 1))
    return tuple(avg.astype(int))

# === IMAGE BUILDERS ===
def build_horizontal_image(frame_dir, output_path, stripe_width=4, line_height=100):
    colours = []
    for file in sorted(os.listdir(frame_dir)):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                colours.append(average_color(os.path.join(frame_dir, file)))
            except Exception as e:
                print(f"[!] Skipping {file}: {e}")

    if not colours:
        raise ValueError("No valid images found.")

    width = len(colours) * stripe_width
    image = Image.new("RGB", (width, line_height))
    draw = ImageDraw.Draw(image)

    for i, color in enumerate(colours):
        x = i * stripe_width
        draw.rectangle([x, 0, x + stripe_width, line_height], fill=color)

    image.save(output_path)
    print(f"[✓] Saved horizontal bar image: {output_path}")

def build_vertical_image(frame_dir, output_path, stripe_height=100, stripe_width=4):
    colours = []
    for file in sorted(os.listdir(frame_dir)):
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                colours.append(average_color(os.path.join(frame_dir, file)))
            except Exception as e:
                print(f"[!] Skipping {file}: {e}")

    if not colours:
        raise ValueError("No valid images found.")

    height = len(colours) * stripe_height
    image = Image.new("RGB", (stripe_width, height))
    draw = ImageDraw.Draw(image)

    for i, color in enumerate(colours):
        y = i * stripe_height
        draw.rectangle([0, y, stripe_width, y + stripe_height], fill=color)

    image.save(output_path)
    print(f"[✓] Saved vertical bar image: {output_path}")

def linear_to_wave_pattern_debug(image_path, output_path, resolution=3000):
    """
    Creates a radial swirl image using a simple polar transformation.
    """
    src = cv2.imread(image_path)
    if src is None:
        raise ValueError(f"Could not read image: {image_path}")

    print(f"Debug: Source shape = {src.shape}")

    result = np.zeros((resolution, resolution, 3), dtype=np.uint8)
    for y in range(resolution):
        for x in range(resolution):
            dx = x
            dy = y
            distance = np.sqrt(dx * dx + dy * dy)
            max_dist = np.sqrt(resolution**2 + resolution**2)
            norm_dist = distance / max_dist

            if norm_dist <= 1.0:
                src_x = int(norm_dist * (src.shape[1] - 1))
                src_y = src.shape[0] // 2
                result[y, x] = src[src_y, src_x]
            else:
                result[y, x] = [50, 50, 50]

    cv2.imwrite(output_path, result)
    print(f"[✓] Saved swirl debug image: {output_path}")

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
    # Step 1: Get inputs
    video_path = input("Enter full path to video file: ").strip()
    if not os.path.exists(video_path):
        print("[✗] Video not found.")
        return

    folder_name = input("Enter folder name (e.g. 'Aliens (1986) - tt0090605'): ").strip()
    frame_dir = os.path.join(FRAME_ROOT, folder_name)
    output_dir = os.path.join(OUTPUT_ROOT, folder_name)

    os.makedirs(output_dir, exist_ok=True)

    # Step 2: Check processed
    processed = load_processed()
    already_processed = processed.get(video_path) == folder_name

    if already_processed:
        print("[!] Video previously processed – skipping frame extraction.")
    else:
        extract_frames(video_path, frame_dir, FPS)
        processed[video_path] = folder_name
        save_processed(processed)

    # Step 3: Generate outputs
    linear_out = os.path.join(output_dir, "linear.png")
    vertical_out = os.path.join(output_dir, "vertical.png")
    swirl_out = os.path.join(output_dir, "radial.png")

    build_horizontal_image(frame_dir, linear_out, STRIPE_WIDTH, LINE_HEIGHT)
    build_vertical_image(frame_dir, vertical_out, LINE_HEIGHT, STRIPE_WIDTH)
    linear_to_wave_pattern_debug(linear_out, swirl_out, RESOLUTION)

if __name__ == "__main__":
    main()