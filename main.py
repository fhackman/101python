import logging
import threading
import time
import queue
import random
from datetime import datetime
from dataclasses import dataclass
from abc import ABC, abstractmethod
from typing import Optional, List, Tuple

# Kivy Imports
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.metrics import dp
from kivy.properties import StringProperty, ColorProperty, ListProperty

# Data Imports
import pandas as pd
import numpy as np

# -----------------------------------------------------------------------------
# MOCK MT5 FOR ANDROID
# -----------------------------------------------------------------------------
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
    # Mock constants
    class MockMT5:
        TIMEFRAME_M1 = 1
        TIMEFRAME_M5 = 5
        TIMEFRAME_M15 = 15
        TIMEFRAME_M30 = 30
        TIMEFRAME_H1 = 60
        TIMEFRAME_H4 = 240
        TIMEFRAME_D1 = 1440
        
        def initialize(self): return True
        def shutdown(self): pass
        def copy_rates_from_pos(self, symbol, timeframe, start, count):
            # Generate fake candle data for testing/demo
            data = []
            base_price = 2000.0
            for i in range(count):
                open_p = base_price + random.uniform(-5, 5)
                close_p = open_p + random.uniform(-5, 5)
                high_p = max(open_p, close_p) + random.uniform(0, 2)
                low_p = min(open_p, close_p) - random.uniform(0, 2)
                # time in seconds
                t = int(time.time()) - (count - i) * 60 * 60 
                data.append((t, open_p, high_p, low_p, close_p, 100, 0, 0))
                base_price = close_p
            return data

    mt5 = MockMT5()

# -----------------------------------------------------------------------------
# PATTERN LOGIC
# -----------------------------------------------------------------------------

@dataclass
class PatternResult:
    """Result of pattern detection"""
    timestamp: datetime
    pattern_name: str
    pattern_type: str  # 'BUY' or 'SELL'
    price: float
    confidence: int  # 0-100
    strength: str  # 'weak', 'moderate', 'strong'
    description: str
    
class PatternDetector(ABC):
    """Base class for pattern detectors"""
    def __init__(self, name: str, pattern_type: str, candles_required: int):
        self.name = name
        self.pattern_type = pattern_type
        self.candles_required = candles_required
    
    @abstractmethod
    def detect(self, candles: pd.Series) -> Optional[PatternResult]:
        """Detect pattern and return result with confidence"""
        pass
    
    def calculate_strength(self, confidence: int) -> str:
        if confidence >= 80: return 'strong'
        elif confidence >= 60: return 'moderate'
        return 'weak'

# --- SINGLE CANDLE ---

class HammerDetector(PatternDetector):
    def __init__(self): super().__init__("Hammer", "BUY", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['lower_wick'] > (2 * c['body_size']) and c['upper_wick'] < c['body_size']:
            confidence = min(100, int(70 + (c['lower_wick'] / c['body_size']) * 10))
            return PatternResult(c['time'], self.name, self.pattern_type, c['close'], confidence, self.calculate_strength(confidence), "Long lower wick")
        return None

class ShootingStarDetector(PatternDetector):
    def __init__(self): super().__init__("Shooting Star", "SELL", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['upper_wick'] > (2 * c['body_size']) and c['lower_wick'] < c['body_size']:
            confidence = min(100, int(70 + (c['upper_wick'] / c['body_size']) * 10))
            return PatternResult(c['time'], self.name, self.pattern_type, c['close'], confidence, self.calculate_strength(confidence), "Long upper wick")
        return None

class DojiDetector(PatternDetector):
    def __init__(self): super().__init__("Doji", "NEUTRAL", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_doji'] and c['body_size'] < c['total_range'] * 0.05:
            return PatternResult(c['time'], self.name, "NEUTRAL", c['close'], 75, "moderate", "Indecision")
        return None

class DragonflyDojiDetector(PatternDetector):
    def __init__(self): super().__init__("Dragonfly Doji", "BUY", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_doji'] and c['lower_wick'] > c['total_range'] * 0.6 and c['upper_wick'] < c['total_range'] * 0.1:
            return PatternResult(c['time'], self.name, self.pattern_type, c['close'], 80, "strong", "Bullish reversal")
        return None

class GravestoneDojiDetector(PatternDetector):
    def __init__(self): super().__init__("Gravestone Doji", "SELL", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_doji'] and c['upper_wick'] > c['total_range'] * 0.6 and c['lower_wick'] < c['total_range'] * 0.1:
            return PatternResult(c['time'], self.name, self.pattern_type, c['close'], 80, "strong", "Bearish reversal")
        return None

class BullishMarubozuDetector(PatternDetector):
    def __init__(self): super().__init__("Bullish Marubozu", "BUY", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_bullish'] and c['body_size'] > c['total_range'] * 0.9:
            return PatternResult(c['time'], self.name, self.pattern_type, c['close'], 85, "strong", "Strong bullish")
        return None

class BearishMarubozuDetector(PatternDetector):
    def __init__(self): super().__init__("Bearish Marubozu", "SELL", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_bearish'] and c['body_size'] > c['total_range'] * 0.9:
            return PatternResult(c['time'], self.name, self.pattern_type, c['close'], 85, "strong", "Strong bearish")
        return None

class SpinningTopDetector(PatternDetector):
    def __init__(self): super().__init__("Spinning Top", "NEUTRAL", 1)
    def detect(self, candles):
        c = candles.iloc[-1]
        if (c['body_size'] < c['total_range'] * 0.3 and c['upper_wick'] > c['body_size'] and c['lower_wick'] > c['body_size']):
            return PatternResult(c['time'], self.name, "NEUTRAL", c['close'], 70, "moderate", "Indecision")
        return None

# --- TWO CANDLE ---

class BullishEngulfingDetector(PatternDetector):
    def __init__(self): super().__init__("Bullish Engulfing", "BUY", 2)
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['close'] > prev['open'] and curr['open'] < prev['close']:
                confidence = 85
                return PatternResult(curr['time'], self.name, self.pattern_type, curr['close'], confidence, self.calculate_strength(confidence), "Bullish engulfing")
        return None

class BearishEngulfingDetector(PatternDetector):
    def __init__(self): super().__init__("Bearish Engulfing", "SELL", 2)
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['close'] < prev['open'] and curr['open'] > prev['close']:
                confidence = 85
                return PatternResult(curr['time'], self.name, self.pattern_type, curr['close'], confidence, self.calculate_strength(confidence), "Bearish engulfing")
        return None

class PiercingLineDetector(PatternDetector):
    def __init__(self): super().__init__("Piercing Line", "BUY", 2)
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        prev_midpoint = (prev['open'] + prev['close']) / 2
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['open'] < prev['close'] and curr['close'] > prev_midpoint and curr['close'] < prev['open']:
                return PatternResult(curr['time'], self.name, self.pattern_type, curr['close'], 80, "strong", "Bullish reversal")
        return None

class DarkCloudCoverDetector(PatternDetector):
    def __init__(self): super().__init__("Dark Cloud Cover", "SELL", 2)
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        prev_midpoint = (prev['open'] + prev['close']) / 2
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['open'] > prev['close'] and curr['close'] < prev_midpoint and curr['close'] > prev['open']:
                return PatternResult(curr['time'], self.name, self.pattern_type, curr['close'], 80, "strong", "Bearish reversal")
        return None

class BullishHaramiDetector(PatternDetector):
    def __init__(self): super().__init__("Bullish Harami", "BUY", 2)
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bearish'] and curr['is_bullish']:
            if (curr['open'] > prev['close'] and curr['close'] < prev['open'] and curr['body_size'] < prev['body_size'] * 0.7):
                return PatternResult(curr['time'], self.name, self.pattern_type, curr['close'], 75, "moderate", "Inside bar")
        return None

class BearishHaramiDetector(PatternDetector):
    def __init__(self): super().__init__("Bearish Harami", "SELL", 2)
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bullish'] and curr['is_bearish']:
            if (curr['close'] > prev['open'] and curr['open'] < prev['close'] and curr['body_size'] < prev['body_size'] * 0.7):
                return PatternResult(curr['time'], self.name, self.pattern_type, curr['close'], 75, "moderate", "Inside bar")
        return None

# --- THREE CANDLE ---

class MorningStarDetector(PatternDetector):
    def __init__(self): super().__init__("Morning Star", "BUY", 3)
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bearish'] and c3['is_bullish']:
            if (c1['body_size'] > c2['body_size'] * 2 and c2['body_size'] < c1['body_size'] * 0.3 and c3['close'] > (c1['open'] + c1['close'])/2):
                return PatternResult(c3['time'], self.name, self.pattern_type, c3['close'], 85, "strong", "Morning Star")
        return None

class EveningStarDetector(PatternDetector):
    def __init__(self): super().__init__("Evening Star", "SELL", 3)
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bullish'] and c3['is_bearish']:
            if (c1['body_size'] > c2['body_size'] * 2 and c2['body_size'] < c1['body_size'] * 0.3 and c3['close'] < (c1['open'] + c1['close'])/2):
                return PatternResult(c3['time'], self.name, self.pattern_type, c3['close'], 85, "strong", "Evening Star")
        return None

class ThreeWhiteSoldiersDetector(PatternDetector):
    def __init__(self): super().__init__("Three White Soldiers", "BUY", 3)
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bullish'] and c2['is_bullish'] and c3['is_bullish']:
            if (c2['close'] > c1['close'] and c3['close'] > c2['close'] and c1['body_size'] > c1['total_range'] * 0.6):
                return PatternResult(c3['time'], self.name, self.pattern_type, c3['close'], 90, "strong", "3 White Soldiers")
        return None

class ThreeBlackCrowsDetector(PatternDetector):
    def __init__(self): super().__init__("Three Black Crows", "SELL", 3)
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bearish'] and c2['is_bearish'] and c3['is_bearish']:
            if (c2['close'] < c1['close'] and c3['close'] < c2['close'] and c1['body_size'] > c1['total_range'] * 0.6):
                return PatternResult(c3['time'], self.name, self.pattern_type, c3['close'], 90, "strong", "3 Black Crows")
        return None

# -----------------------------------------------------------------------------
# SCANNER LOGIC
# -----------------------------------------------------------------------------

class PAPatternScanner:
    def __init__(self, symbol="XAUUSD.m", timeframe=mt5.TIMEFRAME_H1):
        self.symbol = symbol
        self.timeframe = timeframe
        self.connected = False
        self.cached_candles = None
        self.cache_time = 0
        self.pattern_detectors = self._initialize_detectors()
        
    def _initialize_detectors(self) -> List[PatternDetector]:
        return [
            HammerDetector(), ShootingStarDetector(), DojiDetector(), DragonflyDojiDetector(),
            GravestoneDojiDetector(), BullishMarubozuDetector(), BearishMarubozuDetector(),
            SpinningTopDetector(), BullishEngulfingDetector(), BearishEngulfingDetector(),
            PiercingLineDetector(), DarkCloudCoverDetector(), BullishHaramiDetector(),
            BearishHaramiDetector(), MorningStarDetector(), EveningStarDetector(),
            ThreeWhiteSoldiersDetector(), ThreeBlackCrowsDetector()
        ]
    
    def connect(self):
        if not mt5.initialize(): return False
        self.connected = True
        return True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def fetch_candles(self, n=100, force_refresh=False):
        current_time = time.time()
        if not force_refresh and self.cached_candles is not None and (current_time - self.cache_time) < 5:
            return self.cached_candles
            
        if not self.connected: return None
            
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, n)
        if rates is None: return None
        
        # Handle Mock Data (list of tuples) vs Real Data (numpy array)
        if isinstance(rates, list):
            df = pd.DataFrame(rates, columns=['time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'])
        else:
            df = pd.DataFrame(rates)
            
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Enhanced candle properties
        df['body_top'] = df[['open', 'close']].max(axis=1)
        df['body_bottom'] = df[['open', 'close']].min(axis=1)
        df['body_size'] = df['body_top'] - df['body_bottom']
        df['total_range'] = df['high'] - df['low']
        df['upper_wick'] = df['high'] - df['body_top']
        df['lower_wick'] = df['body_bottom'] - df['low']
        df['is_bullish'] = df['close'] > df['open']
        df['is_bearish'] = df['close'] < df['open']
        df['is_doji'] = df['body_size'] < (df['total_range'] * 0.1)
        
        self.cached_candles = df
        self.cache_time = current_time
        return df

    def scan_once(self):
        df = self.fetch_candles()
        if df is None or len(df) < 3: return []
        found_patterns = []
        start_idx = max(2, len(df) - 8)
        for i in range(start_idx, len(df)):
            for detector in self.pattern_detectors:
                if i < detector.candles_required - 1: continue
                candles = df.iloc[i - detector.candles_required + 1 : i + 1]
                result = detector.detect(candles)
                if result: found_patterns.append(result)
        return found_patterns

# -----------------------------------------------------------------------------
# KIVY GUI
# -----------------------------------------------------------------------------

KV = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

<FlatButton@Button>:
    background_normal: ''
    background_down: ''
    background_color: get_color_from_hex('#333333')
    color: get_color_from_hex('#ffffff')
    font_size: '16sp'
    bold: True
    canvas.before:
        Color:
            rgba: get_color_from_hex('#444444') if self.state == 'normal' else get_color_from_hex('#555555')
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [5]

<ModernInput@TextInput>:
    background_normal: ''
    background_active: ''
    background_color: get_color_from_hex('#222222')
    foreground_color: get_color_from_hex('#ffffff')
    cursor_color: get_color_from_hex('#00ff00')
    padding: [10, 10]
    font_size: '16sp'
    multiline: False
    canvas.after:
        Color:
            rgba: get_color_from_hex('#444444')
        Line:
            width: 1
            rectangle: self.x, self.y, self.width, self.height

<ResultCard@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(80)
    padding: dp(10)
    spacing: dp(5)
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8]
    
    bg_color: get_color_from_hex('#333333')
    time_text: ''
    pattern_text: ''
    type_text: ''
    strength_text: ''
    
    BoxLayout:
        size_hint_y: None
        height: dp(20)
        Label:
            text: root.time_text
            font_size: '12sp'
            color: get_color_from_hex('#aaaaaa')
            text_size: self.size
            halign: 'left'
            valign: 'middle'
        Label:
            text: root.strength_text
            font_size: '12sp'
            color: get_color_from_hex('#aaaaaa')
            text_size: self.size
            halign: 'right'
            valign: 'middle'
            
    Label:
        text: root.pattern_text
        font_size: '18sp'
        bold: True
        color: get_color_from_hex('#ffffff')
        text_size: self.size
        halign: 'left'
        valign: 'middle'
        
    Label:
        text: root.type_text
        font_size: '14sp'
        color: get_color_from_hex('#ffffff')
        text_size: self.size
        halign: 'left'
        valign: 'middle'

BoxLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: get_color_from_hex('#121212')
        Rectangle:
            pos: self.pos
            size: self.size

    # Header
    BoxLayout:
        size_hint_y: None
        height: dp(60)
        padding: dp(15)
        canvas.before:
            Color:
                rgba: get_color_from_hex('#1e1e1e')
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "PA Scanner Pro"
            font_size: '24sp'
            bold: True
            color: get_color_from_hex('#00ff00')
            text_size: self.size
            halign: 'left'
            valign: 'middle'

    # Control Panel
    GridLayout:
        cols: 2
        size_hint_y: None
        height: dp(140)
        padding: dp(10)
        spacing: dp(10)
        
        BoxLayout:
            orientation: 'vertical'
            spacing: dp(5)
            Label:
                text: "Symbol"
                size_hint_y: None
                height: dp(20)
                text_size: self.size
                halign: 'left'
                color: get_color_from_hex('#aaaaaa')
            ModernInput:
                id: symbol_input
                text: "XAUUSD.m"
                
        BoxLayout:
            orientation: 'vertical'
            spacing: dp(5)
            Label:
                text: "Timeframe"
                size_hint_y: None
                height: dp(20)
                text_size: self.size
                halign: 'left'
                color: get_color_from_hex('#aaaaaa')
            Spinner:
                id: tf_spinner
                text: 'H1'
                values: ('M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1')
                background_normal: ''
                background_color: get_color_from_hex('#222222')
                color: get_color_from_hex('#ffffff')
                
        FlatButton:
            id: btn_start
            text: "START SCAN"
            background_color: get_color_from_hex('#006400')
            on_press: app.toggle_scan()
            
        Label:
            id: status_label
            text: "Status: Idle"
            color: get_color_from_hex('#666666')

    # Trading Panel
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: dp(120)
        padding: dp(10)
        spacing: dp(10)
        canvas.before:
            Color:
                rgba: get_color_from_hex('#1a1a1a')
            RoundedRectangle:
                pos: self.pos
                size: self.size
                radius: [8]
        
        BoxLayout:
            spacing: dp(10)
            ModernInput:
                id: lot_input
                text: "0.01"
                hint_text: "Lot"
            ModernInput:
                id: tp_input
                text: "1000"
                hint_text: "TP"
            ModernInput:
                id: sl_input
                text: "200"
                hint_text: "SL"
                
        BoxLayout:
            spacing: dp(10)
            FlatButton:
                text: "BUY"
                background_color: get_color_from_hex('#0000aa')
                on_press: app.execute_trade("BUY")
            FlatButton:
                text: "SELL"
                background_color: get_color_from_hex('#aa0000')
                on_press: app.execute_trade("SELL")

    # Results Area
    Label:
        text: "DETECTED PATTERNS"
        size_hint_y: None
        height: dp(30)
        font_size: '14sp'
        color: get_color_from_hex('#666666')
        bold: True

    ScrollView:
        GridLayout:
            id: results_container
            cols: 1
            spacing: dp(5)
            padding: dp(10)
            size_hint_y: None
            height: self.minimum_height
'''

class ResultCard(BoxLayout):
    bg_color = ColorProperty()
    time_text = StringProperty()
    pattern_text = StringProperty()
    type_text = StringProperty()
    strength_text = StringProperty()

class PAScannerApp(App):
    def build(self):
        Window.clearcolor = get_color_from_hex('#121212')
        self.scanner = PAPatternScanner()
        self.is_scanning = False
        self.scan_queue = queue.Queue()
        
        self.root_widget = Builder.load_string(KV)
        
        # Clock for checking queue
        Clock.schedule_interval(self.update_ui, 1.0)
        
        return self.root_widget

    def toggle_scan(self):
        btn = self.root_widget.ids.btn_start
        status = self.root_widget.ids.status_label
        
        if not self.is_scanning:
            # Start
            self.is_scanning = True
            btn.text = "STOP SCAN"
            # btn.background_color = get_color_from_hex('#8b0000') # Handled by KV logic if bound, but here manual
            status.text = "Scanning..."
            status.color = get_color_from_hex('#00ff00')
            
            # Update scanner settings
            tf_map = {
                "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
                "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
                "D1": mt5.TIMEFRAME_D1
            }
            self.scanner.symbol = self.root_widget.ids.symbol_input.text
            self.scanner.timeframe = tf_map.get(self.root_widget.ids.tf_spinner.text, mt5.TIMEFRAME_H1)
            self.scanner.connect()
            
            threading.Thread(target=self.scan_loop, daemon=True).start()
        else:
            # Stop
            self.is_scanning = False
            btn.text = "START SCAN"
            status.text = "Stopped"
            status.color = get_color_from_hex('#666666')
            self.scanner.disconnect()

    def scan_loop(self):
        while self.is_scanning:
            try:
                patterns = self.scanner.scan_once()
                if patterns:
                    self.scan_queue.put(patterns)
            except Exception as e:
                print(f"Scan error: {e}")
            time.sleep(2) # Scan every 2 seconds

    def update_ui(self, dt):
        try:
            while True:
                patterns = self.scan_queue.get_nowait()
                for p in patterns:
                    self.add_result(p)
        except queue.Empty:
            pass

    def add_result(self, result):
        container = self.root_widget.ids.results_container
        
        # Color coding
        if result.pattern_type == 'BUY':
            bg = get_color_from_hex('#1b5e20') # Dark Green
        elif result.pattern_type == 'SELL':
            bg = get_color_from_hex('#b71c1c') # Dark Red
        else:
            bg = get_color_from_hex('#f57f17') # Dark Orange
            
        card = ResultCard(
            bg_color=bg,
            time_text=result.timestamp.strftime('%H:%M:%S'),
            pattern_text=result.pattern_name,
            type_text=f"{result.pattern_type} - {result.description}",
            strength_text=f"Confidence: {result.confidence}%"
        )
        
        container.add_widget(card, index=0) # Add to top
        
        # Keep list manageable
        if len(container.children) > 50:
            container.remove_widget(container.children[-1])

    def execute_trade(self, direction):
        tp = self.root_widget.ids.tp_input.text
        sl = self.root_widget.ids.sl_input.text
        lot = self.root_widget.ids.lot_input.text
        
        if not MT5_AVAILABLE:
            msg = f"SIMULATION: {direction} Order Sent!\nLot: {lot}, TP: {tp}, SL: {sl}"
        else:
            msg = f"MT5 {direction} Order Sent!\nLot: {lot}, TP: {tp}, SL: {sl}"
            
        self.root_widget.ids.status_label.text = msg
        print(msg)

if __name__ == '__main__':
    PAScannerApp().run()
