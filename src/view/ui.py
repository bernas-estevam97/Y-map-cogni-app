import sys
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import os
import numpy as np
from shapely.geometry import Polygon
import ctypes

# Force Windows to show the custom icon on the taskbar instead of the Python logo
try:
    my_app_id = 'bernardo_estevam.y_maze_animal_tracker.version_1' # Arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(my_app_id)
except Exception:
    pass 


def resource_path(relative_path):
    """ Get the absolute path to a resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    return os.path.join(base_path, relative_path)


class ToolTip:
    """
    A simple hover tooltip for CustomTkinter widgets using standard tkinter.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        self.tooltip_window.attributes("-topmost", True)
        
        # Dynamically set tooltip colors based on current theme
        mode = ctk.get_appearance_mode()
        bg_color = "#333333" if mode == "Dark" else "#F9FAFB"
        fg_color = "white" if mode == "Dark" else "#111827"
        border_color = "white" if mode == "Dark" else "#D1D5DB"

        label = tk.Label(self.tooltip_window, text=self.text, justify="left",
                         background=bg_color, foreground=fg_color, relief="solid", borderwidth=1,
                         highlightbackground=border_color, font=("Arial", 10), padx=8, pady=4)
        label.pack()

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class TrackerView(ctk.CTk):
    """
    The graphical user interface for the application.
    (The 'View' in MVC)
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller

        self.title("Y-Maze - Animal Tracker")
        self.geometry("1300x950")
        
        self.current_theme = "Dark"
        ctk.set_appearance_mode(self.current_theme)
        ctk.set_default_color_theme("blue")

        self.video_paths = []
        self.current_video = None
        self.video_zones = {} 
        self.current_drawing_points = []
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.canvas_width = 840
        self.canvas_height = 680
        self.current_frame_img = None
        self.total_frames = 0
        self.video_capture = None

        try:
            icon_path = resource_path("img/y-maze.ico")
            self.iconbitmap(icon_path)
        except Exception as e:
            print(f"Could not load icon from {icon_path}. Error: {e}")

        self.setup_ui()
        self.apply_theme_colors()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Left Sidebar
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(2, weight=1)
        self.sidebar_frame.grid_rowconfigure(4, weight=1) # Push theme toggle to bottom

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Video Queue", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_video_btn = ctk.CTkButton(self.sidebar_frame, text="Add Video(s)", command=self.add_videos)
        self.add_video_btn.grid(row=1, column=0, padx=20, pady=10)

        self.listbox_frame = ctk.CTkFrame(self.sidebar_frame)
        self.listbox_frame.grid(row=2, column=0, padx=20, pady=10, sticky="nsew")
        self.video_listbox = tk.Listbox(self.listbox_frame, highlightthickness=0, borderwidth=0, width=35)
        self.video_listbox.pack(fill="both", expand=True, padx=5, pady=5)
        self.video_listbox.bind("<<ListboxSelect>>", self.on_video_select)

        self.remove_video_btn = ctk.CTkButton(self.sidebar_frame, text="Remove Selected", command=self.remove_video)
        self.remove_video_btn.grid(row=3, column=0, padx=20, pady=20)

        # Theme Toggle Switch (Placed at the bottom of the sidebar)
        self.theme_switch_var = ctk.StringVar(value="Dark")
        self.theme_switch = ctk.CTkSwitch(
            self.sidebar_frame, 
            text="Dark Mode", 
            command=self.toggle_theme,
            variable=self.theme_switch_var,
            onvalue="Dark",
            offvalue="Light"
        )
        self.theme_switch.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="s")

        # Center Canvas Area
        self.center_frame = ctk.CTkFrame(self)
        self.center_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.center_frame.grid_rowconfigure(0, weight=1)
        self.center_frame.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.center_frame, width=self.canvas_width, height=self.canvas_height, highlightthickness=0)
        self.canvas.grid(row=0, column=0, pady=10)
        self.canvas.bind("<Button-1>", self.on_canvas_click)

        # Frame Seeker
        self.seeker_frame = ctk.CTkFrame(self.center_frame, fg_color="transparent")
        self.seeker_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 10))
        self.seeker_frame.grid_columnconfigure(1, weight=1)
        
        self.frame_label = ctk.CTkLabel(self.seeker_frame, text="Frame: 0 / 0", width=100)
        self.frame_label.grid(row=0, column=0, padx=5)
        
        self.frame_slider = ctk.CTkSlider(self.seeker_frame, from_=0, to=100, command=self.on_frame_slider_move, state="disabled")
        self.frame_slider.grid(row=0, column=1, sticky="ew", padx=10)
        self.frame_slider.set(0)

        self.instruction_label = ctk.CTkLabel(self.center_frame, text="Select a video, use slider to find frame, click image to draw zones.")
        self.instruction_label.grid(row=2, column=0, pady=5)

        # Right Sidebar Config
        self.right_frame = ctk.CTkFrame(self, width=300)
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

        ctk.CTkLabel(self.right_frame, text="Zone Tools", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,5))
        
        self.save_zone_btn = ctk.CTkButton(self.right_frame, text="Save Current Polygon", command=self.save_zone)
        self.save_zone_btn.pack(pady=5, padx=20)
        
        self.remove_zone_btn = ctk.CTkButton(self.right_frame, text="Remove Specific Zone", command=self.remove_specific_zone)
        self.remove_zone_btn.pack(pady=5, padx=20)
        
        self.clear_zones_btn = ctk.CTkButton(self.right_frame, text="Clear Zones for Video", command=self.clear_video_zones)
        self.clear_zones_btn.pack(pady=5, padx=20)

        self.copy_zones_btn = ctk.CTkButton(self.right_frame, text="Copy Zones to All", command=self.copy_zones_to_all)
        self.copy_zones_btn.pack(pady=(15, 5), padx=20)

        ctk.CTkLabel(self.right_frame, text="CV Parameters", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,5))

        # Darkness Threshold
        self.darkness_label = ctk.CTkLabel(self.right_frame, text="Darkness (0-255) ⓘ", cursor="hand2")
        self.darkness_label.pack(anchor="w", padx=20)
        ToolTip(self.darkness_label, "Increase to include lighter pixels (detected shape grows).\nDecrease to require strictly darker pixels.")
        
        self.thresh_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.thresh_frame.pack(pady=(0, 5), padx=20, fill="x")
        self.thresh_slider = ctk.CTkSlider(self.thresh_frame, from_=0, to=255, number_of_steps=255, command=self.sync_thresh_entry)
        self.thresh_slider.set(50)
        self.thresh_slider.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.thresh_entry = ctk.CTkEntry(self.thresh_frame, width=50)
        self.thresh_entry.insert(0, "50")
        self.thresh_entry.pack(side="right")
        self.thresh_entry.bind("<Return>", self.sync_thresh_slider)
        self.thresh_entry.bind("<FocusOut>", self.sync_thresh_slider)

        # Minimum Area
        self.min_area_label = ctk.CTkLabel(self.right_frame, text="Min Area ⓘ", cursor="hand2")
        self.min_area_label.pack(anchor="w", padx=20)
        ToolTip(self.min_area_label, "Increase to ignore larger bits of camera noise or dirt.\nDecrease to detect smaller objects.")
        
        self.min_area_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.min_area_frame.pack(pady=(0, 5), padx=20, fill="x")
        self.min_area_slider = ctk.CTkSlider(self.min_area_frame, from_=10, to=2000, number_of_steps=100, command=self.sync_min_area_entry)
        self.min_area_slider.set(1150)
        self.min_area_slider.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.min_area_entry = ctk.CTkEntry(self.min_area_frame, width=50)
        self.min_area_entry.insert(0, "1150")
        self.min_area_entry.pack(side="right")
        self.min_area_entry.bind("<Return>", self.sync_min_area_slider)
        self.min_area_entry.bind("<FocusOut>", self.sync_min_area_slider)

        # Maximum Area
        self.max_area_label = ctk.CTkLabel(self.right_frame, text="Max Area ⓘ", cursor="hand2")
        self.max_area_label.pack(anchor="w", padx=20)
        ToolTip(self.max_area_label, "Increase to allow tracking of larger shapes.\nDecrease to filter out large shadows or cage walls.")
        
        self.max_area_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.max_area_frame.pack(pady=(0, 5), padx=20, fill="x")
        self.max_area_slider = ctk.CTkSlider(self.max_area_frame, from_=100, to=5000, number_of_steps=100, command=self.sync_max_area_entry)
        self.max_area_slider.set(2500)
        self.max_area_slider.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.max_area_entry = ctk.CTkEntry(self.max_area_frame, width=50)
        self.max_area_entry.insert(0, "2500")
        self.max_area_entry.pack(side="right")
        self.max_area_entry.bind("<Return>", self.sync_max_area_slider)
        self.max_area_entry.bind("<FocusOut>", self.sync_max_area_slider)

        # Frame Skip
        ctk.CTkLabel(self.right_frame, text="Frame Skip (Speedup):").pack(anchor="w", padx=20)
        self.skip_frame = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.skip_frame.pack(pady=(0, 5), padx=20, fill="x")
        self.skip_slider = ctk.CTkSlider(self.skip_frame, from_=0, to=10, number_of_steps=10, command=self.sync_skip_entry)
        self.skip_slider.set(0) 
        self.skip_slider.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.skip_entry = ctk.CTkEntry(self.skip_frame, width=50)
        self.skip_entry.insert(0, "0")
        self.skip_entry.pack(side="right")
        self.skip_entry.bind("<Return>", self.sync_skip_slider)
        self.skip_entry.bind("<FocusOut>", self.sync_skip_slider)
        
        self.preview_checkbox = ctk.CTkCheckBox(self.right_frame, text="Show Live Preview")
        self.preview_checkbox.pack(pady=(10, 5), padx=20)

        # Execution Buttons
        self.export_btn = ctk.CTkButton(self.right_frame, text="EXPORT DATA", command=self.export_data, state="disabled")
        self.export_btn.pack(pady=(15, 5), padx=20, side="bottom")

        self.stop_btn = ctk.CTkButton(self.right_frame, text="FORCE STOP", command=self.cancel_processing, state="disabled")
        self.stop_btn.pack(pady=(5, 5), padx=20, side="bottom")

        self.run_btn = ctk.CTkButton(self.right_frame, text="START PROCESSING", command=self.start_processing, height=40, font=ctk.CTkFont(weight="bold"))
        self.run_btn.pack(pady=(10, 5), padx=20, side="bottom")

        # Bottom Log Area
        self.log_textbox = ctk.CTkTextbox(self, height=120)
        self.log_textbox.grid(row=1, column=1, columnspan=2, padx=10, pady=10, sticky="nsew")
        self.log_textbox.insert("0.0", "System Initialized. Awaiting videos...\n")
        self.log_textbox.configure(state="disabled")

    # --- Theme Management ---
    def toggle_theme(self):
        self.current_theme = self.theme_switch_var.get()
        self.apply_theme_colors()

    def apply_theme_colors(self):
        """ Dynamically updates Standard Tkinter widgets and specific CustomTkinter accents. """
        ctk.set_appearance_mode(self.current_theme)

        if self.current_theme == "Dark":
            self.canvas.configure(bg="#1E1E1E")
            self.video_listbox.configure(bg="#2B2B2B", fg="white", selectbackground="#1F538D")
            
            # Original Dark Theme Colors
            self.remove_video_btn.configure(fg_color="#C62828", hover_color="#B71C1C")
            self.stop_btn.configure(fg_color="#C62828", hover_color="#B71C1C")
            self.copy_zones_btn.configure(fg_color="#2E7D32", hover_color="#1B5E20")
            self.export_btn.configure(fg_color="#1565C0", hover_color="#0D47A1")
            self.theme_switch.configure(text="Dark Mode")
        else:
            # Industry Standard Light Theme Colors (Tailwind Inspired)
            self.canvas.configure(bg="#E5E7EB") # Gray 200
            self.video_listbox.configure(bg="#FFFFFF", fg="#111827", selectbackground="#3B82F6") # White bg, Gray 900 fg
            
            # Standard Web Semantic Colors
            self.remove_video_btn.configure(fg_color="#EF4444", hover_color="#DC2626") # Red
            self.stop_btn.configure(fg_color="#EF4444", hover_color="#DC2626") # Red
            self.copy_zones_btn.configure(fg_color="#10B981", hover_color="#059669") # Emerald
            self.export_btn.configure(fg_color="#3B82F6", hover_color="#2563EB") # Blue
            self.theme_switch.configure(text="Light Mode")

    # --- Sync Methods for Input/Sliders ---
    def sync_thresh_entry(self, value):
        self.thresh_entry.delete(0, "end")
        self.thresh_entry.insert(0, str(int(value)))

    def sync_thresh_slider(self, event=None):
        try:
            val = int(self.thresh_entry.get())
            val = max(0, min(255, val))
            self.thresh_slider.set(val)
            self.sync_thresh_entry(val)
        except ValueError:
            self.sync_thresh_entry(self.thresh_slider.get())

    def sync_min_area_entry(self, value):
        self.min_area_entry.delete(0, "end")
        self.min_area_entry.insert(0, str(int(value)))

    def sync_min_area_slider(self, event=None):
        try:
            val = int(self.min_area_entry.get())
            val = max(10, min(2000, val))
            self.min_area_slider.set(val)
            self.sync_min_area_entry(val)
        except ValueError:
            self.sync_min_area_entry(self.min_area_slider.get())

    def sync_max_area_entry(self, value):
        self.max_area_entry.delete(0, "end")
        self.max_area_entry.insert(0, str(int(value)))

    def sync_max_area_slider(self, event=None):
        try:
            val = int(self.max_area_entry.get())
            val = max(100, min(5000, val))
            self.max_area_slider.set(val)
            self.sync_max_area_entry(val)
        except ValueError:
            self.sync_max_area_entry(self.max_area_slider.get())

    def sync_skip_entry(self, value):
        self.skip_entry.delete(0, "end")
        self.skip_entry.insert(0, str(int(value)))

    def sync_skip_slider(self, event=None):
        try:
            val = int(self.skip_entry.get())
            val = max(0, min(10, val))
            self.skip_slider.set(val)
            self.sync_skip_entry(val)
        except ValueError:
            self.sync_skip_entry(self.skip_slider.get())

    # --- Core UI Methods ---
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
                self.video_zones[f] = {}
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
            if self.video_capture:
                self.video_capture.release()
                self.video_capture = None
            self.frame_slider.configure(state="disabled")

    def on_video_select(self, event):
        selection = self.video_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        self.current_video = self.video_paths[idx]
        self.current_drawing_points = []
        
        if self.video_capture:
            self.video_capture.release()
            
        self.video_capture = cv2.VideoCapture(self.current_video)
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if self.total_frames > 0:
            self.frame_slider.configure(state="normal", to=self.total_frames - 1)
            self.frame_slider.set(0)
            self.update_frame_label(0)
            self.load_frame_at_index(0)

    def on_frame_slider_move(self, value):
        frame_idx = int(value)
        self.update_frame_label(frame_idx)
        self.load_frame_at_index(frame_idx)

    def update_frame_label(self, current_frame):
        self.frame_label.configure(text=f"Frame: {current_frame} / {self.total_frames}")

    def load_frame_at_index(self, frame_idx):
        if not self.video_capture or not self.video_capture.isOpened():
            return
            
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = self.video_capture.read()
        
        if not ret:
            return
            
        orig_h, orig_w = frame.shape[:2]
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        
        img_resized = img.resize((self.canvas_width, self.canvas_height), Image.Resampling.LANCZOS)
        self.current_frame_img = ImageTk.PhotoImage(img_resized)
        
        self.scale_x = orig_w / self.canvas_width
        self.scale_y = orig_h / self.canvas_height
        
        self.redraw_canvas()

    def update_live_preview(self, cv_frame, zones, current_f, total_f):
        for label, polygon in zones.items():
            pts = np.array(polygon.exterior.coords, np.int32)
            pts = pts.reshape((-1, 1, 2))
            cv2.polylines(cv_frame, [pts], True, (0, 255, 0), 2)

        frame_rgb = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        img_resized = img.resize((self.canvas_width, self.canvas_height), Image.Resampling.LANCZOS)
        self.current_frame_img = ImageTk.PhotoImage(img_resized)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.current_frame_img)
        self.update_frame_label(current_f)

    def on_canvas_click(self, event):
        if not self.current_video:
            messagebox.showwarning("Warning", "Please select a video from the queue first.")
            return
        cx, cy = event.x, event.y
        self.current_drawing_points.append((cx, cy))
        self.redraw_canvas()

    def redraw_canvas(self):
        self.canvas.delete("all")
        if self.current_frame_img:
            self.canvas.create_image(0, 0, anchor="nw", image=self.current_frame_img)

        if self.current_video in self.video_zones:
            for label, polygon in self.video_zones[self.current_video].items():
                canvas_pts = [(int(x / self.scale_x), int(y / self.scale_y)) for x, y in polygon.exterior.coords]
                flat_pts = [coord for pt in canvas_pts for coord in pt]
                if len(flat_pts) >= 6:
                    self.canvas.create_polygon(flat_pts, outline="#00ff00", fill="", width=2)
                    self.canvas.create_text(canvas_pts[0][0], canvas_pts[0][1] - 10, text=label, fill="#00ff00", font=("Arial", 12, "bold"))

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
            real_points = [(int(x * self.scale_x), int(y * self.scale_y)) for x, y in self.current_drawing_points]
            polygon = Polygon(real_points)
            self.video_zones[self.current_video][label] = polygon
            self.log(f"Saved Zone '{label}' for {os.path.basename(self.current_video)}")
            
        self.current_drawing_points = []
        self.redraw_canvas()

    def remove_specific_zone(self):
        if not self.current_video or not self.video_zones.get(self.current_video):
            messagebox.showwarning("Warning", "No zones available to remove for this video.")
            return
            
        dialog = ctk.CTkInputDialog(text="Enter zone label to remove (e.g., A, B):", title="Remove Zone")
        label = dialog.get_input()
        
        if label:
            if label in self.video_zones[self.current_video]:
                del self.video_zones[self.current_video][label]
                self.log(f"Removed Zone '{label}' for {os.path.basename(self.current_video)}")
                self.redraw_canvas()
            else:
                messagebox.showinfo("Not Found", f"Zone '{label}' does not exist.")

    def clear_video_zones(self):
        if self.current_video:
            self.video_zones[self.current_video] = {}
            self.current_drawing_points = []
            self.redraw_canvas()
            self.log(f"Cleared zones for {os.path.basename(self.current_video)}")

    def copy_zones_to_all(self):
        if not self.current_video or not self.video_zones[self.current_video]:
            messagebox.showwarning("Warning", "No zones to copy.")
            return
            
        zones_to_copy = self.video_zones[self.current_video]
        count = 0
        for vp in self.video_paths:
            if vp != self.current_video:
                self.video_zones[vp] = zones_to_copy.copy()
                count += 1
                
        self.log(f"Copied zones from {os.path.basename(self.current_video)} to {count} other videos.")
        messagebox.showinfo("Success", f"Zones copied to {count} videos.")

    def start_processing(self):
        thresh = int(self.thresh_entry.get())
        min_area = int(self.min_area_entry.get())
        max_area = int(self.max_area_entry.get())
        skip = int(self.skip_entry.get())
        
        self.controller.run_batch_processing(
            self.video_paths, 
            self.video_zones, 
            thresh, 
            min_area,
            max_area,
            skip
        )

    def cancel_processing(self):
        self.controller.cancel_processing()

    def export_data(self):
        self.controller.export_data()

    def enable_export_btn(self):
        self.export_btn.configure(state="normal")

    def disable_ui_for_processing(self):
        self.run_btn.configure(state="disabled", text="PROCESSING...")
        self.stop_btn.configure(state="normal", text="FORCE STOP")
        self.export_btn.configure(state="disabled")
        self.add_video_btn.configure(state="disabled")
        self.copy_zones_btn.configure(state="disabled")
        self.frame_slider.configure(state="disabled")

    def enable_ui_after_processing(self):
        self.run_btn.configure(state="normal", text="START PROCESSING")
        self.stop_btn.configure(state="disabled", text="FORCE STOP")
        self.add_video_btn.configure(state="normal")
        self.copy_zones_btn.configure(state="normal")
        if self.current_video:
            self.frame_slider.configure(state="normal")