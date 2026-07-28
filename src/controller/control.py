import threading
import os
from tkinter import messagebox, filedialog
from src.model.tracker import MouseTracker

class TrackerController:
    """
    Orchestrates communication between the UI and the CV pipeline.
    (The 'Controller' in MVC)
    """
    def __init__(self):
        self.view = None
        self.stop_event = threading.Event()
        self.latest_results = {}

    def set_view(self, view):
        self.view = view

    def run_batch_processing(self, video_paths, video_zones, thresh, min_area, max_area, frame_skip):
        if not video_paths:
            self.view.log("No videos in queue to process.")
            return
            
        if min_area >= max_area:
            messagebox.showwarning("Warning", "Minimum Area must be strictly less than Maximum Area.")
            return

        # Reset the stop event before starting
        self.stop_event.clear()
        self.latest_results.clear()

        # Disable UI elements during processing
        self.view.disable_ui_for_processing()
        self.view.log("\n--- Starting Batch Processing ---")

        # Run in a background thread so UI doesn't freeze
        thread = threading.Thread(
            target=self._process_queue, 
            args=(video_paths, video_zones, thresh, min_area, max_area, frame_skip)
        )
        thread.daemon = True
        thread.start()

    def _process_queue(self, video_paths, video_zones, thresh, min_area, max_area, frame_skip):
        tracker = MouseTracker()
        results = {}
        show_preview = self.view.preview_checkbox.get()

        try:
            for video_path in video_paths:
                if self.stop_event.is_set():
                    break

                filename = os.path.basename(video_path)
                zones = video_zones.get(video_path, {})
                
                if not zones:
                    self.view.log(f"Skipping {filename}: No zones defined.")
                    continue

                self.view.log(f"Processing {filename}...")
                
                # Bundle the parameters for the tracker
                tracking_params = {
                    'zones': zones,
                    'thresh': thresh,
                    'min_area': min_area,
                    'max_area': max_area
                }

                # Define a preview callback if the user wants live video
                preview_cb = None
                if show_preview:
                    def update_preview(frame, current_f, total_f):
                        # Send back to UI safely using .after()
                        self.view.after(0, self.view.update_live_preview, frame, zones, current_f, total_f)
                    preview_cb = update_preview

                # Execute CV tracking
                sequence = tracker.process_video(
                    video_path, 
                    tracking_params, 
                    log_callback=self.view.log,
                    preview_callback=preview_cb,
                    stop_event=self.stop_event,
                    frame_skip=frame_skip
                )
                
                if not self.stop_event.is_set():
                    results[video_path] = sequence
                    self.latest_results[video_path] = sequence
                    self.view.log(f"-> FINAL SEQUENCE for {filename}: {sequence}\n")
                
            if self.stop_event.is_set():
                self.view.log("--- Processing Aborted ---")
            else:
                self.view.log("--- Batch Processing Complete ---")

        except Exception as e:
            self.view.log(f"An error occurred: {str(e)}")
            
        finally:
            # Re-enable UI (using thread-safe .after() method via the view)
            self.view.after(0, self.view.enable_ui_after_processing)
            # Restore the canvas to the reference frame if preview altered it
            self.view.after(0, self.view.redraw_canvas)
            # Enable Export button if there are results
            if self.latest_results:
                self.view.after(0, self.view.enable_export_btn)

    def cancel_processing(self):
        self.stop_event.set()
        self.view.log("Stop requested... waiting for current frame to finish.")

    def export_data(self):
        if not self.latest_results:
            messagebox.showwarning("Warning", "No results to export yet.")
            return
            
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("Text files", "*.txt")],
            title="Save Tracking Results"
        )
        
        if filepath:
            try:
                with open(filepath, 'w') as f:
                    f.write("Video_File,Tracking_Sequence\n")
                    for vid_path, sequence in self.latest_results.items():
                        filename = os.path.basename(vid_path)
                        f.write(f"{filename},{sequence}\n")
                self.view.log(f"Successfully exported results to {os.path.basename(filepath)}")
                messagebox.showinfo("Export Successful", f"Results saved to:\n{filepath}")
            except Exception as e:
                self.view.log(f"Error exporting data: {e}")
                messagebox.showerror("Export Error", f"Failed to save file:\n{e}")