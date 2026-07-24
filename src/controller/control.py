import threading
import os
from tkinter import messagebox
from src.model.tracker import MouseTracker

class TrackerController:
    """
    Orchestrates communication between the UI and the CV pipeline.
    (The 'Controller' in MVC)
    """
    def __init__(self):
        self.view = None

    def set_view(self, view):
        self.view = view

    def run_batch_processing(self, video_paths, video_zones, thresh, area):
        if not video_paths:
            messagebox.showwarning("Warning", "No videos in queue.")
            return

        # Validation: Check if all videos have zones defined
        missing_zones = [os.path.basename(vp) for vp in video_paths if not video_zones.get(vp)]
        if missing_zones:
            msg = f"The following videos have no zones defined:\n\n{', '.join(missing_zones)}\n\nProcess anyway?"
            if not messagebox.askyesno("Missing Zones", msg):
                return

        # Disable UI elements during processing
        self.view.disable_ui_for_processing()
        self.view.log("\n--- STARTING BATCH PROCESSING ---")
        
        # Run in background thread to prevent UI freezing
        threading.Thread(target=self._process_queue, args=(video_paths, video_zones, thresh, area), daemon=True).start()

    def _process_queue(self, video_paths, video_zones, thresh, area):
        tracker = MouseTracker(threshold_value=thresh, min_area=area)
        results = {}

        try:
            for i, video_path in enumerate(video_paths):
                filename = os.path.basename(video_path)
                self.view.log(f"Processing {i+1}/{len(video_paths)}: {filename}")
                
                zones = video_zones.get(video_path, {})
                if not zones:
                    self.view.log(f"Skipping {filename}: No zones defined.")
                    continue
                    
                # Execute CV tracking
                sequence = tracker.process_video(video_path, zones, log_callback=self.view.log)
                results[video_path] = sequence
                self.view.log(f"-> FINAL SEQUENCE for {filename}: {sequence}\n")
                
            self.view.log("--- BATCH PROCESSING COMPLETE ---")
            
        except Exception as e:
            self.view.log(f"CRITICAL ERROR: {str(e)}")
            
        finally:
            # Re-enable UI (using thread-safe .after() method via the view)
            self.view.after(0, self.view.enable_ui_after_processing)