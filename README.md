# Smart-Traffic-Management
## Overview
A real-time, density-based traffic light control system built for the Raspberry Pi 5. This project utilizes Classical Computer Vision to monitor intersection traffic, dynamically adjust green-light times based on vehicle density, and provide immediate lane overrides for emergency/priority vehicles.

Built using Python and OpenCV, the system processes video locally at the edge (30 FPS) without relying on external cloud processing or heavy Deep Learning models.

## Key Features
Dynamic Density Routing: Compares vehicle counts between horizontal and vertical lanes to optimize traffic flow.

Emergency Vehicle Override: Calculates bounding box area thresholds to identify large priority vehicles, immediately granting them a green light.

Failsafe Idle Timer: Automatically cycles lights every 10 seconds if the intersection is completely empty to prevent system starvation.

Auto-Calibration: Uses a 5-second startup sequence to map the geometric boundaries of the intersection using visual markers.

## Filters & Morphological Processing
Instead of a heavy neural network, this system achieves high-speed object detection using a highly tuned Classical Computer Vision pipeline.
HSV Color Filtering (cv2.inRange): The raw BGR camera feed is converted to the Hue, Saturation, Value (HSV) color space. This makes the system highly robust to changes in room lighting. A binary mask is created to isolate specific colors (e.g., yellow vehicles), turning targets white and the background black.
Gaussian Blur (cv2.blur): A 3x3 kernel is applied to smooth edges and remove high-frequency camera noise before structural changes are made.
Morphological Processing Pipeline:
To ensure accurate contour detection, the binary mask undergoes a strict morphological sequence to clean up the data:

Dilation (iterations=10): Expands the white pixels. This bridges internal gaps and merges fragmented parts of a single car (e.g., if a shadow splits the car in half) into one solid continuous blob.

Erosion (iterations=1): Shrinks the white pixels. This strips away tiny speckles of background noise or dust that survived the color filter, preventing false positive "cars".

Final Dilation (iterations=5): Restores the surviving vehicle blobs back to their accurate real-world size so the Area calculation (width * height) works correctly for the priority vehicle override.

Contour Extraction & Bounding Boxes: cv2.findContours and cv2.minAreaRect wrap the cleaned morphological blobs in mathematical rectangles to extract $X/Y$ coordinates and spatial area.

## Hardware Requirements
Raspberry Pi 5 (with active cooling recommended)

Raspberry Pi Camera Module

4x LEDs (Red & Green)

4x 220Ω Resistors

Jumper wires & Breadboard

## To run the code
libcamerify python3 final_traffic.py

##Images
<img width="1919" height="1067" alt="Screenshot 2026-03-18 112243" src="https://github.com/user-attachments/assets/8a0596e4-98e4-4af4-abe6-5e538053ca67" />
<img width="1908" height="1063" alt="Screenshot 2026-03-18 112151" src="https://github.com/user-attachments/assets/51ddb3e5-39e7-4092-9aa4-5254c182b94b" />
<img width="1908" height="1041" alt="Screenshot 2026-03-18 111927" src="https://github.com/user-attachments/assets/739c9b17-d6e4-4991-aabc-12458befc2d6" />


