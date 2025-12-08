"""
PA Scanner Pro - Android Version
Candlestick Pattern Detection without pandas/numpy for Android compatibility
"""
import threading
import time
import queue
import random
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List

# Kivy Imports
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.properties import StringProperty, ColorProperty

# -----------------------------------------------------------------------------
# MOCK MT5 FOR ANDROID - Generates demo data
# -----------------------------------------------------------------------------
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
        data = []
        base_price = 2000.0
        for i in range(count):
            open_p = base_price + random.uniform(-5, 5)
            close_p = open_p + random.uniform(-5, 5)
            high_p = max(open_p, close_p) + random.uniform(0, 2)
            low_p = min(open_p, close_p) - random.uniform(0, 2)
            t = int(time.time()) - (count - i) * 60 * 60
            data.append({
                'time': t, 'open': open_p, 'high': high_p, 
                'low': low_p, 'close': close_p
            })
            base_price = close_p
        return data

mt5 = MockMT5()

# -----------------------------------------------------------------------------
# CANDLE DATA CLASS
# -----------------------------------------------------------------------------
@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    body_top: float = 0
    body_bottom: float = 0
    body_size: float = 0
    total_range: float = 0
    upper_wick: float = 0
    lower_wick: float = 0
    is_bullish: bool = False
    is_bearish: bool = False
    is_doji: bool = False
    
    def __post_init__(self):
        self.body_top = max(self.open, self.close)
        self.body_bottom = min(self.open, self.close)
        self.body_size = self.body_top - self.body_bottom
        self.total_range = self.high - self.low if self.high > self.low else 0.0001
        self.upper_wick = self.high - self.body_top
        self.lower_wick = self.body_bottom - self.low
        self.is_bullish = self.close > self.open
        self.is_bearish = self.close < self.open
        self.is_doji = self.body_size < (self.total_range * 0.1)

@dataclass
class PatternResult:
    timestamp: datetime
    pattern_name: str
    pattern_type: str
    price: float
    confidence: int
    strength: str
    description: str

# -----------------------------------------------------------------------------
# PATTERN DETECTORS - Pure Python
# -----------------------------------------------------------------------------
def detect_hammer(c: Candle) -> Optional[PatternResult]:
    if c.body_size > 0 and c.lower_wick > (2 * c.body_size) and c.upper_wick < c.body_size:
        conf = min(100, int(70 + (c.lower_wick / c.body_size) * 10))
        return PatternResult(c.time, "Hammer", "BUY", c.close, conf, "strong" if conf >= 80 else "moderate", "Long lower wick")
    return None

def detect_shooting_star(c: Candle) -> Optional[PatternResult]:
    if c.body_size > 0 and c.upper_wick > (2 * c.body_size) and c.lower_wick < c.body_size:
        conf = min(100, int(70 + (c.upper_wick / c.body_size) * 10))
        return PatternResult(c.time, "Shooting Star", "SELL", c.close, conf, "strong" if conf >= 80 else "moderate", "Long upper wick")
    return None

def detect_doji(c: Candle) -> Optional[PatternResult]:
    if c.is_doji and c.body_size < c.total_range * 0.05:
        return PatternResult(c.time, "Doji", "NEUTRAL", c.close, 75, "moderate", "Indecision")
    return None

def detect_dragonfly_doji(c: Candle) -> Optional[PatternResult]:
    if c.is_doji and c.lower_wick > c.total_range * 0.6 and c.upper_wick < c.total_range * 0.1:
        return PatternResult(c.time, "Dragonfly Doji", "BUY", c.close, 80, "strong", "Bullish reversal")
    return None

def detect_gravestone_doji(c: Candle) -> Optional[PatternResult]:
    if c.is_doji and c.upper_wick > c.total_range * 0.6 and c.lower_wick < c.total_range * 0.1:
        return PatternResult(c.time, "Gravestone Doji", "SELL", c.close, 80, "strong", "Bearish reversal")
    return None

def detect_marubozu(c: Candle) -> Optional[PatternResult]:
    if c.body_size > c.total_range * 0.9:
        if c.is_bullish:
            return PatternResult(c.time, "Bullish Marubozu", "BUY", c.close, 85, "strong", "Strong bullish")
        elif c.is_bearish:
            return PatternResult(c.time, "Bearish Marubozu", "SELL", c.close, 85, "strong", "Strong bearish")
    return None

def detect_engulfing(prev: Candle, curr: Candle) -> Optional[PatternResult]:
    if prev.is_bearish and curr.is_bullish:
        if curr.close > prev.open and curr.open < prev.close:
            return PatternResult(curr.time, "Bullish Engulfing", "BUY", curr.close, 85, "strong", "Bullish engulfing")
    elif prev.is_bullish and curr.is_bearish:
        if curr.close < prev.open and curr.open > prev.close:
            return PatternResult(curr.time, "Bearish Engulfing", "SELL", curr.close, 85, "strong", "Bearish engulfing")
    return None

def detect_morning_star(c1: Candle, c2: Candle, c3: Candle) -> Optional[PatternResult]:
    if c1.is_bearish and c3.is_bullish:
        if c1.body_size > c2.body_size * 2 and c2.body_size < c1.body_size * 0.3:
            if c3.close > (c1.open + c1.close) / 2:
                return PatternResult(c3.time, "Morning Star", "BUY", c3.close, 85, "strong", "Morning Star")
    return None

def detect_evening_star(c1: Candle, c2: Candle, c3: Candle) -> Optional[PatternResult]:
    if c1.is_bullish and c3.is_bearish:
        if c1.body_size > c2.body_size * 2 and c2.body_size < c1.body_size * 0.3:
            if c3.close < (c1.open + c1.close) / 2:
                return PatternResult(c3.time, "Evening Star", "SELL", c3.close, 85, "strong", "Evening Star")
    return None

def detect_three_soldiers(c1: Candle, c2: Candle, c3: Candle) -> Optional[PatternResult]:
    if c1.is_bullish and c2.is_bullish and c3.is_bullish:
        if c2.close > c1.close and c3.close > c2.close:
            return PatternResult(c3.time, "Three White Soldiers", "BUY", c3.close, 90, "strong", "3 White Soldiers")
    return None

def detect_three_crows(c1: Candle, c2: Candle, c3: Candle) -> Optional[PatternResult]:
    if c1.is_bearish and c2.is_bearish and c3.is_bearish:
        if c2.close < c1.close and c3.close < c2.close:
            return PatternResult(c3.time, "Three Black Crows", "SELL", c3.close, 90, "strong", "3 Black Crows")
    return None

# -----------------------------------------------------------------------------
# SCANNER
# -----------------------------------------------------------------------------
class PAPatternScanner:
    def __init__(self, symbol="XAUUSD", timeframe=60):
        self.symbol = symbol
        self.timeframe = timeframe
        self.connected = False
        
    def connect(self):
        self.connected = mt5.initialize()
        return self.connected

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def fetch_candles(self, n=50) -> List[Candle]:
        if not self.connected: return []
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, n)
        if not rates: return []
        candles = []
        for r in rates:
            candles.append(Candle(
                time=datetime.fromtimestamp(r['time']),
                open=r['open'], high=r['high'], low=r['low'], close=r['close']
            ))
        return candles

    def scan_once(self) -> List[PatternResult]:
        candles = self.fetch_candles()
        if len(candles) < 3: return []
        patterns = []
        
        # Check last 8 candles
        for i in range(max(0, len(candles) - 8), len(candles)):
            c = candles[i]
            # Single candle patterns
            for detector in [detect_hammer, detect_shooting_star, detect_doji, 
                           detect_dragonfly_doji, detect_gravestone_doji, detect_marubozu]:
                result = detector(c)
                if result: patterns.append(result)
            
            # Two candle patterns
            if i >= 1:
                result = detect_engulfing(candles[i-1], c)
                if result: patterns.append(result)
            
            # Three candle patterns
            if i >= 2:
                for detector in [detect_morning_star, detect_evening_star, 
                               detect_three_soldiers, detect_three_crows]:
                    result = detector(candles[i-2], candles[i-1], c)
                    if result: patterns.append(result)
        return patterns

# -----------------------------------------------------------------------------
# KIVY GUI
# -----------------------------------------------------------------------------
KV = '''
#:import get_color_from_hex kivy.utils.get_color_from_hex

<ResultCard@BoxLayout>:
    orientation: 'vertical'
    size_hint_y: None
    height: dp(70)
    padding: dp(8)
    spacing: dp(3)
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [8]
    bg_color: [0.2, 0.2, 0.2, 1]
    time_text: ''
    pattern_text: ''
    type_text: ''
    
    BoxLayout:
        Label:
            text: root.time_text
            font_size: '11sp'
            color: [0.7, 0.7, 0.7, 1]
            text_size: self.size
            halign: 'left'
    Label:
        text: root.pattern_text
        font_size: '16sp'
        bold: True
        color: [1, 1, 1, 1]
        text_size: self.size
        halign: 'left'
    Label:
        text: root.type_text
        font_size: '12sp'
        color: [0.9, 0.9, 0.9, 1]
        text_size: self.size
        halign: 'left'

BoxLayout:
    orientation: 'vertical'
    canvas.before:
        Color:
            rgba: [0.07, 0.07, 0.07, 1]
        Rectangle:
            pos: self.pos
            size: self.size

    # Header
    BoxLayout:
        size_hint_y: None
        height: dp(50)
        padding: dp(10)
        canvas.before:
            Color:
                rgba: [0.12, 0.12, 0.12, 1]
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: "PA Scanner Pro"
            font_size: '22sp'
            bold: True
            color: [0, 1, 0, 1]

    # Control
    BoxLayout:
        size_hint_y: None
        height: dp(60)
        padding: dp(10)
        spacing: dp(10)
        
        Button:
            id: btn_start
            text: "START"
            background_color: [0, 0.4, 0, 1]
            on_press: app.toggle_scan()
            
        Label:
            id: status_label
            text: "Idle"
            color: [0.5, 0.5, 0.5, 1]

    # Pattern List
    Label:
        text: "DETECTED PATTERNS"
        size_hint_y: None
        height: dp(25)
        font_size: '12sp'
        color: [0.5, 0.5, 0.5, 1]

    ScrollView:
        GridLayout:
            id: results_container
            cols: 1
            spacing: dp(5)
            padding: dp(8)
            size_hint_y: None
            height: self.minimum_height
'''

class ResultCard(BoxLayout):
    bg_color = ColorProperty([0.2, 0.2, 0.2, 1])
    time_text = StringProperty('')
    pattern_text = StringProperty('')
    type_text = StringProperty('')

class PAScannerApp(App):
    def build(self):
        Window.clearcolor = (0.07, 0.07, 0.07, 1)
        self.scanner = PAPatternScanner()
        self.is_scanning = False
        self.scan_queue = queue.Queue()
        self.root_widget = Builder.load_string(KV)
        Clock.schedule_interval(self.update_ui, 1.0)
        return self.root_widget

    def toggle_scan(self):
        btn = self.root_widget.ids.btn_start
        status = self.root_widget.ids.status_label
        
        if not self.is_scanning:
            self.is_scanning = True
            btn.text = "STOP"
            status.text = "Scanning..."
            status.color = [0, 1, 0, 1]
            self.scanner.connect()
            threading.Thread(target=self.scan_loop, daemon=True).start()
        else:
            self.is_scanning = False
            btn.text = "START"
            status.text = "Stopped"
            status.color = [0.5, 0.5, 0.5, 1]
            self.scanner.disconnect()

    def scan_loop(self):
        while self.is_scanning:
            try:
                patterns = self.scanner.scan_once()
                if patterns:
                    self.scan_queue.put(patterns)
            except Exception as e:
                print(f"Error: {e}")
            time.sleep(2)

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
        
        if result.pattern_type == 'BUY':
            bg = [0.1, 0.35, 0.1, 1]
        elif result.pattern_type == 'SELL':
            bg = [0.45, 0.1, 0.1, 1]
        else:
            bg = [0.4, 0.35, 0.1, 1]
            
        card = ResultCard(
            bg_color=bg,
            time_text=result.timestamp.strftime('%H:%M:%S'),
            pattern_text=result.pattern_name,
            type_text=f"{result.pattern_type} - {result.description} ({result.confidence}%)"
        )
        container.add_widget(card, index=0)
        
        if len(container.children) > 30:
            container.remove_widget(container.children[-1])

if __name__ == '__main__':
    PAScannerApp().run()
