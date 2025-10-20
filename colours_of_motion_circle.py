import os
import json
import numpy as np
from PIL import Image, ImageDraw

FRAME_ROOT = "frames"
OUTPUT_ROOT = "outputs"

def select_folder(root):
    """List available subfolders and let user select one."""
    folders = [f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))]
    if not folders:
        print("No processed folders found.")
        return None
    for i, folder in enumerate(folders, 1):
        print(f"{i}: {folder}")
    choice = int(input("Select folder: ").strip()) - 1
    return folders[choice]

def build_circle_image(metadata_path, output_path, resolution=6000, inner_radius_ratio=0.25):
    """Create a full circular image based on frame colours."""
    with open(metadata_path, 'r') as f:
        data = json.load(f)
    
    colours = [tuple(frame["color"]) for frame in data]
    n_frames = len(colours)
    print(f"[>] Building full circle with {n_frames} frames")

    # Prepare blank image
    img = Image.new("RGB", (resolution, resolution), "white")
    draw = ImageDraw.Draw(img)
    center = resolution // 2
    outer_radius = resolution // 2
    inner_radius = int(outer_radius * inner_radius_ratio)

    # Draw each slice
    for i, color in enumerate(colours):
        start_angle = (i / n_frames) * 360
        end_angle = ((i + 1) / n_frames) * 360
        draw.pieslice([center - outer_radius, center - outer_radius,
                       center + outer_radius, center + outer_radius],
                      start=start_angle, end=end_angle, fill=color, outline=None)

    # Draw white circle in center (donut effect)
    draw.ellipse([center - inner_radius, center - inner_radius,
                  center + inner_radius, center + inner_radius], fill="white")

    img.save(output_path, "PNG", optimize=False, compress_level=1)
    print(f"[✓] Saved full circle image: {output_path}")

def main():
    folder = select_folder(FRAME_ROOT)
    if not folder:
        return
    frame_dir = os.path.join(FRAME_ROOT, folder)
    metadata_path = os.path.join(frame_dir, "data.json")
    if not os.path.exists(metadata_path):
        print("[✗] Metadata not found. Run processing script first.")
        return

    output_dir = os.path.join(OUTPUT_ROOT, folder)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "circle_full.png")
    
    build_circle_image(metadata_path, output_path)

if __name__ == "__main__":
    main()