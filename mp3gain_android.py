import os
import threading
import math
from pathlib import Path

# Setup local ffmpeg path for Windows testing
SCRIPT_DIR = Path(__file__).parent
FFMPEG_DIR = SCRIPT_DIR / "ffmpeg" / "bin"
if FFMPEG_DIR.exists():
    os.environ["PATH"] = str(FFMPEG_DIR) + os.pathsep + os.environ["PATH"]

# Kivy imports
import kivy
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.clock import Clock, mainthread
from kivy.utils import platform

# Pydub imports
try:
    from pydub import AudioSegment
    from pydub.utils import which
except ImportError:
    AudioSegment = None
    print("Pydub not found. Please install pydub.")

# Theme Colors (Hacker Theme)
BG_DARK = [0.04, 0.05, 0.15, 1]      # #0a0e27
BG_MEDIUM = [0.08, 0.11, 0.24, 1]    # #151b3d
BG_LIGHT = [0.12, 0.15, 0.29, 1]     # #1e2749
MATRIX_GREEN = [0.0, 1.0, 0.25, 1]   # #00ff41
CYBER_CYAN = [0.0, 0.85, 1.0, 1]     # #00d9ff
WARNING_RED = [1.0, 0.03, 0.23, 1]   # #ff073a
TEXT_COLOR = [0.0, 1.0, 0.25, 1]     # Matrix Green

class FileChooserPopup(Popup):
    def __init__(self, callback, **kwargs):
        super().__init__(**kwargs)
        self.callback = callback
        self.title = "Select MP3 Files"
        self.title_color = CYBER_CYAN
        self.background_color = BG_MEDIUM
        
        layout = BoxLayout(orientation='vertical')
        
        # File chooser
        self.file_chooser = FileChooserListView(
            path=str(Path.home()),
            filters=['*.mp3']
        )
        layout.add_widget(self.file_chooser)
        
        # Buttons
        btn_layout = BoxLayout(size_hint_y=None, height=50)
        btn_select = Button(
            text="Select",
            background_color=MATRIX_GREEN,
            color=BG_DARK
        )
        btn_select.bind(on_release=self.on_select)
        
        btn_cancel = Button(
            text="Cancel",
            background_color=WARNING_RED,
            color=BG_DARK
        )
        btn_cancel.bind(on_release=self.dismiss)
        
        btn_layout.add_widget(btn_select)
        btn_layout.add_widget(btn_cancel)
        layout.add_widget(btn_layout)
        
        self.content = layout

    def on_select(self, instance):
        selection = self.file_chooser.selection
        if selection:
            self.callback(selection)
        self.dismiss()

class MP3GainAndroid(App):
    def build(self):
        self.files = [] # List of dicts: {'path': str, 'rms': float, 'status': str}
        self.processing = False
        
        # Main Layout
        main_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        # Background color hack
        with main_layout.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(*BG_DARK)
            self.rect = Rectangle(size=(800, 600), pos=main_layout.pos)
            main_layout.bind(size=self._update_rect, pos=self._update_rect)

        # Title
        title = Label(
            text="[b]MP3 GAIN NORMALIZER[/b]",
            markup=True,
            font_size='24sp',
            color=MATRIX_GREEN,
            size_hint_y=None,
            height=60
        )
        main_layout.add_widget(title)
        
        # Controls
        controls = BoxLayout(orientation='horizontal', size_hint_y=None, height=60, spacing=10)
        
        btn_select = Button(
            text="Select Files",
            background_color=CYBER_CYAN,
            color=BG_DARK,
            bold=True
        )
        btn_select.bind(on_release=self.show_file_chooser)
        controls.add_widget(btn_select)
        
        btn_analyze = Button(
            text="Analyze",
            background_color=MATRIX_GREEN,
            color=BG_DARK,
            bold=True
        )
        btn_analyze.bind(on_release=self.start_analysis)
        controls.add_widget(btn_analyze)
        
        btn_normalize = Button(
            text="Normalize",
            background_color=MATRIX_GREEN,
            color=BG_DARK,
            bold=True
        )
        btn_normalize.bind(on_release=self.start_normalization)
        controls.add_widget(btn_normalize)
        
        main_layout.add_widget(controls)
        
        # Target Volume Slider
        slider_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
        slider_label = Label(text="Target: 100%", color=CYBER_CYAN, size_hint_x=0.3)
        self.slider_label = slider_label
        
        self.slider = Slider(min=0, max=200, value=100)
        self.slider.bind(value=self.on_slider_value)
        
        slider_layout.add_widget(slider_label)
        slider_layout.add_widget(self.slider)
        main_layout.add_widget(slider_layout)
        
        # File List (Scrollable)
        list_header = Label(
            text="Files",
            color=CYBER_CYAN,
            size_hint_y=None,
            height=30,
            halign='left',
            text_size=(self.root_window_width if self.root else 800, None)
        )
        main_layout.add_widget(list_header)
        
        self.scroll_view = ScrollView()
        self.file_list_layout = GridLayout(cols=1, spacing=2, size_hint_y=None)
        self.file_list_layout.bind(minimum_height=self.file_list_layout.setter('height'))
        self.scroll_view.add_widget(self.file_list_layout)
        main_layout.add_widget(self.scroll_view)
        
        # Log / Status
        self.log_label = Label(
            text="Ready...",
            color=MATRIX_GREEN,
            size_hint_y=None,
            height=40,
            halign='left',
            valign='middle'
        )
        self.log_label.bind(size=self.log_label.setter('text_size'))
        main_layout.add_widget(self.log_label)
        
        # Progress Bar
        self.progress = ProgressBar(max=100, value=0, size_hint_y=None, height=20)
        main_layout.add_widget(self.progress)
        
        return main_layout

    def _update_rect(self, instance, value):
        self.rect.pos = instance.pos
        self.rect.size = instance.size

    def on_slider_value(self, instance, value):
        self.slider_label.text = f"Target: {int(value)}%"

    def show_file_chooser(self, instance):
        popup = FileChooserPopup(callback=self.add_files)
        popup.open()

    def add_files(self, file_paths):
        for path in file_paths:
            if not any(f['path'] == path for f in self.files):
                self.files.append({
                    'path': path,
                    'rms': None,
                    'status': 'Pending'
                })
        self.update_file_list_ui()
        self.log(f"Added {len(file_paths)} files.")

    def update_file_list_ui(self):
        self.file_list_layout.clear_widgets()
        for f in self.files:
            fname = os.path.basename(f['path'])
            rms_txt = f"{f['rms']:.1f} dB" if f['rms'] is not None else "--"
            status = f['status']
            
            item_box = BoxLayout(orientation='horizontal', size_hint_y=None, height=40)
            
            lbl_name = Label(text=fname, color=MATRIX_GREEN, size_hint_x=0.5, shorten=True)
            lbl_rms = Label(text=rms_txt, color=CYBER_CYAN, size_hint_x=0.2)
            lbl_status = Label(text=status, color=WARNING_RED if "Error" in status else MATRIX_GREEN, size_hint_x=0.3)
            
            item_box.add_widget(lbl_name)
            item_box.add_widget(lbl_rms)
            item_box.add_widget(lbl_status)
            
            self.file_list_layout.add_widget(item_box)

    @mainthread
    def log(self, message):
        self.log_label.text = f"> {message}"

    @mainthread
    def update_progress(self, value):
        self.progress.value = value

    @mainthread
    def update_file_status(self, index, status, rms=None):
        if 0 <= index < len(self.files):
            self.files[index]['status'] = status
            if rms is not None:
                self.files[index]['rms'] = rms
            self.update_file_list_ui()

    def start_analysis(self, instance):
        if self.processing:
            return
        if not self.files:
            self.log("No files to analyze.")
            return
        
        threading.Thread(target=self._analyze_worker, daemon=True).start()

    def _analyze_worker(self):
        self.processing = True
        self.log("Starting analysis...")
        
        if AudioSegment is None:
             self.log("Error: pydub not installed")
             self.processing = False
             return

        total = len(self.files)
        for i, f in enumerate(self.files):
            self.update_file_status(i, "Analyzing...")
            try:
                audio = AudioSegment.from_mp3(f['path'])
                rms_db = self._calculate_rms_db(audio)
                self.update_file_status(i, "Analyzed", rms=rms_db)
            except Exception as e:
                print(f"Error analyzing {f['path']}: {e}")
                self.update_file_status(i, "Error")
            
            self.update_progress((i + 1) / total * 100)
        
        self.log("Analysis complete.")
        self.processing = False

    def start_normalization(self, instance):
        if self.processing:
            return
        if not self.files:
            self.log("No files to process.")
            return
        
        threading.Thread(target=self._normalize_worker, daemon=True).start()

    def _normalize_worker(self):
        self.processing = True
        self.log("Starting normalization...")
        
        target_percent = self.slider.value
        total = len(self.files)
        
        for i, f in enumerate(self.files):
            if f['rms'] is None:
                self.log(f"Skipping {os.path.basename(f['path'])} (not analyzed)")
                continue
                
            self.update_file_status(i, "Processing...")
            try:
                # Calculate gain
                volume_ratio = target_percent / 100.0
                target_db_adjustment = 20 * math.log10(volume_ratio) if volume_ratio > 0 else -60
                
                audio = AudioSegment.from_mp3(f['path'])
                normalized_audio = audio + target_db_adjustment
                
                # Export
                path_obj = Path(f['path'])
                output_path = path_obj.parent / f"{path_obj.stem}_normalized{path_obj.suffix}"
                
                normalized_audio.export(
                    str(output_path),
                    format="mp3",
                    bitrate="192k"
                )
                self.update_file_status(i, "Done")
            except Exception as e:
                print(f"Error normalizing {f['path']}: {e}")
                self.update_file_status(i, "Error")
            
            self.update_progress((i + 1) / total * 100)
            
        self.log("Normalization complete.")
        self.processing = False

    def _calculate_rms_db(self, audio):
        rms = audio.rms
        max_rms = audio.max_possible_amplitude / math.sqrt(2)
        if rms == 0:
            return -float('inf')
        return 20 * math.log10(rms / max_rms)

    @property
    def root_window_width(self):
        if self.root:
            return self.root.width
        return 800

if __name__ == '__main__':
    MP3GainAndroid().run()
