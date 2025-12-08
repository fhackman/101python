import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Tuple

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)

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

class PAPatternScanner:
    def __init__(self, symbol="XAUUSD.m", timeframe=mt5.TIMEFRAME_H1):
        self.symbol = symbol
        self.timeframe = timeframe
        self.connected = False
        self.cached_candles = None
        self.cache_time = 0
        self.pattern_detectors = self._initialize_detectors()
        
    def _initialize_detectors(self) -> List[PatternDetector]:
        """Initialize all pattern detectors"""
        return [
            # Single candle patterns
            HammerDetector(),
            ShootingStarDetector(),
            DojiDetector(),
            DragonflyDojiDetector(),
            GravestoneDojiDetector(),
            BullishMarubozuDetector(),
            BearishMarubozuDetector(),
            SpinningTopDetector(),
            
            # Two candle patterns
            BullishEngulfingDetector(),
            BearishEngulfingDetector(),
            PiercingLineDetector(),
            DarkCloudCoverDetector(),
            BullishHaramiDetector(),
            BearishHaramiDetector(),
            TweezerBottomDetector(),
            TweezerTopDetector(),
            
            # Three candle patterns
            MorningStarDetector(),
            EveningStarDetector(),
            ThreeWhiteSoldiersDetector(),
            ThreeBlackCrowsDetector(),
            ThreeInsideUpDetector(),
            ThreeInsideDownDetector(),
            ThreeOutsideUpDetector(),
            ThreeOutsideDownDetector(),
            AbandonedBabyBullishDetector(),
            AbandonedBabyBearishDetector(),
        ]
    
    def connect(self):
        if not mt5.initialize():
            return False
        self.connected = True
        return True

    def disconnect(self):
        mt5.shutdown()
        self.connected = False

    def fetch_candles(self, n=100, force_refresh=False):
        # Cache for 5 seconds to improve performance
        current_time = time.time()
        if not force_refresh and self.cached_candles is not None and (current_time - self.cache_time) < 5:
            return self.cached_candles
            
        if not self.connected:
            return None
            
        rates = mt5.copy_rates_from_pos(self.symbol, self.timeframe, 0, n)
        if rates is None:
            return None
        
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s') + pd.Timedelta(hours=7)
        
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
        """Scan for all patterns"""
        df = self.fetch_candles()
        if df is None or len(df) < 3:
            return []

        found_patterns = []
        
        # Scan last 8 candles for efficiency
        start_idx = max(2, len(df) - 8)
        
        for i in range(start_idx, len(df)):
            for detector in self.pattern_detectors:
                if i < detector.candles_required - 1:
                    continue
                    
                # Get required candles
                candles = df.iloc[i - detector.candles_required + 1 : i + 1]
                
                result = detector.detect(candles)
                if result:
                    found_patterns.append(result)
        
        return found_patterns

# ============================================
# SINGLE CANDLE PATTERN DETECTORS
# ============================================

class HammerDetector(PatternDetector):
    def __init__(self):
        super().__init__("Hammer", "BUY", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['lower_wick'] > (2 * c['body_size']) and c['upper_wick'] < c['body_size']:
            confidence = min(100, int(70 + (c['lower_wick'] / c['body_size']) * 10))
            return PatternResult(
                c['time'], self.name, self.pattern_type, c['close'],
                confidence, self.calculate_strength(confidence),
                "Long lower wick indicates buying pressure"
            )
        return None

class ShootingStarDetector(PatternDetector):
    def __init__(self):
        super().__init__("Shooting Star", "SELL", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['upper_wick'] > (2 * c['body_size']) and c['lower_wick'] < c['body_size']:
            confidence = min(100, int(70 + (c['upper_wick'] / c['body_size']) * 10))
            return PatternResult(
                c['time'], self.name, self.pattern_type, c['close'],
                confidence, self.calculate_strength(confidence),
                "Long upper wick indicates selling pressure"
            )
        return None

class DojiDetector(PatternDetector):
    def __init__(self):
        super().__init__("Doji", "NEUTRAL", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_doji'] and c['body_size'] < c['total_range'] * 0.05:
            confidence = 75
            return PatternResult(
                c['time'], self.name, "NEUTRAL", c['close'],
                confidence, self.calculate_strength(confidence),
                "Indecision candle"
            )
        return None

class DragonflyDojiDetector(PatternDetector):
    def __init__(self):
        super().__init__("Dragonfly Doji", "BUY", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_doji'] and c['lower_wick'] > c['total_range'] * 0.6 and c['upper_wick'] < c['total_range'] * 0.1:
            confidence = 80
            return PatternResult(
                c['time'], self.name, self.pattern_type, c['close'],
                confidence, self.calculate_strength(confidence),
                "Doji with long lower wick - bullish reversal"
            )
        return None

class GravestoneDojiDetector(PatternDetector):
    def __init__(self):
        super().__init__("Gravestone Doji", "SELL", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_doji'] and c['upper_wick'] > c['total_range'] * 0.6 and c['lower_wick'] < c['total_range'] * 0.1:
            confidence = 80
            return PatternResult(
                c['time'], self.name, self.pattern_type, c['close'],
                confidence, self.calculate_strength(confidence),
                "Doji with long upper wick - bearish reversal"
            )
        return None

class BullishMarubozuDetector(PatternDetector):
    def __init__(self):
        super().__init__("Bullish Marubozu", "BUY", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_bullish'] and c['body_size'] > c['total_range'] * 0.9:
            confidence = 85
            return PatternResult(
                c['time'], self.name, self.pattern_type, c['close'],
                confidence, self.calculate_strength(confidence),
                "Strong bullish candle with no wicks"
            )
        return None

class BearishMarubozuDetector(PatternDetector):
    def __init__(self):
        super().__init__("Bearish Marubozu", "SELL", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if c['is_bearish'] and c['body_size'] > c['total_range'] * 0.9:
            confidence = 85
            return PatternResult(
                c['time'], self.name, self.pattern_type, c['close'],
                confidence, self.calculate_strength(confidence),
                "Strong bearish candle with no wicks"
            )
        return None

class SpinningTopDetector(PatternDetector):
    def __init__(self):
        super().__init__("Spinning Top", "NEUTRAL", 1)
    
    def detect(self, candles):
        c = candles.iloc[-1]
        if (c['body_size'] < c['total_range'] * 0.3 and 
            c['upper_wick'] > c['body_size'] and c['lower_wick'] > c['body_size']):
            confidence = 70
            return PatternResult(
                c['time'], self.name, "NEUTRAL", c['close'],
                confidence, self.calculate_strength(confidence),
                "Small body with long wicks - indecision"
            )
        return None

# ============================================
# TWO CANDLE PATTERN DETECTORS
# ============================================

class BullishEngulfingDetector(PatternDetector):
    def __init__(self):
        super().__init__("Bullish Engulfing", "BUY", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['close'] > prev['open'] and curr['open'] < prev['close']:
                engulf_ratio = curr['body_size'] / prev['body_size']
                confidence = min(95, int(75 + engulf_ratio * 20))
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Bullish candle engulfs previous bearish"
                )
        return None

class BearishEngulfingDetector(PatternDetector):
    def __init__(self):
        super().__init__("Bearish Engulfing", "SELL", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['close'] < prev['open'] and curr['open'] > prev['close']:
                engulf_ratio = curr['body_size'] / prev['body_size']
                confidence = min(95, int(75 + engulf_ratio * 20))
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Bearish candle engulfs previous bullish"
                )
        return None

class PiercingLineDetector(PatternDetector):
    def __init__(self):
        super().__init__("Piercing Line", "BUY", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        prev_midpoint = (prev['open'] + prev['close']) / 2
        if prev['is_bearish'] and curr['is_bullish']:
            if curr['open'] < prev['close'] and curr['close'] > prev_midpoint and curr['close'] < prev['open']:
                confidence = 80
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Bullish reversal - closes above midpoint"
                )
        return None

class DarkCloudCoverDetector(PatternDetector):
    def __init__(self):
        super().__init__("Dark Cloud Cover", "SELL", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        prev_midpoint = (prev['open'] + prev['close']) / 2
        if prev['is_bullish'] and curr['is_bearish']:
            if curr['open'] > prev['close'] and curr['close'] < prev_midpoint and curr['close'] > prev['open']:
                confidence = 80
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Bearish reversal - closes below midpoint"
                )
        return None

class BullishHaramiDetector(PatternDetector):
    def __init__(self):
        super().__init__("Bullish Harami", "BUY", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bearish'] and curr['is_bullish']:
            if (curr['open'] > prev['close'] and curr['close'] < prev['open'] and
                curr['body_size'] < prev['body_size'] * 0.7):
                confidence = 75
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Small bullish inside previous bearish"
                )
        return None

class BearishHaramiDetector(PatternDetector):
    def __init__(self):
        super().__init__("Bearish Harami", "SELL", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bullish'] and curr['is_bearish']:
            if (curr['close'] > prev['open'] and curr['open'] < prev['close'] and
                curr['body_size'] < prev['body_size'] * 0.7):
                confidence = 75
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Small bearish inside previous bullish"
                )
        return None

class TweezerBottomDetector(PatternDetector):
    def __init__(self):
        super().__init__("Tweezer Bottom", "BUY", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bearish'] and curr['is_bullish']:
            if abs(prev['low'] - curr['low']) < prev['total_range'] * 0.05:
                confidence = 78
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Double bottom support - reversal signal"
                )
        return None

class TweezerTopDetector(PatternDetector):
    def __init__(self):
        super().__init__("Tweezer Top", "SELL", 2)
    
    def detect(self, candles):
        prev, curr = candles.iloc[-2], candles.iloc[-1]
        if prev['is_bullish'] and curr['is_bearish']:
            if abs(prev['high'] - curr['high']) < prev['total_range'] * 0.05:
                confidence = 78
                return PatternResult(
                    curr['time'], self.name, self.pattern_type, curr['close'],
                    confidence, self.calculate_strength(confidence),
                    "Double top resistance - reversal signal"
                )
        return None

# ============================================
# THREE CANDLE PATTERN DETECTORS
# ============================================

class MorningStarDetector(PatternDetector):
    def __init__(self):
        super().__init__("Morning Star", "BUY", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bearish'] and c3['is_bullish']:
            if (c1['body_size'] > c2['body_size'] * 2 and 
                c2['body_size'] < c1['body_size'] * 0.3 and
                c3['close'] > (c1['open'] + c1['close'])/2):
                confidence = 85
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "3-candle bullish reversal pattern"
                )
        return None

class EveningStarDetector(PatternDetector):
    def __init__(self):
        super().__init__("Evening Star", "SELL", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bullish'] and c3['is_bearish']:
            if (c1['body_size'] > c2['body_size'] * 2 and 
                c2['body_size'] < c1['body_size'] * 0.3 and
                c3['close'] < (c1['open'] + c1['close'])/2):
                confidence = 85
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "3-candle bearish reversal pattern"
                )
        return None

class ThreeWhiteSoldiersDetector(PatternDetector):
    def __init__(self):
        super().__init__("Three White Soldiers", "BUY", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bullish'] and c2['is_bullish'] and c3['is_bullish']:
            if (c2['close'] > c1['close'] and c3['close'] > c2['close'] and
                c1['body_size'] > c1['total_range'] * 0.6 and
                c2['body_size'] > c2['total_range'] * 0.6 and
                c3['body_size'] > c3['total_range'] * 0.6):
                confidence = 90
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Three consecutive strong bullish candles"
                )
        return None

class ThreeBlackCrowsDetector(PatternDetector):
    def __init__(self):
        super().__init__("Three Black Crows", "SELL", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bearish'] and c2['is_bearish'] and c3['is_bearish']:
            if (c2['close'] < c1['close'] and c3['close'] < c2['close'] and
                c1['body_size'] > c1['total_range'] * 0.6 and
                c2['body_size'] > c2['total_range'] * 0.6 and
                c3['body_size'] > c3['total_range'] * 0.6):
                confidence = 90
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Three consecutive strong bearish candles"
                )
        return None

class ThreeInsideUpDetector(PatternDetector):
    def __init__(self):
        super().__init__("Three Inside Up", "BUY", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        is_inside = (c2['high'] < c1['high']) and (c2['low'] > c1['low'])
        if is_inside and c1['is_bearish'] and c2['is_bullish'] and c3['is_bullish']:
            if c3['close'] > c1['high']:
                confidence = 82
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Harami followed by bullish breakout"
                )
        return None

class ThreeInsideDownDetector(PatternDetector):
    def __init__(self):
        super().__init__("Three Inside Down", "SELL", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        is_inside = (c2['high'] < c1['high']) and (c2['low'] > c1['low'])
        if is_inside and c1['is_bullish'] and c2['is_bearish'] and c3['is_bearish']:
            if c3['close'] < c1['low']:
                confidence = 82
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Harami followed by bearish breakdown"
                )
        return None

class ThreeOutsideUpDetector(PatternDetector):
    def __init__(self):
        super().__init__("Three Outside Up", "BUY", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        # Engulfing pattern followed by confirmation
        if c1['is_bearish'] and c2['is_bullish'] and c3['is_bullish']:
            if (c2['close'] > c1['open'] and c2['open'] < c1['close'] and 
                c3['close'] > c2['close']):
                confidence = 88
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Bullish engulfing with confirmation"
                )
        return None

class ThreeOutsideDownDetector(PatternDetector):
    def __init__(self):
        super().__init__("Three Outside Down", "SELL", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        # Engulfing pattern followed by confirmation
        if c1['is_bullish'] and c2['is_bearish'] and c3['is_bearish']:
            if (c2['close'] < c1['open'] and c2['open'] > c1['close'] and 
                c3['close'] < c2['close']):
                confidence = 88
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Bearish engulfing with confirmation"
                )
        return None

class AbandonedBabyBullishDetector(PatternDetector):
    def __init__(self):
        super().__init__("Abandoned Baby (Bullish)", "BUY", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bearish'] and c2['is_doji'] and c3['is_bullish']:
            gap_down = c2['high'] < c1['low']
            gap_up = c2['high'] < c3['low']
            if gap_down and gap_up:
                confidence = 92
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Rare reversal - isolated doji with gaps"
                )
        return None

class AbandonedBabyBearishDetector(PatternDetector):
    def __init__(self):
        super().__init__("Abandoned Baby (Bearish)", "SELL", 3)
    
    def detect(self, candles):
        c1, c2, c3 = candles.iloc[-3], candles.iloc[-2], candles.iloc[-1]
        if c1['is_bullish'] and c2['is_doji'] and c3['is_bearish']:
            gap_up = c2['low'] > c1['high']
            gap_down = c2['low'] > c3['high']
            if gap_up and gap_down:
                confidence = 92
                return PatternResult(
                    c3['time'], self.name, self.pattern_type, c3['close'],
                    confidence, self.calculate_strength(confidence),
                    "Rare reversal - isolated doji with gaps"
                )
        return None

# ============================================
# GUI WITH ENHANCEMENTS
# ============================================

class ScannerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Enhanced Price Action Scanner")
        self.root.geometry("1100x700")
        
        self.scanner = PAPatternScanner()
        self.is_scanning = False
        self.scan_queue = queue.Queue()
        self.pattern_stats = {}
        
        self._setup_ui()
        
    def _setup_ui(self):
        # Top Control Panel
        control_frame = ttk.Frame(self.root, padding="10")
        control_frame.pack(fill=tk.X)
        
        ttk.Label(control_frame, text="Symbol:").pack(side=tk.LEFT, padx=5)
        self.symbol_var = tk.StringVar(value="XAUUSD.m")
        self.symbol_entry = ttk.Entry(control_frame, textvariable=self.symbol_var, width=15)
        self.symbol_entry.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="TF:").pack(side=tk.LEFT, padx=5)
        self.tf_var = tk.StringVar(value="H1")
        self.tf_combo = ttk.Combobox(control_frame, textvariable=self.tf_var, width=5, state="readonly")
        self.tf_combo['values'] = ("M1", "M5", "M15", "M30", "H1", "H4", "D1")
        self.tf_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(control_frame, text="Refresh (s):").pack(side=tk.LEFT, padx=5)
        self.refresh_var = tk.StringVar(value="60")
        self.refresh_entry = ttk.Entry(control_frame, textvariable=self.refresh_var, width=5)
        self.refresh_entry.pack(side=tk.LEFT, padx=5)
        
        # Filter
        ttk.Label(control_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.filter_var = tk.StringVar(value="All")
        self.filter_combo = ttk.Combobox(control_frame, textvariable=self.filter_var, width=10, state="readonly")
        self.filter_combo['values'] = ("All", "BUY", "SELL", "NEUTRAL", "StrongOnly")
        self.filter_combo.pack(side=tk.LEFT, padx=5)
        self.filter_combo.bind('<<ComboboxSelected>>', lambda e: self._apply_filter())
        
        self.btn_start = ttk.Button(control_frame, text="Start", command=self.start_scanning)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_stop = ttk.Button(control_frame, text="Stop", command=self.stop_scanning, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.LEFT, padx=5)
        
        self.btn_export = ttk.Button(control_frame, text="Export CSV", command=self.export_to_csv)
        self.btn_export.pack(side=tk.LEFT, padx=5)
        
        self.btn_clear = ttk.Button(control_frame, text="Clear", command=self.clear_results)
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        self.status_var = tk.StringVar(value="Status: Idle")
        self.lbl_status = ttk.Label(control_frame, textvariable=self.status_var)
        self.lbl_status.pack(side=tk.RIGHT, padx=10)

        # Results Table
        table_frame = ttk.Frame(self.root, padding="10")
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("time", "symbol", "pattern", "type", "price", "confidence", "strength", "description")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("time", text="Time")
        self.tree.heading("symbol", text="Symbol")
        self.tree.heading("pattern", text="Pattern")
        self.tree.heading("type", text="Type")
        self.tree.heading("price", text="Price")
        self.tree.heading("confidence", text="Conf %")
        self.tree.heading("strength", text="Strength")
        self.tree.heading("description", text="Description")
        
        self.tree.column("time", width=140)
        self.tree.column("symbol", width=80)
        self.tree.column("pattern", width=180)
        self.tree.column("type", width=70)
        self.tree.column("price", width=80)
        self.tree.column("confidence", width=70)
        self.tree.column("strength", width=80)
        self.tree.column("description", width=250)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Tags for coloring
        self.tree.tag_configure("BUY", background="#d4edda")
        self.tree.tag_configure("SELL", background="#f8d7da")
        self.tree.tag_configure("NEUTRAL", background="#fff3cd")
        self.tree.tag_configure("strong", foreground="#006400")
        self.tree.tag_configure("moderate", foreground="#ff8c00")
        self.tree.tag_configure("weak", foreground="#8b0000")
        
        # Stats panel
        stats_frame = ttk.LabelFrame(self.root, text="Statistics", padding="5")
        stats_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="Total Patterns: 0 | BUY: 0 | SELL: 0 | Strong: 0")
        self.stats_label.pack()

    def start_scanning(self):
        symbol = self.symbol_var.get()
        tf_str = self.tf_var.get()
        
        tf_map = {
            "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
            "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
            "D1": mt5.TIMEFRAME_D1
        }
        
        self.scanner.symbol = symbol
        self.scanner.timeframe = tf_map.get(tf_str, mt5.TIMEFRAME_H1)
        
        if not self.scanner.connect():
            messagebox.showerror("Error", "Could not connect to MT5")
            return
            
        self.is_scanning = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.symbol_entry.config(state=tk.DISABLED)
        self.tf_combo.config(state=tk.DISABLED)
        self.refresh_entry.config(state=tk.DISABLED)
        self.status_var.set(f"Status: Scanning {symbol} ({tf_str})...")
        
        threading.Thread(target=self._scan_loop, daemon=True).start()
        self.root.after(100, self._process_queue)

    def stop_scanning(self):
        self.is_scanning = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.symbol_entry.config(state=tk.NORMAL)
        self.tf_combo.config(state=tk.NORMAL)
        self.refresh_entry.config(state=tk.NORMAL)
        self.status_var.set("Status: Stopped")
        self.scanner.disconnect()

    def _scan_loop(self):
        while self.is_scanning:
            try:
                patterns = self.scanner.scan_once()
                if patterns:
                    self.scan_queue.put(patterns)
            except Exception as e:
                print(f"Scan error: {e}")
            
            try:
                interval = int(self.refresh_var.get())
                if interval < 1: interval = 1
            except ValueError:
                interval = 60
            
            for _ in range(interval):
                if not self.is_scanning: break
                time.sleep(1)

    def _process_queue(self):
        try:
            while True:
                patterns = self.scan_queue.get_nowait()
                for result in patterns:
                    exists = False
                    for item in self.tree.get_children():
                        vals = self.tree.item(item)['values']
                        if str(result.timestamp) == str(vals[0]) and vals[2] == result.pattern_name:
                            exists = True
                            break
                    
                    if not exists:
                        self.tree.insert("", 0, values=(
                            result.timestamp, self.scanner.symbol, result.pattern_name,
                            result.pattern_type, result.price, result.confidence,
                            result.strength, result.description
                        ), tags=(result.pattern_type, result.strength))
                        
                        # Update stats
                        self.pattern_stats[result.pattern_type] = self.pattern_stats.get(result.pattern_type, 0) + 1
                
                self._update_stats()
                self._apply_filter()
        except queue.Empty:
            pass
        
        if self.is_scanning:
            self.root.after(1000, self._process_queue)
    
    def _update_stats(self):
        total = len(self.tree.get_children())
        buy = self.pattern_stats.get('BUY', 0)
        sell = self.pattern_stats.get('SELL', 0)
        strong = sum(1 for item in self.tree.get_children() if 'strong' in self.tree.item(item)['tags'])
        self.stats_label.config(text=f"Total: {total} | BUY: {buy} | SELL: {sell} | Strong: {strong}")
    
    def _apply_filter(self):
        filter_val = self.filter_var.get()
        for item in self.tree.get_children():
            vals = self.tree.item(item)['values']
            show = True
            
            if filter_val == "BUY" and vals[3] != "BUY":
                show = False
            elif filter_val == "SELL" and vals[3] != "SELL":
                show = False
            elif filter_val == "NEUTRAL" and vals[3] != "NEUTRAL":
                show = False
            elif filter_val == "Strong Only" and vals[6] != "strong":
                show = False
            
            if show:
                self.tree.reattach(item, '', self.tree.index(item))
            else:
                self.tree.detach(item)
    
    def export_to_csv(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                f.write("Time,Symbol,Pattern,Type,Price,Confidence,Strength,Description\n")
                for item in self.tree.get_children():
                    vals = self.tree.item(item)['values']
                    f.write(",".join(str(v) for v in vals) + "\n")
            messagebox.showinfo("Success", f"Exported to {filename}")
    
    def clear_results(self):
        self.tree.delete(*self.tree.get_children())
        self.pattern_stats = {}
        self._update_stats()

if __name__ == "__main__":
    root = tk.Tk()
    app = ScannerGUI(root)
    root.mainloop()
