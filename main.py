"""
PA Scanner Pro - Minimal Android Version
Simple Kivy app for testing Android build
"""
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.core.window import Window
import random
from datetime import datetime

# Pattern data
PATTERNS = [
    ("Hammer", "BUY", "Long lower wick"),
    ("Shooting Star", "SELL", "Long upper wick"),
    ("Doji", "NEUTRAL", "Indecision"),
    ("Bullish Engulfing", "BUY", "Bullish reversal"),
    ("Bearish Engulfing", "SELL", "Bearish reversal"),
    ("Morning Star", "BUY", "3-candle reversal"),
    ("Evening Star", "SELL", "3-candle reversal"),
]

class PAScannerApp(App):
    def build(self):
        Window.clearcolor = (0.07, 0.07, 0.07, 1)
        
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Title
        title = Label(
            text='PA Scanner Pro',
            font_size='28sp',
            color=(0, 1, 0, 1),
            size_hint_y=0.15,
            bold=True
        )
        self.layout.add_widget(title)
        
        # Status
        self.status = Label(
            text='Press START to scan',
            font_size='16sp',
            color=(0.7, 0.7, 0.7, 1),
            size_hint_y=0.1
        )
        self.layout.add_widget(self.status)
        
        # Start button
        self.btn = Button(
            text='START SCAN',
            font_size='20sp',
            size_hint_y=0.15,
            background_color=(0, 0.5, 0, 1)
        )
        self.btn.bind(on_press=self.toggle_scan)
        self.layout.add_widget(self.btn)
        
        # Results area
        self.results = Label(
            text='Detected patterns will appear here',
            font_size='14sp',
            color=(0.8, 0.8, 0.8, 1),
            halign='left',
            valign='top',
            text_size=(None, None)
        )
        self.results.bind(size=lambda *x: setattr(self.results, 'text_size', self.results.size))
        self.layout.add_widget(self.results)
        
        self.scanning = False
        self.scan_event = None
        
        return self.layout
    
    def toggle_scan(self, instance):
        if not self.scanning:
            self.scanning = True
            self.btn.text = 'STOP SCAN'
            self.btn.background_color = (0.5, 0, 0, 1)
            self.status.text = 'Scanning...'
            self.status.color = (0, 1, 0, 1)
            self.scan_event = Clock.schedule_interval(self.scan, 2)
        else:
            self.scanning = False
            self.btn.text = 'START SCAN'
            self.btn.background_color = (0, 0.5, 0, 1)
            self.status.text = 'Stopped'
            self.status.color = (0.7, 0.7, 0.7, 1)
            if self.scan_event:
                self.scan_event.cancel()
    
    def scan(self, dt):
        # Simulate pattern detection
        if random.random() < 0.7:  # 70% chance to detect
            pattern = random.choice(PATTERNS)
            time_str = datetime.now().strftime('%H:%M:%S')
            
            color = '[color=00ff00]' if pattern[1] == 'BUY' else '[color=ff0000]' if pattern[1] == 'SELL' else '[color=ffff00]'
            
            new_text = f"{time_str} - {color}{pattern[0]}[/color] ({pattern[1]})\n{pattern[2]}\n\n"
            
            current = self.results.text
            if 'will appear' in current:
                self.results.text = new_text
            else:
                self.results.text = new_text + current[:500]  # Keep last 500 chars
            
            self.results.markup = True

if __name__ == '__main__':
    PAScannerApp().run()
