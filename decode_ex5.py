import struct
import binascii
import datetime
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext
from dataclasses import dataclass
from typing import List, Dict, Any
import os

@dataclass
class EX5Header:
    copyright: str = ""
    description: str = ""
    version: str = ""
    input_params: Dict[str, Any] = None

class EX5Decoder:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.header = EX5Header()
        self.raw_data = None
        self.header_info = {}
        
    def read_file(self):
        try:
            with open(self.file_path, 'rb') as file:
                self.raw_data = file.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {self.file_path} was not found.")
        except Exception as e:
            raise Exception(f"Error reading file: {str(e)}")
    
    def decode_header(self):
        if not self.raw_data:
            self.read_file()
        
        # Check EX5 signature
        ex5_signature = b'\x00\x00\x00\x00\x38\x98\x00\x00'
        if not self.raw_data.startswith(ex5_signature):
            raise ValueError("Invalid EX5 file format")
        
        self.header_info['file_size'] = len(self.raw_data)
        
        try:
            copyright_start = self.raw_data.index(b'Copyright')
            copyright_end = self.raw_data.index(b'\x00', copyright_start)
            self.header.copyright = self.raw_data[copyright_start:copyright_end].decode('ascii')
        except ValueError:
            self.header.copyright = "Copyright information not found"
        
        timestamp_offset = 0x1C
        if len(self.raw_data) > timestamp_offset + 4:
            timestamp = struct.unpack('<I', self.raw_data[timestamp_offset:timestamp_offset+4])[0]
            self.header_info['creation_date'] = datetime.datetime.fromtimestamp(timestamp)
    
    def find_input_parameters(self):
        param_markers = [b'input', b'extern', b'parameter']
        potential_params = {}
        
        for marker in param_markers:
            start = 0
            while True:
                try:
                    start = self.raw_data.index(marker, start)
                    end = self.raw_data.index(b'\x00', start)
                    param_data = self.raw_data[start:end].decode('ascii', errors='ignore')
                    
                    parts = param_data.split()
                    if len(parts) >= 2:
                        param_type = parts[0]
                        param_name = parts[1]
                        potential_params[param_name] = {'type': param_type}
                    
                    start = end + 1
                except ValueError:
                    break
        
        self.header.input_params = potential_params
    
    def analyze(self):
        self.decode_header()
        self.find_input_parameters()
        return {
            'header_info': self.header_info,
            'copyright': self.header.copyright,
            'input_parameters': self.header.input_params
        }

def extract_strings(data: bytes, min_length: int = 4) -> List[str]:
    strings = []
    current_string = ""
    for byte in data:
        if 32 <= byte <= 126:
            current_string += chr(byte)
        else:
            if len(current_string) >= min_length:
                strings.append(current_string)
            current_string = ""
    return strings

class EX5AnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("EX5 File Analyzer")
        self.root.geometry("600x400")
        
        # File selection frame
        file_frame = ttk.Frame(root, padding="10")
        file_frame.pack(fill=tk.X)
        
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(file_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)
        ttk.Button(file_frame, text="Analyze", command=self.analyze_file).pack(side=tk.LEFT, padx=(10, 0))
        
        # Results display
        results_frame = ttk.Frame(root, padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, width=70, height=20)
        self.results_text.pack(fill=tk.BOTH, expand=True)
    
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("EX5 files", "*.ex5"), ("All files", "*.*")]
        )
        if file_path:
            self.file_path.set(file_path)
    
    def analyze_file(self):
        file_path = self.file_path.get()
        if not file_path:
            self.show_results("Please select an EX5 file first.")
            return
        
        try:
            decoder = EX5Decoder(file_path)
            analysis = decoder.analyze()
            
            strings = extract_strings(decoder.raw_data)
            
            file_type = "Unknown"
            type_indicators = {
                'OnTick': 'Expert Advisor',
                'OnCalculate': 'Indicator',
                'OnStart': 'Script'
            }
            
            for indicator, f_type in type_indicators.items():
                if any(indicator in s for s in strings):
                    file_type = f_type
                    break
            
            results = f"=== Analysis Results ===\n\n"
            results += f"File: {os.path.basename(file_path)}\n"
            results += f"Type: {file_type}\n"
            results += f"Copyright: {analysis['copyright']}\n"
            
            if 'creation_date' in analysis['header_info']:
                results += f"Creation Date: {analysis['header_info']['creation_date']}\n"
            
            if analysis['input_parameters']:
                results += "\nDetected Input Parameters:\n"
                for name, info in analysis['input_parameters'].items():
                    results += f"  {info['type']} {name}\n"
            
            results += "\nPotentially Useful Strings Found:\n"
            for string in [s for s in strings if len(s) > 10][:10]:
                results += f"  {string}\n"
            
            self.show_results(results)
            
        except Exception as e:
            self.show_results(f"Error analyzing file: {str(e)}")
    
    def show_results(self, text):
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, text)

def main():
    root = tk.Tk()
    app = EX5AnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()