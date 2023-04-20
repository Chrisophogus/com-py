from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import os

# Set up parameters for the circle image
video_path = '/Users/Chris/Documents/github/com-py/Portals.mp4'
processed_dir = '/Users/Chris/Documents/github/com-py/processing/Portals'
output_path = os.path.splitext(video_path)[0] + '-circle.png'

width, height = Image.open(os.path.join(processed_dir, '000001.png')).size
size = (width, height)
center_x = int(width / 2)
center_y = int(height / 2)
radius = 3

# Create a new image for the circle
circle_img = Image.new('RGBA', size, (255, 255, 255, 0))

# Draw the circle on the new image
draw = ImageDraw.Draw(circle_img)
draw.ellipse((center_x - radius, center_y - radius, center_x + radius, center_y + radius), fill=(255, 255, 255, 255))

# Set up the output image
output_img = Image.new('RGBA', size, (0, 0, 0, 0))

# Paste each stripe onto the output image with increasing distance from the center
for i in range(1, len(os.listdir(processed_dir))+1):
    stripe_path = os.path.join(processed_dir, f'{i:06d}.png')
    stripe = Image.open(stripe_path)
    angle = (i-1) / (len(os.listdir(processed_dir))-1) * 2 * np.pi
    x = int(center_x + radius * i * np.cos(angle))
    y = int(center_y + radius * i * np.sin(angle))
    output_img.paste(stripe, (x, y))

# Paste the circle image onto the output image
output_img.paste(circle_img, (center_x - radius, center_y - radius))

# Save the output image
output_img.save(output_path)
