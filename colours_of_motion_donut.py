import os
import re
import cv2
import numpy as np
from PIL import Image
import argparse

# === CONFIGURATION ===
CIRCLE_ROOT = "circle_data"
OUTPUT_ROOT = "outputs"
QUICK_RESOLUTION = 4000
HQ_RESOLUTION = 6000
STRIP_NAME_PATTERN = re.compile(r"^strip_(\d+)\.png$", re.IGNORECASE)


def list_strip_paths(input_dir):
    strips = []
    for file in os.listdir(input_dir):
        match = STRIP_NAME_PATTERN.fullmatch(file)
        if match:
            strips.append((int(match.group(1)), os.path.join(input_dir, file)))
    return [path for _, path in sorted(strips)]

def parse_args():
    parser = argparse.ArgumentParser(description="Generate donut poster Colours of Motion output.")
    parser.add_argument(
        "--poster_mode",
        action="store_true",
        help="Render higher-resolution donut poster.",
    )
    return parser.parse_args()

def list_movie_folders(base_dir):
    """List available processed movie folders."""
    return sorted(f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f)))

def build_donut_poster(input_dir, output_path, resolution=HQ_RESOLUTION):
    """Builds a full circle 'donut poster' from 1px strips."""
    print(f"[>] Building donut poster from {input_dir}")
    if resolution < 2:
        raise ValueError("resolution must be at least 2 pixels.")

    # Collect strips
    strips = list_strip_paths(input_dir)
    if not strips:
        raise ValueError("No strip images found in folder!")

    print(f"[>] Found {len(strips)} strips")

    # Load strips into a list
    frames = []
    strip_height = None
    for i, file in enumerate(strips, 1):
        with Image.open(file) as source:
            np_img = np.array(source.convert("RGB"))
        if np_img.shape[1] < 1:
            raise ValueError(f"Strip has no colour column: {file}")
        if strip_height is None:
            strip_height = np_img.shape[0]
        elif np_img.shape[0] != strip_height:
            raise ValueError(f"Strip height does not match earlier files: {file}")
        frames.append(np_img[:, 0, :])  # Extract color column
        if i % 1000 == 0:
            print(f"  Loaded {i} strips...")

    # Convert list to array (num_strips x height x 3)
    frame_array = np.stack(frames, axis=0)

    # Create a long rectangular image (time vs height)
    height = frame_array.shape[1]
    num_strips = frame_array.shape[0]
    print(f"[>] Creating base timeline image: {num_strips}x{height}")
    base_img = np.zeros((height, num_strips, 3), dtype=np.uint8)
    for i in range(num_strips):
        base_img[:, i, :] = frame_array[i]

    # Resize to final resolution x radius
    # Use area downsampling when shrinking to reduce aliasing.
    if base_img.shape[1] > resolution:
        interp = cv2.INTER_AREA
    else:
        interp = cv2.INTER_CUBIC
    base_img_resized = cv2.resize(base_img, (resolution, resolution // 2), interpolation=interp)

    # Warp to polar coordinates (full circle)
    print("[>] Transforming to circular donut poster...")
    donut = cv2.warpPolar(
        base_img_resized,
        (resolution, resolution),
        (resolution // 2, resolution // 2),
        resolution // 2,
        cv2.WARP_FILL_OUTLIERS + cv2.WARP_POLAR_LINEAR
    )

    # Rotate so start of movie is at 12 o'clock
    donut_rotated = np.rot90(donut, k=3)

    # Save result
    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    if not cv2.imwrite(output_path, donut_rotated, [cv2.IMWRITE_PNG_COMPRESSION, 1]):
        raise OSError(f"Could not write donut poster: {output_path}")
    print(f"[✓] Saved donut poster: {output_path}")
    return output_path

def main():
    args = parse_args()
    # List available movies
    movies = list_movie_folders(CIRCLE_ROOT)
    if not movies:
        print("[✗] No circle data folders found. Run processing first.")
        return

    print("Available movies:")
    for idx, movie in enumerate(movies, 1):
        print(f"  {idx}. {movie}")

    choice = input("Select a movie number: ").strip()
    if not choice.isdigit() or int(choice) < 1 or int(choice) > len(movies):
        print("[✗] Invalid selection.")
        return

    folder_name = movies[int(choice) - 1]
    input_dir = os.path.join(CIRCLE_ROOT, folder_name)
    output_dir = os.path.join(OUTPUT_ROOT, folder_name)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "circle_donut_poster.png")

    resolution = HQ_RESOLUTION if args.poster_mode else QUICK_RESOLUTION
    build_donut_poster(input_dir, output_path, resolution)

if __name__ == "__main__":
    main()
