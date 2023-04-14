import cv2
import numpy as np
import os

def create_panorama(input_path):
    # Open the video file
    cap = cv2.VideoCapture(input_path)

    # Get the width and height of the frames
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Initialize an empty panorama
    panorama = np.zeros((height, width * 2, 3), dtype=np.uint8)

    # Loop through the frames of the video
    frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Get the average color of the frame
        avg_color = np.mean(frame, axis=(0, 1))

        # Create a strip of the average color
        strip = np.ones((height, width, 3), dtype=np.uint8) * avg_color

        # Add the strip to the panorama
        panorama[:, frame_count * width : (frame_count + 1) * width] = strip

        frame_count += 1

    # Release the video capture
    cap.release()

    # Save the panorama as a JPEG file in the same directory as the input file
    output_path = os.path.splitext(input_path)[0] + ".jpg"
    cv2.imwrite(output_path, panorama)

    print("Panorama created and saved to:", output_path)

# Test the function with an example MKV file
input_path = "example.mkv"
create_panorama(input_path)
