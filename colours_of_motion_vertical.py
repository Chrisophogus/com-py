import os
import json
from PIL import Image, ImageDraw, ImageFilter
import numpy as np

# === CONFIGURATION ===
FRAME_ROOT = "frames"
OUTPUT_ROOT = "outputs"

# Poster size
POSTER_WIDTH = 3000
POSTER_HEIGHT = 5000

# Cinematic tuning
BASE_STRIPE_HEIGHT = 4        # height per frame
MIN_WIDTH_RATIO = 0.2         # narrowest stripe = 20% of full width
MAX_WIDTH_RATIO = 0.9         # widest stripe = 90% of full width
FEATHER_RADIUS = 2            # blur amount

# === UTILS ===
def list_folders(base_path):
    return sorted([f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))])

def load_metadata(folder_path):
    data_file = os.path.join(folder_path, "data.json")
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"No data.json found in {folder_path}")
    with open(data_file, 'r') as f:
        return json.load(f)

# === CLASSIC VERTICAL ===
def build_vertical_classic(metadata, output_path, target_width=1600, target_height=20000):
    print("[>] Building classic vertical image...")
    colours = [frame["color"] for frame in metadata]
    n_frames = len(colours)
    stripe_height = max(1, target_height // n_frames)
    actual_height = n_frames * stripe_height

    image_array = np.zeros((actual_height, target_width, 3), dtype=np.uint8)
    for i, color in enumerate(colours):
        start_y = i * stripe_height
        end_y = start_y + stripe_height
        image_array[start_y:end_y, :] = color

    image = Image.fromarray(image_array, 'RGB')
    image = image.resize((target_width, target_height), Image.LANCZOS)
    image.save(output_path, "PNG", optimize=False, compress_level=1)
    print(f"[✓] Saved classic vertical image: {output_path}")

# === CINEMATIC VERTICAL (BRIGHTNESS-BASED WIDTH) ===
def build_vertical_cinematic(metadata, output_path, target_width=POSTER_WIDTH, target_height=POSTER_HEIGHT):
    print("[>] Building cinematic brightness-based vertical image...")

    # Extract brightness values
    brightness_values = [frame["brightness"] for frame in metadata]
    min_b, max_b = min(brightness_values), max(brightness_values)
    colours = [frame["color"] for frame in metadata]
    n_frames = len(colours)

    # Fixed height per frame
    stripe_height = max(1, target_height // n_frames)

    # Create black canvas
    image = Image.new("RGB", (target_width, target_height), "black")
    draw = ImageDraw.Draw(image)

    y = 0
    for colour, brightness in zip(colours, brightness_values):
        # Map brightness to stripe width
        norm_b = (brightness - min_b) / (max_b - min_b + 1e-5)
        stripe_width = int(MIN_WIDTH_RATIO * target_width + norm_b * (MAX_WIDTH_RATIO - MIN_WIDTH_RATIO) * target_width)

        x1 = (target_width - stripe_width) // 2
        x2 = x1 + stripe_width

        draw.rectangle([x1, y, x2, y + stripe_height], fill=tuple(map(int, colour)))
        y += stripe_height
        if y >= target_height:
            break

    # Feather edges
    blurred = image.filter(ImageFilter.GaussianBlur(radius=FEATHER_RADIUS))
    final = Image.composite(blurred, image, image.convert("L"))
    final.save(output_path, "PNG", optimize=False, compress_level=1)
    print(f"[✓] Saved cinematic vertical image: {output_path}")

# === MAIN ===
def main():
    folders = list_folders(FRAME_ROOT)
    if not folders:
        print("[✗] No processed frame folders found.")
        return

    print("Available processed movies:")
    for i, folder in enumerate(folders, start=1):
        print(f"  {i}. {folder}")

    choice = input("Select a folder number: ").strip()
    try:
        folder_name = folders[int(choice) - 1]
    except (ValueError, IndexError):
        print("[✗] Invalid selection.")
        return

    frame_dir = os.path.join(FRAME_ROOT, folder_name)
    output_dir = os.path.join(OUTPUT_ROOT, folder_name)
    os.makedirs(output_dir, exist_ok=True)

    metadata = load_metadata(frame_dir)

    # Build both styles
    classic_out = os.path.join(output_dir, "vertical_classic.png")
    cinematic_out = os.path.join(output_dir, "vertical_cinematic.png")

    build_vertical_classic(metadata, classic_out, target_width=1600, target_height=20000)
    build_vertical_cinematic(metadata, cinematic_out, target_width=POSTER_WIDTH, target_height=POSTER_HEIGHT)

    print("[✓] Vertical generation complete.")

if __name__ == "__main__":
    main()