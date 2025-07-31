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

# Cinematic style tuning
SIMILARITY_THRESHOLD = 25  # Lower = more scene splits
BASE_STRIPE_HEIGHT = 5
COLUMN_WIDTH_RATIO = 0.35  # Width of central band (percentage of canvas)
FEATHER_RADIUS = 2         # Blur feathering

# === UTILS ===
def list_folders(base_path):
    """Lists all subfolders in a directory."""
    folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]
    return sorted(folders)

def load_metadata(folder_path):
    """Loads data.json from a processed frames folder."""
    data_file = os.path.join(folder_path, "data.json")
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"No data.json found in {folder_path}")
    with open(data_file, 'r') as f:
        return json.load(f)

# === CLASSIC VERTICAL ===
def build_vertical_classic(metadata, output_path, target_width=1600, target_height=20000):
    print("[>] Building classic vertical image...")
    colours = [frame["average_color"] for frame in metadata]
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

# === CINEMATIC VERTICAL ===
def colour_distance(c1, c2):
    return np.linalg.norm(np.array(c1) - np.array(c2))

def build_vertical_cinematic(metadata, output_path, target_width=POSTER_WIDTH, target_height=POSTER_HEIGHT):
    print("[>] Building cinematic vertical image...")
    colours = [frame["average_color"] for frame in metadata]

    # Group frames by colour similarity
    grouped_colours = []
    group_sizes = []
    current_group = [colours[0]]
    for c in colours[1:]:
        if colour_distance(c, current_group[-1]) < SIMILARITY_THRESHOLD:
            current_group.append(c)
        else:
            grouped_colours.append(np.mean(current_group, axis=0))
            group_sizes.append(len(current_group))
            current_group = [c]
    grouped_colours.append(np.mean(current_group, axis=0))
    group_sizes.append(len(current_group))

    # Create canvas
    image = Image.new("RGB", (target_width, target_height), "black")
    draw = ImageDraw.Draw(image)
    column_width = int(target_width * COLUMN_WIDTH_RATIO)
    x1 = (target_width - column_width) // 2
    x2 = x1 + column_width

    # Draw variable height stripes
    y = 0
    for colour, size in zip(grouped_colours, group_sizes):
        stripe_height = BASE_STRIPE_HEIGHT * max(1, size // 2)
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
    # List available processed folders
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

    # Build classic and cinematic verticals
    classic_out = os.path.join(output_dir, "vertical_classic.png")
    cinematic_out = os.path.join(output_dir, "vertical_cinematic.png")

    build_vertical_classic(metadata, classic_out, target_width=1600, target_height=20000)
    build_vertical_cinematic(metadata, cinematic_out, target_width=POSTER_WIDTH, target_height=POSTER_HEIGHT)

    print("[✓] Vertical generation complete.")

if __name__ == "__main__":
    main()