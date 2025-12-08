#!/usr/bin/env python3
"""
MP3Gain Normalizer - Hacker-Themed GUI
A Python application for analyzing and normalizing MP3 file volumes
with a visually striking matrix-style interface.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
import threading
from pathlib import Path
from typing import List, Tuple
import math

# Setup local ffmpeg path
SCRIPT_DIR = Path(__file__).parent
FFMPEG_DIR = SCRIPT_DIR / "ffmpeg" / "bin"

# Add ffmpeg to PATH if local folder exists
if FFMPEG_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ["PATH"]

try:
    from pydub import AudioSegment
    from pydub.utils import which
except ImportError:
    print("Error: pydub not installed. Run: pip install pydub")
    exit(1)


class HackerTheme:
    """Color and style constants for the hacker theme"""
    BG_DARK = "#0a0e27"
    BG_MEDIUM = "#151b3d"
    BG_LIGHT = "#1e2749"
    
    MATRIX_GREEN = "#00ff41"
    CYBER_CYAN = "#00d9ff"
    WARNING_RED = "#ff073a"
    SUCCESS_GREEN = "#39ff14"
    
    FONT_MAIN = ("Consolas", 10)
    FONT_TITLE = ("Consolas", 14, "bold")
    FONT_BUTTON = ("Consolas", 10, "bold")
    FONT_LOG = ("Courier New", 9)


class MP3GainGUI:
    """Main application window with hacker-themed GUI"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("▓▓▓ MP3 GAIN NORMALIZER v1.0 ▓▓▓")
        self.root.geometry("900x700")
        self.root.configure(bg=HackerTheme.BG_DARK)
        self.root.resizable(True, True)
        
        # File list: (filepath, rms_db, target_volume, status)
        self.files = []
        self.target_volume = tk.DoubleVar(value=100.0)
        self.processing = False
        
        self._create_widgets()
        self._apply_hacker_styles()
        
        # Check for ffmpeg/avconv (after widgets are created so we can log)
        self.ffmpeg_available = which("ffmpeg") or which("avconv")
        if not self.ffmpeg_available:
            ffmpeg_folder = SCRIPT_DIR / "ffmpeg"
            messagebox.showwarning(
                "Missing Dependency",
                f"ffmpeg or avconv is required for MP3 processing.\n\n"
                f"Option 1 - Use local folder:\n"
                f"Extract ffmpeg to: {ffmpeg_folder}\\bin\\\n"
                f"(Create the folder structure and place ffmpeg.exe there)\n\n"
                f"Option 2 - System install:\n"
                f"- Windows: Download from ffmpeg.org\n"
                f"- Linux: sudo apt install ffmpeg\n"
                f"- Mac: brew install ffmpeg\n\n"
                f"The app will work once ffmpeg is available."
            )
        else:
            # Detect which ffmpeg is being used
            ffmpeg_path = which("ffmpeg") or which("avconv")
            if str(FFMPEG_DIR) in str(ffmpeg_path):
                self.log("> Using local ffmpeg from: ffmpeg/bin/")
    
    def _create_widgets(self):
        """Create all GUI widgets"""
        
        # Title bar
        title_frame = tk.Frame(self.root, bg=HackerTheme.BG_MEDIUM, height=60)
        title_frame.pack(fill=tk.X, padx=2, pady=2)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame,
            text="▓▓▓ MP3 GAIN NORMALIZER v1.0 ▓▓▓",
            font=HackerTheme.FONT_TITLE,
            bg=HackerTheme.BG_MEDIUM,
            fg=HackerTheme.MATRIX_GREEN
        )
        title_label.pack(pady=15)
        
        # Control buttons frame
        control_frame = tk.Frame(self.root, bg=HackerTheme.BG_DARK)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.btn_select = tk.Button(
            control_frame,
            text="[ SELECT FILES ]",
            command=self.select_files,
            font=HackerTheme.FONT_BUTTON,
            bg=HackerTheme.BG_LIGHT,
            fg=HackerTheme.CYBER_CYAN,
            activebackground=HackerTheme.CYBER_CYAN,
            activeforeground=HackerTheme.BG_DARK,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.btn_select.pack(side=tk.LEFT, padx=5)
        
        self.btn_analyze = tk.Button(
            control_frame,
            text="[ ANALYZE ]",
            command=self.analyze_files,
            font=HackerTheme.FONT_BUTTON,
            bg=HackerTheme.BG_LIGHT,
            fg=HackerTheme.MATRIX_GREEN,
            activebackground=HackerTheme.MATRIX_GREEN,
            activeforeground=HackerTheme.BG_DARK,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.btn_analyze.pack(side=tk.LEFT, padx=5)
        
        self.btn_normalize = tk.Button(
            control_frame,
            text="[ NORMALIZE ]",
            command=self.normalize_files,
            font=HackerTheme.FONT_BUTTON,
            bg=HackerTheme.BG_LIGHT,
            fg=HackerTheme.SUCCESS_GREEN,
            activebackground=HackerTheme.SUCCESS_GREEN,
            activeforeground=HackerTheme.BG_DARK,
            relief=tk.FLAT,
            padx=15,
            pady=8,
            cursor="hand2"
        )
        self.btn_normalize.pack(side=tk.LEFT, padx=5)
        
        # Target volume slider frame
        slider_frame = tk.Frame(self.root, bg=HackerTheme.BG_MEDIUM)
        slider_frame.pack(fill=tk.X, padx=10, pady=10)
        
        slider_label = tk.Label(
            slider_frame,
            text="Target Volume:",
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_MEDIUM,
            fg=HackerTheme.CYBER_CYAN
        )
        slider_label.pack(side=tk.LEFT, padx=10)
        
        # Create formatted label for percentage display
        self.target_label = tk.Label(
            slider_frame,
            text=f"{self.target_volume.get():.0f}%",
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_MEDIUM,
            fg=HackerTheme.MATRIX_GREEN,
            width=8
        )
        self.target_label.pack(side=tk.LEFT, padx=5)
        
        # Update label when slider changes
        self.target_volume.trace('w', lambda *args: self.target_label.config(text=f"{self.target_volume.get():.0f}%"))
        
        self.slider = tk.Scale(
            slider_frame,
            from_=0.0,
            to=200.0,
            resolution=1.0,
            orient=tk.HORIZONTAL,
            variable=self.target_volume,
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_LIGHT,
            fg=HackerTheme.MATRIX_GREEN,
            highlightthickness=0,
            troughcolor=HackerTheme.BG_DARK,
            activebackground=HackerTheme.CYBER_CYAN,
            length=300,
            showvalue=False
        )
        self.slider.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # File list frame
        list_frame = tk.Frame(self.root, bg=HackerTheme.BG_DARK)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        list_label = tk.Label(
            list_frame,
            text=">> File List",
            font=HackerTheme.FONT_BUTTON,
            bg=HackerTheme.BG_DARK,
            fg=HackerTheme.MATRIX_GREEN,
            anchor=tk.W
        )
        list_label.pack(fill=tk.X, pady=(0, 5))
        
        # Treeview for file list
        tree_frame = tk.Frame(list_frame, bg=HackerTheme.BG_LIGHT)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tree = ttk.Treeview(
            tree_frame,
            columns=("filename", "rms", "target", "status"),
            show="headings",
            height=10
        )
        
        self.tree.heading("filename", text="Filename")
        self.tree.heading("rms", text="Current RMS (dB)")
        self.tree.heading("target", text="Target Volume (%)")
        self.tree.heading("status", text="Status")
        
        self.tree.column("filename", width=350)
        self.tree.column("rms", width=150, anchor=tk.CENTER)
        self.tree.column("target", width=150, anchor=tk.CENTER)
        self.tree.column("status", width=200, anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        # File management buttons
        file_btn_frame = tk.Frame(self.root, bg=HackerTheme.BG_DARK)
        file_btn_frame.pack(fill=tk.X, padx=10, pady=5)
        
        btn_remove = tk.Button(
            file_btn_frame,
            text="[ REMOVE SELECTED ]",
            command=self.remove_selected,
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_LIGHT,
            fg=HackerTheme.WARNING_RED,
            activebackground=HackerTheme.WARNING_RED,
            activeforeground=HackerTheme.BG_DARK,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        btn_remove.pack(side=tk.LEFT, padx=5)
        
        btn_clear = tk.Button(
            file_btn_frame,
            text="[ CLEAR ALL ]",
            command=self.clear_all,
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_LIGHT,
            fg=HackerTheme.WARNING_RED,
            activebackground=HackerTheme.WARNING_RED,
            activeforeground=HackerTheme.BG_DARK,
            relief=tk.FLAT,
            padx=10,
            pady=5,
            cursor="hand2"
        )
        btn_clear.pack(side=tk.LEFT, padx=5)
        
        # Progress bar frame
        progress_frame = tk.Frame(self.root, bg=HackerTheme.BG_MEDIUM)
        progress_frame.pack(fill=tk.X, padx=10, pady=10)
        
        progress_label = tk.Label(
            progress_frame,
            text="Progress:",
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_MEDIUM,
            fg=HackerTheme.CYBER_CYAN
        )
        progress_label.pack(side=tk.LEFT, padx=10)
        
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate',
            length=500
        )
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        
        self.progress_text = tk.Label(
            progress_frame,
            text="0%",
            font=HackerTheme.FONT_MAIN,
            bg=HackerTheme.BG_MEDIUM,
            fg=HackerTheme.MATRIX_GREEN,
            width=6
        )
        self.progress_text.pack(side=tk.LEFT, padx=10)
        
        # Terminal log frame
        log_frame = tk.Frame(self.root, bg=HackerTheme.BG_DARK)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))
        
        log_label = tk.Label(
            log_frame,
            text=">> Terminal Log",
            font=HackerTheme.FONT_BUTTON,
            bg=HackerTheme.BG_DARK,
            fg=HackerTheme.MATRIX_GREEN,
            anchor=tk.W
        )
        log_label.pack(fill=tk.X, pady=(0, 5))
        
        log_text_frame = tk.Frame(log_frame, bg=HackerTheme.BG_LIGHT)
        log_text_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = tk.Text(
            log_text_frame,
            font=HackerTheme.FONT_LOG,
            bg=HackerTheme.BG_DARK,
            fg=HackerTheme.MATRIX_GREEN,
            insertbackground=HackerTheme.MATRIX_GREEN,
            relief=tk.FLAT,
            height=8,
            wrap=tk.WORD
        )
        
        log_scrollbar = ttk.Scrollbar(log_text_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscroll=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        self.log("> MP3 Gain Normalizer initialized")
        self.log("> Ready to process files...")
    
    def _apply_hacker_styles(self):
        """Apply custom styles to ttk widgets"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Treeview style
        style.configure(
            "Treeview",
            background=HackerTheme.BG_DARK,
            foreground=HackerTheme.MATRIX_GREEN,
            fieldbackground=HackerTheme.BG_DARK,
            font=HackerTheme.FONT_MAIN,
            borderwidth=0
        )
        style.configure(
            "Treeview.Heading",
            background=HackerTheme.BG_LIGHT,
            foreground=HackerTheme.CYBER_CYAN,
            font=HackerTheme.FONT_BUTTON,
            relief=tk.FLAT
        )
        style.map("Treeview", background=[('selected', HackerTheme.BG_LIGHT)])
        style.map("Treeview", foreground=[('selected', HackerTheme.SUCCESS_GREEN)])
        
        # Progressbar style
        style.configure(
            "Horizontal.TProgressbar",
            background=HackerTheme.MATRIX_GREEN,
            troughcolor=HackerTheme.BG_DARK,
            borderwidth=0,
            thickness=20
        )
    
    def log(self, message: str, color: str = None):
        """Add a message to the terminal log"""
        self.log_text.insert(tk.END, message + "\n")
        if color:
            # Color specific lines (future enhancement)
            pass
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def select_files(self):
        """Open file dialog to select multiple MP3 files"""
        files = filedialog.askopenfilenames(
            title="Select MP3 Files",
            filetypes=[("MP3 files", "*.mp3"), ("All files", "*.*")]
        )
        
        if files:
            added_count = 0
            for filepath in files:
                # Check if file already in list
                if not any(f[0] == filepath for f in self.files):
                    self.files.append([filepath, None, self.target_volume.get(), "Pending"])
                    added_count += 1
            
            self.log(f"> Added {added_count} file(s) to queue")
            self.update_file_list()
    
    def update_file_list(self):
        """Update the treeview with current file list"""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Add all files
        for filepath, rms, target, status in self.files:
            filename = os.path.basename(filepath)
            rms_str = f"{rms:.1f}" if rms is not None else "Not analyzed"
            target_str = f"{target:.0f}%"
            
            self.tree.insert("", tk.END, values=(filename, rms_str, target_str, status))
    
    def remove_selected(self):
        """Remove selected files from the list"""
        selected = self.tree.selection()
        if not selected:
            self.log("> No files selected for removal")
            return
        
        # Get indices of selected items
        indices = [self.tree.index(item) for item in selected]
        indices.sort(reverse=True)
        
        for idx in indices:
            del self.files[idx]
        
        self.log(f"> Removed {len(indices)} file(s)")
        self.update_file_list()
    
    def clear_all(self):
        """Clear all files from the list"""
        if self.files:
            count = len(self.files)
            self.files.clear()
            self.update_file_list()
            self.log(f"> Cleared {count} file(s)")
        else:
            self.log("> No files to clear")
    
    def analyze_files(self):
        """Analyze RMS levels of all files"""
        if not self.files:
            self.log("> No files to analyze")
            messagebox.showwarning("No Files", "Please select MP3 files first")
            return
        
        if self.processing:
            self.log("> Analysis already in progress")
            return
        
        # Run analysis in background thread
        thread = threading.Thread(target=self._analyze_worker, daemon=True)
        thread.start()
    
    def _analyze_worker(self):
        """Background worker for analyzing files"""
        self.processing = True
        self.log("> Starting analysis...")
        
        total = len(self.files)
        
        for idx, file_data in enumerate(self.files):
            filepath = file_data[0]
            filename = os.path.basename(filepath)
            
            # Update status
            file_data[3] = "Analyzing..."
            self.root.after(0, self.update_file_list)
            
            self.log(f"> Analyzing: {filename}")
            
            try:
                # Load audio file
                audio = AudioSegment.from_mp3(filepath)
                
                # Calculate RMS in dB
                rms_db = self._calculate_rms_db(audio)
                
                # Update file data
                file_data[1] = rms_db
                file_data[2] = self.target_volume.get()
                file_data[3] = "Analyzed ✓"
                
                self.log(f"  Current level: {rms_db:.1f} dB")
                
            except Exception as e:
                self.log(f"  Error: {str(e)}")
                file_data[3] = "Error ✗"
            
            # Update progress
            progress = ((idx + 1) / total) * 100
            self.root.after(0, self._update_progress, progress)
            self.root.after(0, self.update_file_list)
        
        self.log("> Analysis complete!")
        self.processing = False
        self.root.after(0, self._update_progress, 0)
    
    def normalize_files(self):
        """Normalize all analyzed files"""
        if not self.files:
            self.log("> No files to normalize")
            messagebox.showwarning("No Files", "Please select MP3 files first")
            return
        
        # Check if any files have been analyzed
        analyzed = [f for f in self.files if f[1] is not None]
        if not analyzed:
            self.log("> No analyzed files. Please run analysis first")
            messagebox.showwarning("Not Analyzed", "Please analyze files first")
            return
        
        if self.processing:
            self.log("> Normalization already in progress")
            return
        
        # Run normalization in background thread
        thread = threading.Thread(target=self._normalize_worker, daemon=True)
        thread.start()
    
    def _normalize_worker(self):
        """Background worker for normalizing files"""
        self.processing = True
        self.log("> Starting normalization...")
        
        target_volume = self.target_volume.get()
        files_to_process = [f for f in self.files if f[1] is not None]
        total = len(files_to_process)
        
        for idx, file_data in enumerate(files_to_process):
            filepath = file_data[0]
            current_rms = file_data[1]
            target_vol_percent = file_data[2]
            filename = os.path.basename(filepath)
            
            # Update status
            file_data[3] = "Processing..."
            self.root.after(0, self.update_file_list)
            
            self.log(f"> Normalizing: {filename}")
            
            try:
                # Convert volume percentage to dB adjustment
                # 100% = 0dB (no change), 200% = +6dB, 50% = -6dB
                volume_ratio = target_vol_percent / 100.0
                target_db_adjustment = 20 * math.log10(volume_ratio) if volume_ratio > 0 else -60
                
                # Log the adjustment
                self.log(f"  Target volume: {target_vol_percent:.0f}% ({target_db_adjustment:+.1f} dB)")
                self.log(f"  Current RMS: {current_rms:.1f} dB")
                
                # Load audio
                audio = AudioSegment.from_mp3(filepath)
                
                # Apply gain
                normalized_audio = audio + target_db_adjustment
                
                # Generate output filename
                path_obj = Path(filepath)
                output_path = path_obj.parent / f"{path_obj.stem}_normalized{path_obj.suffix}"
                
                # Export
                normalized_audio.export(
                    output_path,
                    format="mp3",
                    bitrate="192k",
                    tags={
                        'artist': normalized_audio.tags.get('artist', [''])[0] if hasattr(normalized_audio, 'tags') else '',
                        'album': normalized_audio.tags.get('album', [''])[0] if hasattr(normalized_audio, 'tags') else '',
                        'title': normalized_audio.tags.get('title', [''])[0] if hasattr(normalized_audio, 'tags') else ''
                    }
                )
                
                file_data[3] = "Complete ✓"
                self.log(f"  Saved: {output_path.name}")
                
            except Exception as e:
                self.log(f"  Error: {str(e)}")
                file_data[3] = "Error ✗"
            
            # Update progress
            progress = ((idx + 1) / total) * 100
            self.root.after(0, self._update_progress, progress)
            self.root.after(0, self.update_file_list)
        
        self.log("> Normalization complete!")
        self.processing = False
        self.root.after(0, self._update_progress, 0)
        
        # Show completion message
        self.root.after(0, messagebox.showinfo, "Complete", 
                       f"Normalized {total} file(s) successfully!")
    
    def _calculate_rms_db(self, audio: AudioSegment) -> float:
        """Calculate RMS loudness in dB"""
        # Get RMS value
        rms = audio.rms
        
        # Convert to dBFS (dB relative to full scale)
        # Reference: maximum possible RMS for 16-bit audio
        max_rms = audio.max_possible_amplitude / math.sqrt(2)
        
        if rms == 0:
            return -float('inf')
        
        db = 20 * math.log10(rms / max_rms)
        return db
    
    def _update_progress(self, value: float):
        """Update progress bar"""
        self.progress_var.set(value)
        self.progress_text.config(text=f"{value:.0f}%")


def main():
    """Main entry point"""
    root = tk.Tk()
    app = MP3GainGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
