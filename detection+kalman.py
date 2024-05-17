import numpy as np
import cv2
import pyrealsense2 as rs
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

# Kalman Filter parameters
state_size = 6
meas_size = 4
contr_size = 0
type = cv2.CV_32F

# Create Kalman Filter object
kf = cv2.KalmanFilter(state_size, meas_size, contr_size, type)
state = np.zeros((state_size, 1), dtype=np.float32)
meas = np.zeros((meas_size, 1), dtype=np.float32)

# Transition State Matrix A
kf.transitionMatrix = np.eye(state_size, dtype=np.float32)

kf.measurementMatrix = np.zeros((meas_size, state_size), dtype=np.float32)
kf.measurementMatrix[0, 0] = 1.0
kf.measurementMatrix[1, 1] = 1.0
kf.measurementMatrix[2, 4] = 1.0
kf.measurementMatrix[3, 5] = 1.0

# Process Noise Covariance Matrix Q
kf.processNoiseCov = np.zeros((state_size, state_size), dtype=np.float32)
kf.processNoiseCov[0, 0] = 1e-2
kf.processNoiseCov[1, 1] = 1e-2
kf.processNoiseCov[2, 2] = 5.0
kf.processNoiseCov[3, 3] = 5.0
kf.processNoiseCov[4, 4] = 1e-2
kf.processNoiseCov[5, 5] = 1e-2

# Measures Noise Covariance Matrix R
kf.measurementNoiseCov = np.identity(meas_size, dtype=np.float32) * 1e-1

def detect_marker(frame, marker_detected):
    # Convert the frame to grayscale
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Use Canny edge detection to find edges
    edges = cv2.Canny(blurred, 50, 150)

    # Find contours in the edge-detected image
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Flag to track if a contour has been drawn
    contour_drawn = False
    
    # Initialize x, y, and radius
    x, y, radius = None, None, None

    # Filter contours based on area and circularity
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        if perimeter == 0:
            continue
        circularity = 4 * np.pi * (area / (perimeter * perimeter))

        if area > 1000 and circularity > 0.8:
            # Draw the contour
            cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
            contour_drawn = True

            # Find the center and radius of enclosing circle
            ((x, y), radius) = cv2.minEnclosingCircle(contour)
            center = (int(x), int(y))

            # Draw the outer circle (marker)
            cv2.circle(frame, center, int(radius), (0, 255, 0), 2)

            # Draw a red point in the detected circle center
            cv2.circle(frame, center, 2, (0, 0, 255), -1)

            # Find the dot inside the marker
            dot_roi = gray[int(y) - 5:int(y) + 5, int(x) - 5:int(x) + 5]
            _, dot_thresh = cv2.threshold(dot_roi, 50, 255, cv2.THRESH_BINARY)

            # Check if there's any white pixel in the dot thresholded image
            if cv2.countNonZero(dot_thresh) > 0:
                # Black dot detected, draw a circle around it
                cv2.circle(frame, center, 5, (0, 0, 255), -1)

                # Set marker_detected flag to True
                marker_detected = True

    # If no contour is drawn and marker was previously detected, set marker_detected to False
    if not contour_drawn and marker_detected:
        marker_detected = False

    return frame, marker_detected, x, y, radius

# Initialize the RealSense pipeline
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)

# Start streaming
pipeline.start(config)

print("\nHit 'q' to exit...\n")

ticks = 0
found = False
not_found_count = 0

# Initialize lists to store x, y, z coordinates for plotting
x_values = []
y_values = []
z_values = []

# Initialize the 3D plot
fig = plt.figure()
ax = fig.add_subplot(111, projection='3d')

while True:
    prec_tick = ticks
    ticks = cv2.getTickCount()
    dT = (ticks - prec_tick) / cv2.getTickFrequency()  # seconds

    # Wait for the next set of frames
    frames = pipeline.wait_for_frames()
    color_frame = frames.get_color_frame()
    if not color_frame:
        continue

    # Convert the color frame to a numpy array
    frame = np.asanyarray(color_frame.get_data())

    res = frame.copy()

    if found:
        kf.transitionMatrix[2, 2] = dT
        kf.transitionMatrix[3, 3] = dT

        state = kf.predict()

        pred_rect_width = int(state[4, 0])
        pred_rect_height = int(state[5, 0])
        pred_rect_x = int(state[0, 0] - pred_rect_width / 2)
        pred_rect_y = int(state[1, 0] - pred_rect_height / 2)
        cv2.circle(res, (int(state[0, 0]), int(state[1, 0])), 2, (255, 0, 0), -1)
        cv2.rectangle(res, (pred_rect_x, pred_rect_y), (pred_rect_x + pred_rect_width, pred_rect_y + pred_rect_height), (255, 0, 0), 2)

        # Append x, y, z values for plotting
        x_values.append(state[0, 0])
        y_values.append(state[1, 0])
        z_values.append(state[2, 0])

        # Plot the trajectory in real-time
        ax.plot(x_values, y_values, zs=z_values, color='b', marker='o')
        ax.set_xlabel('X')
        ax.set_ylabel('Y')
        ax.set_zlabel('Z')
        plt.draw()
        plt.pause(0.001)

        # Print the x, y, z location of the marker
        print(f"X: {state[0, 0]}, Y: {state[1, 0]}, Z: {state[2, 0]}")

    # Detect the marker
    res, found, x, y, radius = detect_marker(res, found)

    if len(x_values) == 0:
        not_found_count += 1
        print("notFoundCount:", not_found_count)
        if not_found_count >= 100:
            found = False
    else:
        not_found_count = 0
        if x is not None and y is not None and radius is not None:
            meas[0, 0] = x
            meas[1, 0] = y
            meas[2, 0] = float(radius)
            meas[3, 0] = float(radius)

            if not found:
                kf.errorCovPre = np.eye(state_size, dtype=np.float32)
                state[0, 0] = meas[0, 0]
                state[1, 0] = meas[1, 0]
                state[2, 0] = 0
                state[3, 0] = 0
                state[4, 0] = meas[2, 0]
                state[5, 0] = meas[3, 0]

                kf.statePost = state
                found = True
            else:
                kf.correct(meas)

    cv2.imshow("Tracking", res)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Stop streaming
pipeline.stop()

# Close all OpenCV windows
cv2.destroyAllWindows()
