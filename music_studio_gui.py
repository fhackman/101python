import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import time
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import librosa
import soundfile as sf
from mp3tomidi import convert_mp3_to_midi
import pretty_midi
import music21

class MusicStudioGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Music Studio AI")
        self.root.geometry("1100x850")
        self.root.configure(bg="#1A1A2E")
        
        self.file_path = None
        self.midi_path = None
        
        self.setup_styles()
        self.setup_ui()
        
    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Modern Dark Theme
        bg_color = "#1A1A2E"
        fg_color = "#E94560"
        accent_color = "#0F3460"
        text_color = "#FFFFFF"
        
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("TLabel", background=bg_color, foreground=text_color, font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground=fg_color)
        
        self.style.configure("TButton", 
                           font=("Segoe UI", 11, "bold"), 
                           background=fg_color, 
                           foreground="white",
                           borderwidth=0,
                           padding=10)
        self.style.map("TButton", background=[('active', "#C81E45")])
        
        self.style.configure("Card.TFrame", background=accent_color, relief="flat")
        
        # Progress Bar Style
        self.style.configure("Horizontal.TProgressbar", background=fg_color, troughcolor=accent_color, borderwidth=0)
        
    def setup_ui(self):
        # Main Container
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_lbl = ttk.Label(main_frame, text="Music Studio AI", style="Header.TLabel")
        header_lbl.pack(pady=(0, 20))
        
        # File Selection Area
        file_frame = ttk.Frame(main_frame, style="Card.TFrame", padding=15)
        file_frame.pack(fill="x", pady=10)
        
        self.file_lbl = ttk.Label(file_frame, text="No file selected", font=("Segoe UI", 12))
        self.file_lbl.pack(side="left", fill="x", expand=True)
        
        browse_btn = ttk.Button(file_frame, text="Browse MP3", command=self.browse_file)
        browse_btn.pack(side="right", padx=5)
        
        # Action Buttons
        action_frame = ttk.Frame(main_frame, padding=10)
        action_frame.pack(fill="x", pady=10)
        
        self.convert_btn = ttk.Button(action_frame, text="Convert to MIDI", command=self.start_conversion, state="disabled")
        self.convert_btn.pack(side="left", fill="x", expand=True, padx=5)
        
        self.sheet_btn = ttk.Button(action_frame, text="Convert MIDI to Sheet", command=self.start_sheet_conversion, state="disabled")
        self.sheet_btn.pack(side="left", fill="x", expand=True, padx=5)
        
        self.separate_btn = ttk.Button(action_frame, text="Separate Instruments", command=self.start_separation, state="disabled")
        self.separate_btn.pack(side="left", fill="x", expand=True, padx=5)
        
        # Status & Progress
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill="x", pady=5)
        
        self.status_lbl = ttk.Label(status_frame, text="Ready", font=("Segoe UI", 10, "italic"), foreground="#AAAAAA")
        self.status_lbl.pack(anchor="w")
        
        self.progress = ttk.Progressbar(status_frame, style="Horizontal.TProgressbar", orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", pady=(5, 0))
        
        # Visualization Area
        viz_frame = ttk.Frame(main_frame, style="Card.TFrame", padding=5)
        viz_frame.pack(fill="both", expand=True, pady=10)
        
        # Matplotlib Figure
        plt.style.use('dark_background')
        self.fig, (self.ax_wave, self.ax_piano) = plt.subplots(2, 1, figsize=(10, 6), dpi=100)
        self.fig.patch.set_facecolor('#16213E')
        
        self.ax_wave.set_facecolor('#16213E')
        self.ax_wave.set_title("Audio Waveform", color='white', fontsize=10)
        self.ax_wave.set_xticks([])
        self.ax_wave.set_yticks([])
        
        self.ax_piano.set_facecolor('#16213E')
        self.ax_piano.set_title("Piano Roll (Sheet Music)", color='white', fontsize=10)
        self.ax_piano.set_xlabel("Time (s)")
        self.ax_piano.set_ylabel("Pitch")
        
        self.canvas = FigureCanvasTkAgg(self.fig, master=viz_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        
    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if filename:
            self.file_path = filename
            self.file_lbl.config(text=os.path.basename(filename))
            self.convert_btn.config(state="normal")
            self.separate_btn.config(state="normal")
            self.sheet_btn.config(state="disabled") # Disabled until MIDI is ready
            self.status_lbl.config(text="File loaded. Ready to process.")
            self.progress['value'] = 0
            
            # Preview Waveform
            threading.Thread(target=self.plot_waveform, daemon=True).start()
            
    def plot_waveform(self):
        try:
            y, sr = librosa.load(self.file_path, sr=None, duration=30) # Load first 30s for preview
            self.ax_wave.clear()
            self.ax_wave.plot(np.linspace(0, len(y)/sr, len(y)), y, color='#E94560', alpha=0.8)
            self.ax_wave.set_title("Audio Waveform (Preview)", color='white')
            self.ax_wave.set_facecolor('#16213E')
            self.canvas.draw_idle()
        except Exception as e:
            print(f"Error plotting waveform: {e}")

    def start_conversion(self):
        if not self.file_path: return
        self.convert_btn.config(state="disabled")
        self.status_lbl.config(text="Converting to MIDI... This may take a moment.")
        self.progress.config(mode="indeterminate")
        self.progress.start(10)
        threading.Thread(target=self.process_midi, daemon=True).start()
        
    def process_midi(self):
        try:
            output_dir = os.path.dirname(self.file_path)
            midi_file = convert_mp3_to_midi(self.file_path, output_dir)
            self.midi_path = midi_file
            
            self.root.after(0, lambda: self.status_lbl.config(text=f"MIDI Saved: {os.path.basename(midi_file)}"))
            self.root.after(0, self.plot_pianoroll)
            self.root.after(0, lambda: self.convert_btn.config(state="normal"))
            self.root.after(0, lambda: self.sheet_btn.config(state="normal"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.convert_btn.config(state="normal"))
        finally:
            self.root.after(0, self.progress.stop)
            self.root.after(0, lambda: self.progress.config(mode="determinate", value=100))

    def start_sheet_conversion(self):
        if not self.midi_path: return
        self.sheet_btn.config(state="disabled")
        self.status_lbl.config(text="Converting MIDI to Sheet Music (MusicXML)...")
        self.progress.config(mode="determinate", value=0)
        threading.Thread(target=self.process_sheet, daemon=True).start()

    def process_sheet(self):
        try:
            # 1. Parse MIDI
            self.root.after(0, lambda: self.progress.config(value=30))
            self.root.after(0, lambda: self.status_lbl.config(text="Parsing MIDI..."))
            
            score = music21.converter.parse(self.midi_path)
            
            # 2. Write MusicXML
            self.root.after(0, lambda: self.progress.config(value=60))
            self.root.after(0, lambda: self.status_lbl.config(text="Generating MusicXML..."))
            
            base_name = os.path.splitext(self.midi_path)[0]
            xml_path = f"{base_name}.musicxml"
            score.write('musicxml', fp=xml_path)
            
            self.root.after(0, lambda: self.progress.config(value=100))
            self.root.after(0, lambda: self.status_lbl.config(text=f"Sheet Music Saved: {os.path.basename(xml_path)}"))
            self.root.after(0, lambda: self.sheet_btn.config(state="normal"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.sheet_btn.config(state="normal"))
            self.root.after(0, lambda: self.progress.config(value=0))

    def plot_pianoroll(self):
        if not self.midi_path: return
        try:
            midi_data = pretty_midi.PrettyMIDI(self.midi_path)
            
            self.ax_piano.clear()
            
            # Collect notes
            notes = []
            for instrument in midi_data.instruments:
                if not instrument.is_drum:
                    for note in instrument.notes:
                        notes.append((note.start, note.pitch, note.end - note.start))
            
            if notes:
                starts, pitches, durations = zip(*notes)
                self.ax_piano.barh(pitches, durations, left=starts, height=0.8, color='#0F3460', edgecolor='#E94560')
                self.ax_piano.set_ylim(min(pitches)-2, max(pitches)+2)
                self.ax_piano.set_xlim(0, max(starts) + max(durations))
            
            self.ax_piano.set_title("Piano Roll (Sheet Music)", color='white')
            self.ax_piano.set_facecolor('#16213E')
            self.canvas.draw_idle()
            
        except Exception as e:
            print(f"Error plotting piano roll: {e}")

    def start_separation(self):
        if not self.file_path: return
        self.separate_btn.config(state="disabled")
        self.status_lbl.config(text="Separating Instruments... Please wait.")
        self.progress.config(mode="determinate", value=0)
        threading.Thread(target=self.process_separation, daemon=True).start()
        
    def process_separation(self):
        try:
            self.root.after(0, lambda: self.progress.config(value=10))
            y, sr = librosa.load(self.file_path)
            
            # Harmonic-Percussive Source Separation
            self.root.after(0, lambda: self.progress.config(value=40))
            self.root.after(0, lambda: self.status_lbl.config(text="Processing HPSS..."))
            y_harmonic, y_percussive = librosa.effects.hpss(y)
            
            self.root.after(0, lambda: self.progress.config(value=80))
            self.root.after(0, lambda: self.status_lbl.config(text="Saving Audio Files..."))
            
            base_name = os.path.splitext(self.file_path)[0]
            sf.write(f"{base_name}_harmonic.wav", y_harmonic, sr)
            sf.write(f"{base_name}_percussive.wav", y_percussive, sr)
            
            self.root.after(0, lambda: self.progress.config(value=100))
            self.root.after(0, lambda: self.status_lbl.config(text="Separation Complete! Saved _harmonic.wav and _percussive.wav"))
            self.root.after(0, lambda: self.separate_btn.config(state="normal"))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.separate_btn.config(state="normal"))
            self.root.after(0, lambda: self.progress.config(value=0))

if __name__ == "__main__":
    root = tk.Tk()
    app = MusicStudioGUI(root)
    root.mainloop()
