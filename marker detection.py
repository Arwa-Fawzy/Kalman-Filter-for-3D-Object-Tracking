import cv2
import numpy as np
import pyrealsense2 as rs

def detect_circle_from_video():
    # Initialize the RealSense pipeline
    pipeline = rs.pipeline()
    config = rs.config()
    config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
    pipeline.start(config)
    
    while True:
        # Wait for the next set of frames
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            continue
        color_image = np.asanyarray(color_frame.get_data())
        
        # Convert frame to grayscale
        gray = cv2.cvtColor(color_image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Detect circles using Hough Circle Transform
        circles = cv2.HoughCircles(blurred, cv2.HOUGH_GRADIENT, 1, 20,
                                   param1=50, param2=30, minRadius=10, maxRadius=30)
        
        # Check if circles are detected
        if circles is not None:
            # Convert the circle parameters to integers
            circles = np.uint16(np.around(circles))
            
            # Draw circles on the frame
            for circle in circles[0, :]:
                center = (circle[0], circle[1])
                radius = circle[2]
                # Draw the outer circle (black border)
                cv2.circle(color_image, center, radius, (0, 0, 0), 2)
                # Draw the center circle (black small circle inside)
                cv2.circle(color_image, center, int(radius / 5), (0, 0, 0), -1)
                # Draw a bounding box around the detected circle
                cv2.rectangle(color_image, (center[0] - radius, center[1] - radius),
                              (center[0] + radius, center[1] + radius), (0, 255, 0), 2)
        
        # Display the frame with detected circles
        cv2.imshow("Circle Detection", color_image)
        
        # Press 'q' to exit
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    # Release the pipeline
    pipeline.stop()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    detect_circle_from_video()
