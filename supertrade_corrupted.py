import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
import time
from datetime import datetime
import json
import os
import logging

# Configuration
CONFIG = {
    "SYMBOL": "XAUUSD.m",
    "TIMEFRAME": mt5.TIMEFRAME_H4,
    "VOLUME": 0.01,
    "POLL_INTERVAL": 300,  # 5 minutes
    "SEQ_LENGTH": 100,     # Input sequence length
    "MODEL_PATH": "superpoint_transformer.pth",
    "RISK_PARAMS": {
        "max_drawdown": 0.05,  # 5% max drawdown
        "stop_loss": 0.01,     # 1% stop loss (percentage based for auto)
        "take_profit": 0.02    # 2% take profit (percentage based for auto)
    },
    "MANUAL_PARAMS": {
        "volume": 0.01,
        "tp_points": 1000,
        "sl_points": 200
    },
    "MODEL_PARAMS": {
        "d_model": 64,
        "nhead": 4,
        "num_layers": 2
    },
    "FEATURES": ['open', 'high', 'low', 'close', 'tick_volume', 
                 'returns', 'volatility', 'rsi', 'volume_ma', 'volume_change']
}

# Save config to file
def save_config():
    with open('bot_config.json', 'w') as f:
        json.dump(CONFIG, f, indent=4)

# Load config if exists
if os.path.exists('bot_config.json'):
    with open('bot_config.json', 'r') as f:
        loaded_config = json.load(f)
        CONFIG.update(loaded_config)

# ----------------------------
# Neural Network Architecture
# ----------------------------
class CausalConv1d(nn.Module):
    """Ensures no future data leakage in keypoint detection"""
    def __init__(self, in_channels, out_channels, kernel_size, dilation=1):
        super().__init__()
        self.padding = (kernel_size - 1) * dilation
        self.conv = nn.Conv1d(in_channels, out_channels, kernel_size, 
                             dilation=dilation, padding=0)
    
    def forward(self, x):
        x = F.pad(x, (self.padding, 0))  # Pad left only
        return self.conv(x)

class SuperpointTransformer(nn.Module):
    def __init__(self, input_dim=5, d_model=64, nhead=4, 
                 num_layers=3, num_classes=3, seq_len=CONFIG['SEQ_LENGTH']):
        super().__init__()
        # Keypoint detector (causal convolutions)
        self.score_net = nn.Sequential(
            nn.Conv1d(input_dim, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            CausalConv1d(64, 32, kernel_size=3),
            nn.ReLU(),
            nn.Conv1d(32, 1, kernel_size=1),
            nn.Sigmoid()
        )
        
        # Embedding & Transformer
        self.embedding = nn.Linear(input_dim, d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model, nhead, dropout=0.1, batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers)
        
        # Prediction
        self.fc = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(32, num_classes)
        )
        
        # Causal mask for Transformer
        mask = torch.triu(torch.ones(seq_len, seq_len)) == 1
        self.register_buffer("mask", mask.float().masked_fill(mask, float('-inf')))
    
    def forward(self, x):
        # Input shape: (batch, seq_len, features)
        x_perm = x.permute(0, 2, 1)  # (batch, features, seq_len)
        
        # Keypoint scores (batch, seq_len)
        scores = self.score_net(x_perm).squeeze(1)
        
        # Amplify keypoint features
        weighted_x = x * (1 + scores.unsqueeze(2))
        
        # Transformer processing
        embeddings = self.embedding(weighted_x)
        out = self.transformer(embeddings, mask=self.mask)
        
        # Use last timestep for prediction
        return self.fc(out[:, -1, :]), scores

# ----------------------------
# Trading Utilities
# ----------------------------
def initialize_mt5():
    if not mt5.initialize():
        print("MT5 initialization failed!")
        return False
    return True

def fetch_data(symbol, timeframe, n_bars):
    if not mt5.initialize():
        print("MT5 init failed in fetch_data")
        return None
        
    try:
        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n_bars)
        if rates is None:
            print(f"Failed to fetch data for {symbol}")
            return None
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df.set_index('time', inplace=True)
        return df
    except Exception as e:
        print(f"Data fetch error: {e}")
        return None

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_technical_indicators(df):
    # Price-based features
    df['returns'] = df['close'].pct_change()
    df['volatility'] = df['close'].rolling(20).std()
    df['rsi'] = compute_rsi(df['close'], 14)
    
    # Volume-based features
    df['volume_ma'] = df['tick_volume'].rolling(10).mean()
    df['volume_change'] = df['tick_volume'].pct_change()
    
    # Drop NA values
    df.dropna(inplace=True)
    return df

def preprocess_data(df):
    # Select features
    features = ['open', 'high', 'low', 'close', 'tick_volume', 
                'returns', 'volatility', 'rsi', 'volume_ma', 'volume_change']
    available_features = [f for f in features if f in df.columns]
    
    # Scale data
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(df[available_features])
    return scaled_data, scaler, available_features

def calculate_position_size(balance, risk_per_trade=0.01, stop_loss_pct=0.01):
    risk_amount = balance * risk_per_trade
    return risk_amount / stop_loss_pct

# ----------------------------
# Trading Execution
# ----------------------------
def execute_trade(symbol, signal, model_confidence, current_price, volume=None, sl_points=None, tp_points=None):
    if not mt5.initialize():
        return False

    try:
        # Get current account balance
        account_info = mt5.account_info()
        if account_info is None:
            print("Failed to get account info")
            return False
            
        balance = account_info.balance
        equity = account_info.equity
        
        # Risk management checks (skip for manual trades if desired, but keeping for safety)
        drawdown = 1 - (equity / balance) if balance > 0 else 0
        if drawdown > CONFIG['RISK_PARAMS']['max_drawdown']:
            print(f"Drawdown limit reached: {drawdown:.2%} > {CONFIG['RISK_PARAMS']['max_drawdown']:.2%}")
            return False
            
        # Determine Position Size
        if volume is not None:
            position_size = volume
        else:
            # Auto-calculate based on risk
            position_size = calculate_position_size(
                balance, 
                risk_per_trade=0.01, 
                stop_loss_pct=CONFIG['RISK_PARAMS']['stop_loss']
                input_dim=input_dim,
                d_model=self.config['MODEL_PARAMS']['d_model'],
                nhead=self.config['MODEL_PARAMS']['nhead'],
                num_layers=self.config['MODEL_PARAMS']['num_layers'],
                seq_len=self.config['SEQ_LENGTH'],
                num_classes=3 # BUY, SELL, HOLD
            )
            model.load_state_dict(torch.load(self.config['MODEL_PATH']))
            model.eval()
            self.model = model
            self.log("Model loaded successfully.")
            return True
        except Exception as e:
            self.log(f"Error loading model: {e}", level=logging.ERROR)
            return False

    def get_trading_signal(self, sequence):
        if self.model is None:
            self.log("Model not loaded, cannot get signal.", level=logging.WARNING)
            return 0 # HOLD

        try:
            # Convert sequence to tensor and add batch dimension
            input_tensor = torch.tensor(sequence, dtype=torch.float32).unsqueeze(0)
            
            with torch.no_grad():
                output, scores = self.model(input_tensor)
                probabilities = F.softmax(output, dim=1)
                
                # Get predicted class (0: HOLD, 1: BUY, 2: SELL)
                _, predicted_class = torch.max(probabilities, 1)
                
                # Store confidence for the predicted class
                self.model_confidence = probabilities[0, predicted_class.item()].item()
                
                return predicted_class.item()
        except Exception as e:
            self.log(f"Error getting trading signal: {e}", level=logging.ERROR)
            return 0 # Default to HOLD on error

    def manual_trade(self, signal, volume, sl_points=None, tp_points=None):
        try:
            if not initialize_mt5():
                self.log("MT5 Init failed for manual trade")
                return

            current_price = mt5.symbol_info_tick(self.config['SYMBOL']).ask # Approximation
            
            success = execute_trade(
                self.config['SYMBOL'],
                signal,
                1.0, # Full confidence for manual
                current_price,
                volume=volume,
                sl_points=sl_points,
                tp_points=tp_points
            )
            
            if success:
                self.log(f"Manual {'BUY' if signal == 1 else 'SELL'} executed. Vol: {volume}, SL: {sl_points}, TP: {tp_points}")
            else:
                self.log("Manual trade failed")
                
        except Exception as e:
            self.log(f"Manual trade error: {e}")

    def stop(self):
        self.running = False
        self.log("Stopping bot...")
            
    def run(self):
        self.running = True
        save_config()
        
        if not initialize_mt5():
            self.log("MT5 Init failed")
            return
            
        if not self.load_model():
            self.log("Model load failed")
            return
            
        self.log(f"Starting Superpoint Trading Bot for {self.config['SYMBOL']}")
        
        try:
            while self.running:
                start_time = time.time()
                
                try:
                    # 1. Fetch market data
                    df = fetch_data(
                        self.config['SYMBOL'], 
                        self.config['TIMEFRAME'], 
                        self.config['SEQ_LENGTH'] + 50  # Extra for indicators
                    )
                    if df is None:
                        time.sleep(5)
                        continue
                        
                    # Store for GUI
                    self.latest_data = df.copy() if df is not None else None
                        
                    # 2. Process data
                    df = compute_technical_indicators(df)
                    processed_data, self.scaler, self.feature_names = preprocess_data(df)
                    
                    # Ensure we have enough data
                    if len(processed_data) < self.config['SEQ_LENGTH']:
                        self.log("Insufficient data, waiting...")
                        time.sleep(10)
                        continue
                        
                    # Take most recent sequence
                    sequence = processed_data[-self.config['SEQ_LENGTH']:]
                    
                    # 3. Get trading signal
                    signal = self.get_trading_signal(sequence)
                    
                    # 4. Execute trade if signal changes
                    current_price = mt5.symbol_info_tick(self.config['SYMBOL']).ask
                    if signal != self.last_position:
                        if execute_trade(
                            self.config['SYMBOL'], 
                            signal, 
                            self.model_confidence,
                            current_price
                        ):
                            self.last_position = signal
                    
                    # 5. Log status
                    status = {
                        "timestamp": datetime.now().strftime('%H:%M:%S'),
                        "symbol": self.config['SYMBOL'],
                        "signal": "BUY" if signal == 1 else "SELL" if signal == 2 else "HOLD",
                        "confidence": f"{self.model_confidence:.2f}",
                        "price": current_price
                    }
                    self.latest_status = status
                    self.log(f"Status: {status}")
                    
                except Exception as e:
                    self.log(f"Runtime error: {e}")
                
                # 6. Wait for next interval
                elapsed = time.time() - start_time
                wait_time = max(1, self.config['POLL_INTERVAL'] - elapsed)
                
                # Sleep in 1s intervals to check self.running
                for _ in range(int(wait_time)):
                    if not self.running:
                        break
                    time.sleep(1)
                
        except KeyboardInterrupt:
            self.log("\nBot stopped by user")
        finally:
            mt5.shutdown()
            self.log("MT5 Shutdown")

# ----------------------------
# Main Execution
# ----------------------------
if __name__ == "__main__":
    bot = SuperpointTradingBot(CONFIG)
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()