import cv2
import numpy as np
from shapely.geometry import Point, Polygon
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import threading
import os

class MouseTracker:
    """
    Core CV Pipeline for tracking the mouse and detecting zone transitions.
    """
    def __init__(self, threshold_value=100, min_area=100):
        self.threshold_value = threshold_value
        self.min_area = min_area

    def check_zone(self, centroid, zones):
        if not centroid:
            return None
        point = Point(centroid[0], centroid[1])
        for label, polygon in zones.items():
            if polygon.contains(point):
                return label
        return None

    def process_video(self, video_path, zones, log_callback=None):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return f"Error: Could not open {video_path}"
            
        tracking_sequence = ""
        current_zone = None
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
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

class TrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Animal Zone Tracker")
        self.geometry("1100x700")
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # State Variables
        self.video_paths = []
        self.current_video = None
        self.video_zones = {} # Dict mapping video_path -> { 'Zone A': Polygon, ... }
        self.current_drawing_points = [] # Points for the polygon currently being drawn
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.canvas_width = 640
        self.canvas_height = 480
        self.current_frame_img = None

        self.setup_ui()

    def setup_ui(self):
        # Configure Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Left Sidebar: Video Queue ---
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Video Queue", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_video_btn = ctk.CTkButton(self.sidebar_frame, text="Add Video(s)", command=self.add_videos)
        self.add_video_btn.grid(row=1, column=0, padx=20, pady=10)

        # Video Listbox (using standard tk Listbox inside a CTkFrame for simplicity)
        self.listbox_frame = ctk.CTkFrame(self.sidebar_frame)
        self.listbox_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.video_listbox = tk.Listbox(self.listbox_frame, bg="#2b2b2b", fg="white", selectbackground="#1f538d", highlightthickness=0, borderwidth=0)
        self.video_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.video_listbox.bind("<<ListboxSelect>>", self.on_video_select)

        self.remove_video_btn = ctk.CTkButton(self.sidebar_frame, text="Remove Selected", command=self.remove_video, fg_color="#c62828", hover_color="#b71c1c")
        self.remove_video_btn.grid(row=3, column=0, padx=20, pady=20)

        # --- Center: Canvas Area ---
        self.center_frame = ctk.CTkFrame(self)
        self.center_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.center_frame.grid_rowconfigure(0, weight=1)
        self.center_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.center_frame, width=self.canvas_width, height=self.canvas_height, bg="#1e1e1e", highlightthickness=0)
        self.canvas.grid(row=0, column=0, pady=10)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Instruction Label
        self.instruction_label = ctk.CTkLabel(self.center_frame, text="Select a video to view the reference frame and click on the image to draw zones.")
        self.instruction_label.grid(row=1, column=0, pady=5)

        # --- Right Sidebar: Config & Actions ---
        self.right_frame = ctk.CTkFrame(self, width=250)
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(self.right_frame, text="Zone Tools", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20,10))
        
        self.save_zone_btn = ctk.CTkButton(self.right_frame, text="Save Current Polygon", command=self.save_zone)
        self.save_zone_btn.pack(pady=5, padx=20)
        
        self.clear_zones_btn = ctk.CTkButton(self.right_frame, text="Clear Zones for Video", command=self.clear_video_zones)
        self.clear_zones_btn.pack(pady=5, padx=20)

        self.copy_zones_btn = ctk.CTkButton(self.right_frame, text="Copy Zones to All Videos", command=self.copy_zones_to_all, fg_color="#2e7d32", hover_color="#1b5e20")
        self.copy_zones_btn.pack(pady=(20, 5), padx=20)

        ctk.CTkLabel(self.right_frame, text="CV Parameters", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(30,10))
        
        ctk.CTkLabel(self.right_frame, text="Darkness Threshold (0-255)").pack()
        self.thresh_slider = ctk.CTkSlider(self.right_frame, from_=0, to=255, number_of_steps=255)
        self.thresh_slider.set(100)
        self.thresh_slider.pack(pady=5, padx=20)

        ctk.CTkLabel(self.right_frame, text="Minimum Area (noise filter)").pack()
        self.area_slider = ctk.CTkSlider(self.right_frame, from_=10, to=1000, number_of_steps=99)
        self.area_slider.set(100)
        self.area_slider.pack(pady=5, padx=20)

        self.run_btn = ctk.CTkButton(self.right_frame, text="START PROCESSING", command=self.start_processing_thread, height=40, font=ctk.CTkFont(weight="bold"))
        self.run_btn.pack(pady=(40, 10), padx=20, side="bottom")

        # --- Bottom: Log Area ---
        self.log_textbox = ctk.CTkTextbox(self, height=150)
        self.log_textbox.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.log_textbox.insert("0.0", "System Initialized. Awaiting videos...\n")
        self.log_textbox.configure(state="disabled")

    def log(self, message):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def add_videos(self):
        files = filedialog.askopenfilenames(title="Select Videos", filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv")])
        for f in files:
            if f not in self.video_paths:
                self.video_paths.append(f)
                self.video_zones[f] = {} # Initialize empty zones for new video
                filename = os.path.basename(f)
                self.video_listbox.insert(tk.END, filename)

    def remove_video(self):
        selection = self.video_listbox.curselection()
        if selection:
            idx = selection[0]
            vid_path = self.video_paths[idx]
            self.video_listbox.delete(idx)
            self.video_paths.pop(idx)
            if vid_path in self.video_zones:
                del self.video_zones[vid_path]
            
            self.canvas.delete("all")
            self.current_video = None
            self.current_drawing_points = []

    def on_video_select(self, event):
        selection = self.video_listbox.curselection()
        if not selection:
            return
            
        idx = selection[0]
        self.current_video = self.video_paths[idx]
        self.current_drawing_points = []
        self.load_reference_frame(self.current_video)
        self.redraw_canvas()

    def load_reference_frame(self, video_path):
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        cap.release()
        
        if not ret:
            self.log(f"Error: Could not read frame from {os.path.basename(video_path)}")
            return
            
        # Store original dimensions for scaling
        orig_h, orig_w = frame.shape[:2]
        
        # Convert BGR to RGB for PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        # Resize to fit canvas
        img_resized = img.resize((self.canvas_width, self.canvas_height), Image.Resampling.LANCZOS)
        self.current_frame_img = ImageTk.PhotoImage(img_resized)
        
        # Calculate scaling factors to map canvas clicks back to original video resolution
        self.scale_x = orig_w / self.canvas_width
        self.scale_y = orig_h / self.canvas_height

    def on_canvas_click(self, event):
        if not self.current_video:
            messagebox.showwarning("Warning", "Please select a video from the queue first.")
            return

        # Store canvas coordinates
        cx, cy = event.x, event.y
        self.current_drawing_points.append((cx, cy))
        self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("all")
        
        if self.current_frame_img:
            self.canvas.create_image(0, 0, anchor="nw", image=self.current_frame_img)

        # 1. Draw Saved Zones for this video
        if self.current_video in self.video_zones:
            for label, polygon in self.video_zones[self.current_video].items():
                # Convert real scaled points back to canvas coordinates for display
                canvas_pts = [(int(x / self.scale_x), int(y / self.scale_y)) for x, y in polygon.exterior.coords]
                # Flatten list of tuples for Tkinter create_polygon
                flat_pts = [coord for pt in canvas_pts for coord in pt]
                if len(flat_pts) >= 6: # Need at least 3 points (6 coords)
                    self.canvas.create_polygon(flat_pts, outline="#00ff00", fill="", width=2)
                    self.canvas.create_text(canvas_pts[0][0], canvas_pts[0][1] - 10, text=label, fill="#00ff00", font=("Arial", 12, "bold"))

        # 2. Draw Currently In-Progress Polygon
        for pt in self.current_drawing_points:
            self.canvas.create_oval(pt[0]-3, pt[1]-3, pt[0]+3, pt[1]+3, fill="red", outline="red")
            
        if len(self.current_drawing_points) > 1:
            flat_pts = [coord for pt in self.current_drawing_points for coord in pt]
            self.canvas.create_line(flat_pts, fill="red", width=2)

    def save_zone(self):
        if len(self.current_drawing_points) < 3:
            messagebox.showwarning("Warning", "A zone must have at least 3 points.")
            return
            
        dialog = ctk.CTkInputDialog(text="Enter zone label (e.g., A, B, C):", title="Save Zone")
        label = dialog.get_input()
        
        if label:
            # Convert canvas points to real video dimensions using the scale factor
            real_points = [(int(x * self.scale_x), int(y * self.scale_y)) for x, y in self.current_drawing_points]
            polygon = Polygon(real_points)
            
            self.video_zones[self.current_video][label] = polygon
            self.log(f"Saved Zone '{label}' for {os.path.basename(self.current_video)}")
            
        self.current_drawing_points = []
        self.redraw_canvas()

    def clear_video_zones(self):
        if self.current_video:
            self.video_zones[self.current_video] = {}
            self.current_drawing_points = []
            self.redraw_canvas()
            self.log(f"Cleared zones for {os.path.basename(self.current_video)}")

    def copy_zones_to_all(self):
        if not self.current_video or not self.video_zones[self.current_video]:
            messagebox.showwarning("Warning", "No zones defined in the current video to copy.")
            return
            
        zones_to_copy = self.video_zones[self.current_video]
        count = 0
        for vp in self.video_paths:
            if vp != self.current_video:
                # Copy the dictionary of Shapely Polygons
                self.video_zones[vp] = zones_to_copy.copy()
                count += 1
                
        self.log(f"Copied zones from {os.path.basename(self.current_video)} to {count} other videos.")
        messagebox.showinfo("Success", f"Zones copied to {count} videos.")

    def start_processing_thread(self):
        if not self.video_paths:
            messagebox.showwarning("Warning", "No videos in queue.")
            return
            
        # Validation: Check if all videos have zones defined
        missing_zones = [os.path.basename(vp) for vp in self.video_paths if not self.video_zones.get(vp)]
        if missing_zones:
            msg = f"The following videos have no zones defined:\n\n{', '.join(missing_zones)}\n\nProcess anyway?"
            if not messagebox.askyesno("Missing Zones", msg):
                return

        # Disable UI elements during processing
        self.run_btn.configure(state="disabled", text="PROCESSING...")
        self.add_video_btn.configure(state="disabled")
        self.copy_zones_btn.configure(state="disabled")
        
        self.log("\n--- STARTING BATCH PROCESSING ---")
        
        # Run in background thread to prevent UI freezing
        threading.Thread(target=self._process_queue, daemon=True).start()

    def _process_queue(self):
        # Fetch current slider parameters
        thresh = int(self.thresh_slider.get())
        area = int(self.area_slider.get())
        
        tracker = MouseTracker(threshold_value=thresh, min_area=area)
        results = {}

        try:
            for i, video_path in enumerate(self.video_paths):
                filename = os.path.basename(video_path)
                self.log(f"Processing {i+1}/{len(self.video_paths)}: {filename}")
                
                zones = self.video_zones.get(video_path, {})
                if not zones:
                    self.log(f"Skipping {filename}: No zones defined.")
                    continue
                    
                # The log_callback allows the tracker to pipe text directly into our UI log
                sequence = tracker.process_video(video_path, zones, log_callback=self.log)
                results[video_path] = sequence
                self.log(f"-> FINAL SEQUENCE for {filename}: {sequence}\n")
                
            self.log("--- BATCH PROCESSING COMPLETE ---")
            
        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            
        finally:
            # Re-enable UI (Must use after() to interact with Tkinter from a thread, 
            # though CustomTkinter is sometimes forgiving, it's safer to use after)
            self.after(0, self._reset_run_button)

    def _reset_run_button(self):
        self.run_btn.configure(state="normal", text="START PROCESSING")
        self.add_video_btn.configure(state="normal")
        self.copy_zones_btn.configure(state="normal")

if __name__ == "__main__":
    app = TrackerApp()
    app.mainloop()