from PIL import Image, ImageDraw, ImageOps
import math

# Load the panorama image
panorama = Image.open('duggee.jpg')

# Calculate the size of the circular image
diameter = min(panorama.size)
diameter = diameter - diameter % 2  # ensure diameter is an even number

# Extract a strip of pixels from the far left of the panorama
left_strip = panorama.crop((0, 0, int(diameter/2), panorama.size[1]))

# Append the left strip to the right side of the panorama until the right side becomes the outside edge of the circle
while panorama.size[0] < diameter:
    panorama = ImageOps.expand(panorama, border=1, fill='black')
    panorama.paste(left_strip, (panorama.size[0]-left_strip.size[0], 0))

# Create a circular mask with a black background and a white circle in the center
mask = Image.new('L', (diameter, diameter), 0)
draw = ImageDraw.Draw(mask)
draw.ellipse((0, 0, diameter, diameter), fill=255)

# Resize and paste the panorama image onto the mask
panorama = panorama.resize((diameter, diameter))
panorama.putalpha(mask)

# Save the circular version of the original panorama image
panorama.save('panorama_circle.png')
