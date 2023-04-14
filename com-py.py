from PIL import Image
import numpy as np
import cv2
import os
import time

# Replace the path below with the path to your movie file
video_path = '/Users/Chris/Documents/github/com-py/Portals.mp4'

# Create a VideoCapture object and get the frames per second of the video
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)

# Define the number of frames to process (set to None to process all frames)
num_frames = None

# Set up variables to store the average color of each frame
avg_colors = []
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Process each frame in the video
frame_count = 0
start_time = time.time()
while cap.isOpened():
    # Read the next frame from the video
    ret, frame = cap.read()
    if not ret:
        break
    
    # Convert the frame from BGR to RGB format
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Calculate the average color of the frame
    avg_color = tuple(np.round(frame.mean(axis=(0,1))).astype(np.uint8))
    avg_colors.append(avg_color)
    
    # Show progress
    frame_count += 1
    if num_frames is not None and frame_count >= num_frames:
        break
    print(f'Processed frame {frame_count} of {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))} ({frame_count/int(cap.get(cv2.CAP_PROP_FRAME_COUNT))*100:.2f}%)')
    
# Release the VideoCapture object
cap.release()

# Create a new image to store the panorama
panorama = Image.new('RGB', (len(avg_colors), height), color='black')

# Draw each stripe onto the panorama
for x, color in enumerate(avg_colors):
    stripe = Image.new('RGB', (1, height), color=color)
    panorama.paste(stripe, (x, 0))

# Check if the panorama is too large and resize it if needed
if panorama.size[0] > 65500:
    print(f'Panorama too large, resizing to 65500 pixels')
    aspect_ratio = panorama.size[0] / panorama.size[1]
    new_height = int(65500 / aspect_ratio)
    panorama = panorama.resize((65500, new_height))

# Save the panorama
output_path = os.path.splitext(video_path)[0] + '-pan.jpg'
panorama.save(output_path)

end_time = time.time()

print(f'Panorama saved to {output_path}')
print(f'Time taken: {end_time - start_time:.2f} seconds')
