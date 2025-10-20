import os
import cv2
import numpy as np
from PIL import Image

# === CONFIGURATION ===
CIRCLE_ROOT = "circle_data"
OUTPUT_ROOT = "outputs"
RESOLUTION = 6000  # Final image size (square)

def list_movie_folders(base_dir):
    """List available processed movie folders."""
    return [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]

def build_donut_poster(input_dir, output_path, resolution=6000):
    """Builds a full circle 'donut poster' from 1px strips."""
    print(f"[>] Building donut poster from {input_dir}")

    # Collect strips
    strips = sorted(
        [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.png')]
    )
    if not strips:
        raise ValueError("No strip images found in folder!")

    print(f"[>] Found {len(strips)} strips")

    # Load strips into a list
    frames = []
    for i, file in enumerate(strips, 1):
        img = Image.open(file).convert('RGB')
        np_img = np.array(img)
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
    base_img_resized = cv2.resize(base_img, (resolution, resolution // 2), interpolation=cv2.INTER_LINEAR)

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
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    cv2.imwrite(output_path, donut_rotated)
    print(f"[✓] Saved donut poster: {output_path}")

def main():
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

    build_donut_poster(input_dir, output_path, RESOLUTION)

if __name__ == "__main__":
    main()