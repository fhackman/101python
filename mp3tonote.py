import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os
import threading
import music21
from basic_pitch.inference import predict_and_save
from basic_pitch import ICASSP_2022_MODEL_PATH

class AI_MusicTranscriber:
    def __init__(self, root):
        self.root = root
        self.root.title("Polyphonic AI Transcriber (Pro Edition)")
        self.root.geometry("700x500")
        self.root.configure(bg="#1e1e1e") # Dark Mode for Coding/Trading environment
        
        # Variables
        self.file_path = None
        self.status_var = tk.StringVar()
        self.status_var.set("System Ready: Waiting for Audio Input...")
        
        self._init_ui()

    def _init_ui(self):
        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TProgressbar", thickness=20)

        # Main Container
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=30, pady=30)

        # Header
        tk.Label(main_frame, text="AI Audio to Sheet Music", 
                 font=("Segoe UI", 24, "bold"), bg="#1e1e1e", fg="#00ff88").pack(pady=(0, 10))
        
        tk.Label(main_frame, text="Powered by CNN & Music21 | Polyphonic Support", 
                 font=("Consolas", 10), bg="#1e1e1e", fg="#aaaaaa").pack(pady=(0, 30))

        # File Selection
        self.file_display = tk.Entry(main_frame, font=("Consolas", 11), bg="#2d2d2d", fg="#ffffff", insertbackground='white')
        self.file_display.pack(fill=tk.X, pady=5)
        
        btn_frame = tk.Frame(main_frame, bg="#1e1e1e")
        btn_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(btn_frame, text="BROWSE MP3/WAV", command=self.browse_file,
                  bg="#3a3a3a", fg="white", font=("Segoe UI", 10, "bold"), 
                  relief=tk.FLAT, padx=20, pady=8).pack(side=tk.LEFT)

        self.convert_btn = tk.Button(btn_frame, text="RUN AI TRANSCRIPTION", command=self.start_ai_thread,
                  bg="#007acc", fg="white", font=("Segoe UI", 10, "bold"), 
                  relief=tk.FLAT, padx=20, pady=8, state=tk.DISABLED)
        self.convert_btn.pack(side=tk.RIGHT)

        # Log/Status Area
        self.log_text = tk.Text(main_frame, height=10, bg="#000000", fg="#00ff00", 
                                font=("Consolas", 9), state=tk.DISABLED, relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True, pady=20)

        # Progress Bar
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100, mode='indeterminate')
        self.progress.pack(fill=tk.X)

        # Status Bar
        tk.Label(self.root, textvariable=self.status_var, 
                 bg="#252526", fg="#dcdcdc", font=("Segoe UI", 9), anchor="w", padx=10).pack(side=tk.BOTTOM, fill=tk.X)

    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f">> {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav *.flac")])
        if filename:
            self.file_path = filename
            self.file_display.delete(0, tk.END)
            self.file_display.insert(0, filename)
            self.convert_btn.config(state=tk.NORMAL, bg="#007acc")
            self.log(f"Selected: {os.path.basename(filename)}")

    def start_ai_thread(self):
        if not self.file_path: return
        
        # UI Update
        self.convert_btn.config(state=tk.DISABLED, bg="#555555")
        self.progress.start(10)
        
        # Threading to keep GUI alive during Heavy Inference
        thread = threading.Thread(target=self.run_inference_pipeline)
        thread.start()

    def run_inference_pipeline(self):
        try:
            output_dir = os.path.dirname(self.file_path)
            base_name = os.path.splitext(os.path.basename(self.file_path))[0]
            
            # --- Step 1: AI Inference ---
            self.status_var.set("Phase 1/3: Running CNN Inference...")
            self.log("Initializing Neural Network (Basic Pitch)...")
            self.log("Extracting Mel-Spectrogram & Predicting MIDI events...")
            
            # predict_and_save handles the heavy lifting
            predict_and_save(
                [self.file_path],
                output_dir,
                save_midi=True,
                sonify_midi=False,
                save_model_outputs=False,
                save_notes=False,
                model_or_model_path=ICASSP_2022_MODEL_PATH
            )
            
            # Basic pitch naming convention usually appends '_basic_pitch.mid'
            expected_midi = os.path.join(output_dir, f"{base_name}_basic_pitch.mid")
            final_xml = os.path.join(output_dir, f"{base_name}_sheet.xml")

            if not os.path.exists(expected_midi):
                raise FileNotFoundError("AI failed to generate MIDI file.")

            self.log("AI Inference Complete. MIDI Generated.")

            # --- Step 2: Quantization & Cleaning ---
            self.status_var.set("Phase 2/3: Quantizing & Formatting...")
            self.log("Loading MIDI into Music21 Stream...")
            
            s = music21.converter.parse(expected_midi)
            
            self.log("Quantizing Rhythm (Snap to grid)...")
            # Quantize to nearest 16th note to make sheet music readable
            # This cleans up the "human" timing from the audio
            s.quantize([4], processOffsets=True, processDurations=True, inPlace=True)
            
            # Add Metadata
            s.insert(0, music21.metadata.Metadata())
            s.metadata.title = f"Transcribed: {base_name}"
            s.metadata.composer = "Hack's AI Engine"

            # --- Step 3: Export ---
            self.status_var.set("Phase 3/3: Exporting MusicXML...")
            s.write('musicxml', fp=final_xml)
            
            self.log(f"SUCCESS: Sheet Music saved as {os.path.basename(final_xml)}")
            self.status_var.set("Ready")
            
            messagebox.showinfo("Mission Accomplished", 
                                f"Transcription Complete!\n\nXML Saved: {final_xml}\n\nYou can open this in MuseScore/Sibelius.")

        except Exception as e:
            self.log(f"ERROR: {str(e)}")
            messagebox.showerror("Critical Error", str(e))
        finally:
            self.root.after(0, self.reset_ui)

    def reset_ui(self):
        self.progress.stop()
        self.convert_btn.config(state=tk.NORMAL, bg="#007acc")

if __name__ == "__main__":
    root = tk.Tk()
    app = AI_MusicTranscriber(root)
    root.mainloop()