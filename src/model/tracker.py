import cv2
from shapely.geometry import Point
import os

class MouseTracker:
    """
    Core CV Pipeline for tracking the mouse and detecting zone transitions.
    (The 'Model' in MVC)
    """
    def __init__(self, threshold_value=100, min_area=100):
        self.threshold_value = threshold_value
        self.min_area = min_area

    def check_zone(self, centroid, zones):
        """Checks which zone the centroid is currently inside."""
        if not centroid:
            return None
        point = Point(centroid[0], centroid[1])
        for label, polygon in zones.items():
            if polygon.contains(point):
                return label
        return None

    def process_video(self, video_path, zones, log_callback=None):
        """Processes a single video and returns the zone transition sequence."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return f"Error: Could not open {video_path}"
            
        tracking_sequence = ""
        current_zone = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            # Preprocessing & Segmentation
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            _, binary = cv2.threshold(blurred, self.threshold_value, 255, cv2.THRESH_BINARY_INV)
            
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            centroid = None
            if contours:
                largest_contour = max(contours, key=cv2.contourArea)
                if cv2.contourArea(largest_contour) > self.min_area:
                    M = cv2.moments(largest_contour)
                    if M["m00"] != 0:
                        cX = int(M["m10"] / M["m00"])
                        cY = int(M["m01"] / M["m00"])
                        centroid = (cX, cY)
            
            if centroid:
                detected_zone = self.check_zone(centroid, zones)
                if detected_zone and detected_zone != current_zone:
                    tracking_sequence += detected_zone
                    current_zone = detected_zone
                    if log_callback:
                        log_callback(f"[{os.path.basename(video_path)}] Transitioned to {detected_zone}")

        cap.release()
        return tracking_sequence