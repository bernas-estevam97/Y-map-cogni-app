import cv2
import numpy as np
from shapely.geometry import Point

class MouseTracker:
    """
    The computer vision pipeline for tracking a black mouse and logging zone entries.
    (The 'Model' in MVC)
    """
    def __init__(self):
        self.tracking_sequence = ""
        self.current_zone = None

    def process_video(self, video_path, tracking_params, log_callback=None, preview_callback=None, stop_event=None, frame_skip=0):
        self.tracking_sequence = ""
        self.current_zone = None
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            if log_callback: log_callback(f"Error: Could not open {video_path}")
            return self.tracking_sequence

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_count = 0
        
        if log_callback: log_callback(f"Starting tracking for {video_path}...")

        # Extract parameters from the dictionary
        zones = tracking_params.get('zones', {})
        threshold_value = tracking_params.get('thresh', 50) 
        min_area = tracking_params.get('min_area', 1100)
        # We now use the user-defined max_area, with a safe fallback of infinity
        max_area = tracking_params.get('max_area', float('inf')) 

        while True:
            # Check for force stop signal
            if stop_event and stop_event.is_set():
                if log_callback: log_callback("Processing forcibly stopped by user.")
                break

            ret, frame = cap.read()
            if not ret:
                break
                
            frame_count += 1
            
            # Apply Frame Skip for speedup
            if frame_skip > 0 and frame_count % (frame_skip + 1) != 0:
                continue

            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            
            # Inverse Binary Threshold: Black objects become white (255)
            _, thresh_img = cv2.threshold(blurred, threshold_value, 255, cv2.THRESH_BINARY_INV)

            # Find contours
            contours, _ = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            preview_frame = None
            if preview_callback:
                preview_frame = frame.copy()
                # Draw all detected contours in blue for debugging thresholding
                cv2.drawContours(preview_frame, contours, -1, (255, 0, 0), 1)

            # Filter out noise (too small) and large shadows/walls (too big) using user parameters
            valid_contours = [c for c in contours if min_area < cv2.contourArea(c) < max_area]

            if valid_contours:
                # Assume the largest valid contour is the mouse
                largest_contour = max(valid_contours, key=cv2.contourArea)
                M = cv2.moments(largest_contour)
                
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])
                    
                    mouse_point = Point(cX, cY)
                    
                    if preview_callback:
                        # Draw the accepted centroid in red
                        cv2.circle(preview_frame, (cX, cY), 5, (0, 0, 255), -1)

                    # Flag to track if the mouse is currently inside any defined polygon
                    in_any_zone = False

                    # Check which zone the mouse is in using intersects
                    for label, polygon in zones.items():
                        if polygon.intersects(mouse_point):
                            in_any_zone = True
                            if self.current_zone != label:
                                self.tracking_sequence += label
                                self.current_zone = label
                                if log_callback: log_callback(f"Frame {frame_count}: Entered Zone {label}")
                            break # Found the zone, no need to check others
                    
                    # If the mouse didn't intersect with any zone, it has left into empty space.
                    # We reset current_zone to None so it can re-trigger when entering the same zone later.
                    if not in_any_zone:
                        if self.current_zone is not None:
                            if log_callback: log_callback(f"Frame {frame_count}: Left Zone {self.current_zone}")
                            self.current_zone = None

            if preview_callback and preview_frame is not None:
                preview_callback(preview_frame, frame_count, total_frames)

        cap.release()
        return self.tracking_sequence