import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import pickle
from tqdm import tqdm


def extract_average_colours(video_path, cache_path):
  """
  Extracts average colors from each frame of a video.
  """
  if os.path.exists(cache_path):
    with open(cache_path, 'rb') as f:
      return pickle.load(f)

  if not os.path.exists(video_path):
    raise FileNotFoundError(f"Video file not found: {video_path}")

  cap = cv2.VideoCapture(video_path)
  if not cap.isOpened():
    raise ValueError(f"Could not open video file: {video_path}")

  frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
  average_colours = []

  for _ in tqdm(range(frame_count), desc="Processing frames"):
    ret, frame = cap.read()
    if not ret:
      break
    avg_colour_per_row = np.average(frame, axis=0)
    avg_colour = np.average(avg_colour_per_row, axis=0)
    average_colours.append(avg_colour)

  cap.release()
  average_colours = np.array(average_colours, dtype=np.uint8)

  with open(cache_path, 'wb') as f:
    pickle.dump(average_colours, f)

  return average_colours


def create_timeline_image(average_colours):
  """
  Creates a vertical image with each row representing the average color of a frame.
  """
  height = average_colours.shape[0]
  timeline_image = np.zeros((height, 1, 3), dtype=np.uint8)

  for i in range(height):
    timeline_image[i] = average_colours[i]

  return cv2.resize(timeline_image, (500, height))


def create_circular_image(timeline_image):
  """
  Creates a circular image with a single spiral pattern showing only the bottom right quarter.
  """
  height, width, _ = timeline_image.shape
  # Adjust radius to ensure the spiral doesn't touch the edges
  max_radius = int(min(height, width) / 2 * 0.8)  # Adjust factor for smaller radius
  circular_image = np.zeros((max_radius, max_radius, 3), dtype=np.uint8)

  for i in tqdm(range(max_radius), desc="Creating circular image"):
    # Calculate offset for spiral mapping
    offset = int(i / max_radius * width)  # Adjust factor for tighter/looser spiral

    for j in range(width):
      # Use offset for color mapping
      adjusted_j = (j + offset) % width

      # Only process pixels in the bottom right quarter
      if i >= max_radius // 2 and j >= width // 2:
        angle = 2 * np.pi * adjusted_j / width
        x = int(i * np.cos(angle))
        y = int(i * np.sin(angle))
        # Check for valid coordinates within the circular image
        if 0 <= x + max_radius // 2 < max_radius and 0 <= y + max_radius // 2 < max_radius:
          circular_image[y + max_radius // 2, x + max_radius // 2] = timeline_image[i, adjusted_j]

  return circular_image


# Main script
video_filename = 'your_video_file.mkv'  # Replace with your MKV file name
cache_folder = 'processing'
os.makedirs(cache_folder, exist_ok=True)
cache_filename = os.path.join(cache_folder, f"{os.path.splitext(video_filename)[0]}_avg_colours.pkl")

average_colours = extract_average_colours(video_filename, cache_filename)
timeline_image = create_timeline_image(average_colours)
circular_image = create_circular_image(timeline_image)

# No rotation needed since center is already at top left

# Save the final circular image to a

output_filename = 'circular_colour_timeline.png'
cv2.imwrite(output_filename, cv2.cvtColor(circular_image, cv2.COLOR_BGR2RGB))

print(f"Circular colour timeline (bottom right quarter) saved as {output_filename}")