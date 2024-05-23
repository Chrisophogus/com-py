import cv2
import numpy as np
import matplotlib.pyplot as plt

def extract_average_colours(video_path):
    cap = cv2.VideoCapture(video_path)
    average_colours = []

    while True:
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

    for i in range(height):
        for j in range(width):
            angle = 2 * np.pi * j / width
            x = int(radius + (i - radius) * np.cos(angle))
            y = int(radius + (i - radius) * np.sin(angle))
            if 0 <= x < height and 0 <= y < height:
                circular_image[x, y] = timeline_image[i, j]

    return circular_image

# Main script
video_path = 'path_to_your_video.mkv'  # Replace with your MKV file path
average_colours = extract_average_colours(video_path)
timeline_image = create_timeline_image(average_colours)
circular_image = create_circular_image(timeline_image)

# Display the final circular image
plt.imshow(cv2.cvtColor(circular_image, cv2.COLOR_BGR2RGB))
plt.axis('off')
plt.show()

# Save the image if needed
cv2.imwrite('circular_colour_timeline.png', circular_image)
