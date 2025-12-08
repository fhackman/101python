import os
import sys
import tempfile
import platform
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import traceback

class MusicToSightSingingConverter:
    def __init__(self):
        self.check_system_requirements()
        self.setup_environment()
        
    def check_system_requirements(self):
        """Verify basic system requirements"""
        if sys.version_info < (3, 8):
            messagebox.showerror(
                "Python Version Error",
                "Python 3.8 or higher is required.\n"
                f"Current version: {sys.version}"
            )
            raise RuntimeError("Python version too old")

        try:
            tk.Tk()  # Test Tkinter availability
        except:
            messagebox.showerror(
                "Tkinter Error",
                "Tkinter is not available.\n"
                "On Linux, install with: sudo apt-get install python3-tk"
            )
            raise

    def setup_environment(self):
        """Configure paths and environment"""
        try:
            from music21 import environment
            env = environment.Environment()
            
            # Set MuseScore path
            ms_path = self.find_musescore()
            if ms_path:
                env['musicxmlPath'] = ms_path
                env['musescoreDirectPNGPath'] = ms_path
            else:
                messagebox.showwarning(
                    "MuseScore Not Found",
                    "MuseScore not found. Sheet music generation may not work.\n"
                    "Please install from https://musescore.org/"
                )
        except ImportError:
            pass  # Handled in check_dependencies

    def find_musescore(self):
        """Find MuseScore executable path"""
        system = platform.system()
        paths = {
            'Windows': [
                'C:/Program Files/MuseScore 4/bin/MuseScore4.exe',
                'C:/Program Files/MuseScore 3/bin/MuseScore3.exe'
            ],
            'Darwin': [
                '/Applications/MuseScore 4.app/Contents/MacOS/mscore',
                '/Applications/MuseScore 3.app/Contents/MacOS/mscore'
            ],
            'Linux': [
                '/usr/bin/musescore',
                '/usr/local/bin/musescore',
                '/snap/bin/musescore'
            ]
        }.get(system, [])
        
        return next((p for p in paths if Path(p).exists()), None)

    def check_dependencies(self):
        """Check and install required packages"""
        required = {
            'librosa': '0.10.1',
            'music21': '9.1.0',
            'pydub': '0.25.1',
            'numpy': '1.24.4'
        }
        
        missing = []
        wrong_version = []
        
        for package, version in required.items():
            try:
                mod = __import__(package)
                if hasattr(mod, '__version__') and mod.__version__ != version:
                    wrong_version.append(f"{package} (needs {version}, has {mod.__version__})")
            except ImportError:
                missing.append(package)
        
        if missing or wrong_version:
            msg = ["Dependency issues detected:"]
            if missing:
                msg.append("\nMissing packages:\n- " + "\n- ".join(missing))
            if wrong_version:
                msg.append("\nVersion mismatches:\n- " + "\n- ".join(wrong_version))
            
            msg.append("\nWould you like to install the correct versions?")
            
            if messagebox.askyesno("Dependency Issues", "\n".join(msg)):
                self.install_dependencies(required)
                messagebox.showinfo(
                    "Restart Required",
                    "Please restart the application after installation completes."
                )
                sys.exit(0)
            else:
                raise ImportError("Missing or incorrect dependencies")

    def install_dependencies(self, requirements):
        """Install required packages"""
        install_cmd = [
            sys.executable, "-m", "pip", "install",
            "--upgrade", "--user"
        ] + [f"{pkg}=={ver}" for pkg, ver in requirements.items()]
        
        try:
            subprocess.run(install_cmd, check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror(
                "Installation Failed",
                f"Failed to install dependencies:\n{str(e)}"
            )
            raise

    def run_conversion(self, input_file):
        """Main conversion workflow"""
        if not input_file or not Path(input_file).exists():
            return None, None
        
        try:
            # Import inside method to prevent early dependency errors
            import librosa
            from music21 import stream, note, tempo, clef
            from pydub import AudioSegment
            
            # Create sheet music
            sheet_path = self.create_sheet_music(input_file, librosa)
            if not sheet_path:
                return None, None
                
            # Create slowed audio
            audio_path = self.create_practice_audio(input_file, AudioSegment)
            
            return sheet_path, audio_path
            
        except Exception as e:
            traceback.print_exc()
            messagebox.showerror("Error", f"Conversion failed: {str(e)}")
            return None, None

    def create_sheet_music(self, audio_file, librosa):
        """Convert audio to sheet music with solfege"""
        try:
            # Load audio with reduced verbosity
            y, sr = librosa.load(audio_file, sr=None, mono=True)
            
            # Extract pitches using YIN algorithm
            pitches = librosa.yin(
                y,
                fmin=librosa.note_to_hz('C2'),
                fmax=librosa.note_to_hz('C7'),
                sr=sr
            )
            
            # Convert to notes and remove invalid ones
            notes = []
            for p in pitches:
                if p > 0:
                    try:
                        notes.append(librosa.hz_to_note(p))
                    except:
                        continue
            
            # Create music21 stream
            s = stream.Stream()
            s.append(clef.TrebleClef())
            s.append(tempo.MetronomeMark(number=100))
            
            # Add notes with solfege
            solfege_map = {
                'C': 'Do', 'D': 'Re', 'E': 'Mi',
                'F': 'Fa', 'G': 'Sol', 'A': 'La', 'B': 'Ti'
            }
            
            for n in notes:
                try:
                    note_name = n[:-1] if n[-1].isdigit() else n
                    n_obj = note.Note(n)
                    n_obj.lyric = solfege_map.get(note_name.upper(), '')
                    s.append(n_obj)
                except:
                    continue
            
            # Save as PNG
            output = tempfile.NamedTemporaryFile(suffix='.png', delete=False).name
            s.write('musicxml.png', output)
            return output
            
        except Exception as e:
            messagebox.showerror("Error", f"Sheet music generation failed: {str(e)}")
            return None

    def create_practice_audio(self, audio_file, AudioSegment):
        """Create slowed down audio for practice"""
        try:
            audio = AudioSegment.from_file(audio_file)
            slowed = audio._spawn(
                audio.raw_data,
                overrides={"frame_rate": int(audio.frame_rate * 0.7)}
            )
            output = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False).name
            slowed.export(output, format='mp3', bitrate='192k')
            return output
        except Exception as e:
            messagebox.showerror("Error", f"Audio processing failed: {str(e)}")
            return None

    def open_file(self, path):
        """Open file with default application"""
        try:
            system = platform.system()
            if system == 'Windows':
                os.startfile(path)
            elif system == 'Darwin':
                subprocess.run(['open', path], check=True)
            else:
                subprocess.run(['xdg-open', path], check=True)
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't open file: {str(e)}")


def main():
    """Run the application"""
    try:
        # Initialize main window
        root = tk.Tk()
        root.title("Music to Sight-Singing Converter")
        root.geometry("400x300")
        
        # Initialize converter
        converter = MusicToSightSingingConverter()
        converter.check_dependencies()
        
        # UI Elements
        tk.Label(
            root,
            text="Music to Sight-Singing Converter",
            font=('Arial', 16, 'bold')
        ).pack(pady=10)
        
        tk.Label(
            root,
            text="Convert audio files to sight-singing exercises\nwith sheet music and practice audio",
            wraplength=380
        ).pack(pady=5)
        
        def browse_and_convert():
            """Handle file selection and conversion"""
            file_path = filedialog.askopenfilename(
                title="Select Music File",
                initialdir=os.path.expanduser("~"),
                filetypes=[
                    ("Audio Files", "*.mp3 *.wav *.ogg *.flac"),
                    ("All Files", "*.*")
                ]
            )
            
            if not file_path:
                return
                
            status.config(text="Processing...", fg='blue')
            root.update()
            
            sheet_path, audio_path = converter.run_conversion(file_path)
            
            if sheet_path and audio_path:
                status.config(text="Conversion Complete!", fg='green')
                
                # Show results dialog
                result_window = tk.Toplevel(root)
                result_window.title("Conversion Results")
                result_window.geometry("400x200")
                
                tk.Label(
                    result_window,
                    text="Successfully created:",
                    font=('Arial', 12)
                ).pack(pady=10)
                
                tk.Label(
                    result_window,
                    text=f"Sheet music: {sheet_path}\nPractice audio: {audio_path}",
                    justify=tk.LEFT
                ).pack(pady=5)
                
                def open_files():
                    converter.open_file(sheet_path)
                    converter.open_file(audio_path)
                    result_window.destroy()
                
                tk.Button(
                    result_window,
                    text="Open Files",
                    command=open_files,
                    width=15
                ).pack(pady=10)
                
                tk.Button(
                    result_window,
                    text="Close",
                    command=result_window.destroy,
                    width=15
                ).pack(pady=5)
                
            else:
                status.config(text="Conversion Failed", fg='red')
        
        # Main button
        convert_btn = tk.Button(
            root,
            text="Select Music File",
            command=browse_and_convert,
            height=2,
            width=20
        )
        convert_btn.pack(pady=20)
        
        # Status label
        status = tk.Label(root, text="", font=('Arial', 10))
        status.pack(pady=10)
        
        # System info
        sys_info = f"Python {sys.version.split()[0]} on {platform.system()}"
        tk.Label(root, text=sys_info, font=('Arial', 8)).pack(side=tk.BOTTOM, pady=5)
        
        root.mainloop()
        
    except Exception as e:
        messagebox.showerror(
            "Fatal Error",
            f"Application failed to start:\n{str(e)}\n\n"
            "Please check the requirements and try again."
        )
        traceback.print_exc()


if __name__ == "__main__":
    # Ensure proper working directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Run the application
    main()