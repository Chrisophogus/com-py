from PIL import Image, ImageDraw, ImageOps

# Load the panorama image
panorama = Image.open('duggee.jpg')

# Convert the image to "RGBA" mode
panorama = panorama.convert("RGBA")

# Create a new image with a transparent background
circle = Image.new('RGBA', panorama.size, (255, 255, 255, 0))

# Draw a white circle on the transparent image
diameter = panorama.width
draw = ImageDraw.Draw(circle)
draw.ellipse((0, 0, diameter, diameter), fill=(255, 255, 255, 255))

# Apply a mask to the panorama image
mask = ImageOps.fit(circle, panorama.size, centering=(0.5, 0.5))
panorama.putalpha(mask.getchannel('A'))

# Paste the masked panorama image onto the transparent circle image
final_image = Image.alpha_composite(circle, panorama)

# Save the final image as a PNG file
final_image.save('panorama_circle.png')
