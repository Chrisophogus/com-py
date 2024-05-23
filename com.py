import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
from tqdm import tqdm

def extract_average_colours(video_path):
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
    return np.array(average_colours, dtype=np.uint8)

def create_timeline_image(average_colours):
    height = average_colours.shape[0]
    timeline_image = np.zeros((height, 1, 3), dtype=np.uint8)

    for i in range(height):
        timeline_image[i] = average_colours[i]

    return cv2.resize(timeline_image, (500, height))

def create_circular_image(timeline_image):
    height, width, _ = timeline_image.shape
    radius = height // 2
    circular_image = np.zeros((height, height, 3), dtype=np.uint8)

    for i in tqdm(range(height), desc="Creating circular image"):
        for j in range(width):
            angle = 2 * np.pi * j / width
            x = int(radius + (i - radius) * np.cos(angle))
            y = int(radius + (i - radius) * np.sin(angle))
            if 0 <= x < height and 0 <= y < height:
                circular_image[x, y] = timeline_image[i, j]

    return circular_image

# Main script
video_filename = 'your_video_file.mkv'  # Replace with your MKV file name
average_colours = extract_average_colours(video_filename)
timeline_image = create_timeline_image(average_colours)
circular_image = create_circular_image(timeline_image)

# Save the final circular image to a file
output_filename = 'circular_colour_timeline.png'
plt.imsave(output_filename, cv2.cvtColor(circular_image, cv2.COLOR_BGR2RGB))

print(f"Circular colour timeline saved as {output_filename}")
