from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import cv2
import os
import time

# Prompt the user for the path to the video file
video_path = input("Enter the path to the video file: ")

# Create a VideoCapture object and get the frames per second of the video
cap = cv2.VideoCapture(video_path)
fps = cap.get(cv2.CAP_PROP_FPS)

# Define the number of frames to process (set to None to process all frames)
num_frames = None

# Set up variables to store the average color of each frame
avg_colors = []
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

# Set up directory to store processed frames
filename = os.path.splitext(os.path.basename(video_path))[0]
processed_dir = os.path.join('./processing', filename)
if not os.path.exists(processed_dir):
    os.makedirs(processed_dir)

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
    
    # Create a new image for the stripe and save it
    stripe = Image.new('RGB', (1, height), color=avg_color)
    stripe.save(os.path.join(processed_dir, f'{frame_count + 1:06d}.png'))
    
    # Show progress
    frame_count += 1
    if num_frames is not None and frame_count >= num_frames:
        break
    print(f'Processed frame {frame_count} of {int(cap.get(cv2.CAP_PROP_FRAME_COUNT))} ({frame_count/int(cap.get(cv2.CAP_PROP_FRAME_COUNT))*100:.2f}%)')
    
# Release the VideoCapture object
cap.release()

# Create a new image to store the panorama
panorama = Image.new('RGBA', (len(avg_colors), height), color=(0, 0, 0, 0))

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
output_path = os.path.splitext(video_path)[0] + '-pan.png'
panorama.save(output_path)

end_time = time.time()

print(f'Panorama saved to {output_path}')
print(f'Time taken: {end_time - start_time:.2f} seconds')

# Open the panorama image
panorama_img = Image.open(output_path)

# Get the center of the image
center_x = int(panorama_img.width / 2)
center_y = panorama_img.height

# Define the radius of the circle
radius = int(panorama_img.width / 2)

# Create a new image for the circle
circle_img = Image.new('RGBA', panorama_img.size, (255, 255, 255, 0))

# Draw the circle on the new image
draw = ImageDraw.Draw(circle_img)
draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=(255, 255, 255, 255))

# Paste the panorama onto the circle image with alpha mask
circle_img.paste(panorama_img, (0, 0), panorama_img)

# Save the circle image
output_circle_path = os.path.splitext(video_path)[0] + '-pan-circle.png'
circle_img.save(output_circle_path)

print(f'Circle panorama saved to {output_circle_path}')

