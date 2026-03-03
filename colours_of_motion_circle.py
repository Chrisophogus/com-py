import os
import json
import numpy as np
from PIL import Image, ImageDraw
import argparse

FRAME_ROOT = "frames"
OUTPUT_ROOT = "outputs"
QUICK_RESOLUTION = 4000
HQ_RESOLUTION = 6000
SUPERSAMPLE = 2

def parse_args():
    parser = argparse.ArgumentParser(description="Generate full-circle Colours of Motion output.")
    parser.add_argument(
        "--poster_mode",
        action="store_true",
        help="Render higher-resolution, anti-aliased output.",
    )
    return parser.parse_args()

def select_folder(root):
    """List available subfolders and let user select one."""
    folders = [f for f in os.listdir(root) if os.path.isdir(os.path.join(root, f))]
    if not folders:
        print("No processed folders found.")
        return None
    for i, folder in enumerate(folders, 1):
        print(f"{i}: {folder}")
    choice = input("Select folder: ").strip()
    if not choice.isdigit():
        print("[✗] Invalid selection.")
        return None
    index = int(choice) - 1
    if index < 0 or index >= len(folders):
        print("[✗] Invalid selection.")
        return None
    return folders[index]

def build_circle_image(
    metadata_path,
    output_path,
    resolution=HQ_RESOLUTION,
    inner_radius_ratio=0.25,
    supersample=SUPERSAMPLE,
):
    """Create a full circular image based on frame colours."""
    with open(metadata_path, 'r') as f:
        data = json.load(f)
    
    colours = [tuple(frame["color"]) for frame in data]
    n_frames = len(colours)
    if n_frames == 0:
        print("[✗] Metadata is empty. Nothing to render.")
        return
    print(f"[>] Building full circle with {n_frames} frames")

    render_size = max(1, int(resolution * supersample))
    # Render larger then downsample for smoother edges.
    img = Image.new("RGB", (render_size, render_size), "white")
    draw = ImageDraw.Draw(img)
    center = render_size // 2
    outer_radius = render_size // 2
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

    if supersample > 1:
        img = img.resize((resolution, resolution), Image.LANCZOS)

    img.save(output_path, "PNG", optimize=False, compress_level=1)
    print(f"[✓] Saved full circle image: {output_path}")

def main():
    args = parse_args()
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
    
    resolution = HQ_RESOLUTION if args.poster_mode else QUICK_RESOLUTION
    build_circle_image(metadata_path, output_path, resolution=resolution)

if __name__ == "__main__":
    main()
