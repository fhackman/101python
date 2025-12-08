import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import os
import sys

# Configuration (copied from supertrade.py)
CONFIG = {
    "SYMBOL": "XAUUSD.m",
    "SEQ_LENGTH": 100,
    "MODEL_PATH": "superpoint_transformer.pth",
    "MODEL_PARAMS": {
        "d_model": 64,
        "nhead": 4,
        "num_layers": 2
    },
    "FEATURES": ['open', 'high', 'low', 'close', 'tick_volume', 
                 'returns', 'volatility', 'rsi', 'volume_ma', 'volume_change']
}

# Neural Network Architecture (copied from supertrade.py)
class CausalConv1d(nn.Module):
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
        x_perm = x.permute(0, 2, 1)
        scores = self.score_net(x_perm).squeeze(1)
        weighted_x = x * (1 + scores.unsqueeze(2))
        embeddings = self.embedding(weighted_x)
        out = self.transformer(embeddings, mask=self.mask)
        return self.fc(out[:, -1, :]), scores

def load_model():
    print(f"Current working directory: {os.getcwd()}")
    print(f"Model path: {os.path.abspath(CONFIG['MODEL_PATH'])}")
    
    if not os.path.exists(CONFIG['MODEL_PATH']):
        print("Error: Model file does not exist!")
        return

    try:
        input_dim = len(CONFIG['FEATURES'])
        print(f"Initializing model with input_dim={input_dim}")
        model = SuperpointTransformer(
            input_dim=input_dim,
            d_model=CONFIG['MODEL_PARAMS']['d_model'],
            nhead=CONFIG['MODEL_PARAMS']['nhead'],
            num_layers=CONFIG['MODEL_PARAMS']['num_layers'],
            seq_len=CONFIG['SEQ_LENGTH'],
            num_classes=3
        )
        
        print("Loading state dict...")
        # Try loading with map_location to handle potential device mismatches
        state_dict = torch.load(CONFIG['MODEL_PATH'], map_location=torch.device('cpu'))
        
        # Check for shape mismatches
        model_state = model.state_dict()
        for name, param in state_dict.items():
            if name in model_state:
                if param.shape != model_state[name].shape:
                    print(f"Shape mismatch for {name}: loaded {param.shape}, expected {model_state[name].shape}")
            else:
                print(f"Unexpected key in state_dict: {name}")
                
        model.load_state_dict(state_dict)
        model.eval()
        print("Model loaded successfully!")
        return True
    except Exception as e:
        print(f"Error loading model: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    load_model()
