#!/usr/bin/env python3
"""
Real Bitcoin Miner with GPU Acceleration
Uses CUDA for NVIDIA GPUs
For authorized testing and educational purposes only
"""

import hashlib
import struct
import time
import threading
import json
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import numpy as np

try:
    import pycuda.driver as cuda
    import pycuda.autoinit
    from pycuda.compiler import SourceModule
    HAS_CUDA = True
except ImportError:
    HAS_CUDA = False
    print("[-] CUDA not available. Install pycuda for GPU acceleration.")

class GPUBitcoinMiner:
    def __init__(self, difficulty: int = 20, device_id: int = 0):
        """
        Initialize GPU Bitcoin miner
        
        Args:
            difficulty: Number of leading zeros required
            device_id: CUDA device ID to use
        """
        self.difficulty = difficulty
        self.device_id = device_id
        self.target = 2 ** (256 - difficulty * 4)
        self.blocks_mined = 0
        self.total_hashes = 0
        self.running = False
        
        # GPU setup
        self.context = None
        self.device = None
        self.kernel = None
        self.setup_gpu()
        
        # Mining statistics
        self.stats = {
            "start_time": None,
            "hash_rate": 0,
            "blocks_found": 0,
            "gpu_utilization": 0
        }

    def setup_gpu(self) -> bool:
        """Setup CUDA device and compile mining kernel"""
        if not HAS_CUDA:
            print("[-] CUDA not available. Falling back to CPU mining.")
            return False
            
        try:
            # Initialize CUDA
            cuda.init()
            self.device = cuda.Device(self.device_id)
            self.context = self.device.make_context()
            
            print(f"[+] Using GPU: {self.device.name()}")
            print(f"[+] Compute Capability: {self.device.compute_capability()}")
            print(f"[+] Total Memory: {self.device.total_memory() / 1024**3:.1f} GB")
            
            # Compile CUDA kernel
            self.compile_mining_kernel()
            return True
            
        except Exception as e:
            print(f"[-] GPU setup failed: {e}")
            return False

    def compile_mining_kernel(self) -> None:
        """Compile the CUDA mining kernel"""
        cuda_kernel = """
        #include <stdint.h>
        
        __device__ void sha256_transform(uint32_t *state, const uint32_t *data) {
            uint32_t a, b, c, d, e, f, g, h, t1, t2, m[64];
            uint32_t k[64] = {
                0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
                0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
                0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
                0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
                0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
                0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
                0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
                0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
            };
            
            for (int i = 0; i < 16; i++)
                m[i] = data[i];
            for (int i = 16; i < 64; i++) {
                uint32_t s0 = (m[i-15] >> 7 | m[i-15] << 25) ^ (m[i-15] >> 18 | m[i-15] << 14) ^ (m[i-15] >> 3);
                uint32_t s1 = (m[i-2] >> 17 | m[i-2] << 15) ^ (m[i-2] >> 19 | m[i-2] << 13) ^ (m[i-2] >> 10);
                m[i] = m[i-16] + s0 + m[i-7] + s1;
            }
            
            a = state[0]; b = state[1]; c = state[2]; d = state[3];
            e = state[4]; f = state[5]; g = state[6]; h = state[7];
            
            for (int i = 0; i < 64; i++) {
                uint32_t s1 = (e >> 6 | e << 26) ^ (e >> 11 | e << 21) ^ (e >> 25 | e << 7);
                uint32_t ch = (e & f) ^ (~e & g);
                uint32_t temp1 = h + s1 + ch + k[i] + m[i];
                uint32_t s0 = (a >> 2 | a << 30) ^ (a >> 13 | a << 19) ^ (a >> 22 | a << 10);
                uint32_t maj = (a & b) ^ (a & c) ^ (b & c);
                uint32_t temp2 = s0 + maj;
                
                h = g; g = f; f = e; e = d + temp1;
                d = c; c = b; b = a; a = temp1 + temp2;
            }
            
            state[0] += a; state[1] += b; state[2] += c; state[3] += d;
            state[4] += e; state[5] += f; state[6] += g; state[7] += h;
        }
        
        __device__ void double_sha256(const uint32_t *header, uint32_t *output) {
            uint32_t state1[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 
                                 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
            uint32_t state2[8] = {0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 
                                 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19};
            
            // First SHA256
            uint32_t data[16];
            for (int i = 0; i < 16; i++) data[i] = header[i];
            sha256_transform(state1, data);
            
            // Second SHA256 (on first hash)
            uint32_t hash_data[16] = {0};
            for (int i = 0; i < 8; i++) {
                hash_data[i] = (state1[i] >> 24) | ((state1[i] >> 8) & 0xff00) | 
                              ((state1[i] << 8) & 0xff0000) | (state1[i] << 24);
            }
            hash_data[8] = 0x80000000;
            hash_data[15] = 0x00000100;
            
            sha256_transform(state2, hash_data);
            
            for (int i = 0; i < 8; i++) {
                output[i] = (state2[i] >> 24) | ((state2[i] >> 8) & 0xff00) | 
                           ((state2[i] << 8) & 0xff0000) | (state2[i] << 24);
            }
        }
        
        __global__ void mine_bitcoin(uint32_t *header_template, uint64_t start_nonce, 
                                   uint64_t *results, uint64_t target_high, uint64_t target_low) {
            int idx = blockIdx.x * blockDim.x + threadIdx.x;
            uint64_t nonce = start_nonce + idx;
            
            // Copy header and set nonce
            uint32_t header[20];
            for (int i = 0; i < 19; i++) header[i] = header_template[i];
            header[19] = (uint32_t)(nonce & 0xFFFFFFFF);
            
            // Calculate hash
            uint32_t hash[8];
            double_sha256(header, hash);
            
            // Check if hash meets target (simplified check)
            uint64_t hash_value = ((uint64_t)hash[0] << 32) | hash[1];
            if (hash_value < target_high || (hash_value == target_high && ((uint64_t)hash[2] << 32 | hash[3]) < target_low)) {
                results[0] = nonce;
                results[1] = hash[0];
                results[2] = hash[1];
                results[3] = hash[2];
                results[4] = hash[3];
            }
        }
        """
        
        try:
            self.kernel = SourceModule(cuda_kernel)
            self.mine_func = self.kernel.get_function("mine_bitcoin")
            print("[+] CUDA kernel compiled successfully")
        except Exception as e:
            print(f"[-] Kernel compilation failed: {e}")

    def create_block_header(self, version: int, prev_block_hash: str, merkle_root: str, 
                          timestamp: int, bits: int) -> np.ndarray:
        """Create block header template for GPU mining"""
        # Convert to little-endian bytes
        prev_block = bytes.fromhex(prev_block_hash)[::-1]
        merkle_root_bytes = bytes.fromhex(merkle_root)[::-1]
        
        # Pack header (without nonce)
        header = struct.pack("<L", version)
        header += prev_block
        header += merkle_root_bytes
        header += struct.pack("<LL", timestamp, bits)
        
        # Convert to uint32 array for GPU
        header_uint32 = np.frombuffer(header, dtype=np.uint32)
        return header_uint32

    def mine_block_gpu(self, version: int, prev_block_hash: str, merkle_root: str, 
                      timestamp: int, bits: int, batch_size: int = 1000000) -> Optional[Tuple[int, str]]:
        """Mine block using GPU acceleration"""
        if not HAS_CUDA or self.kernel is None:
            print("[-] GPU not available, falling back to CPU")
            return self.mine_block_cpu(version, prev_block_hash, merkle_root, timestamp, bits)
        
        print(f"[*] Starting GPU mining with difficulty {self.difficulty}")
        print(f"[*] Batch size: {batch_size:,}")
        
        # Create header template
        header_template = self.create_block_header(version, prev_block_hash, merkle_root, timestamp, bits)
        
        # Allocate GPU memory
        header_gpu = cuda.mem_alloc(header_template.nbytes)
        results_gpu = cuda.mem_alloc(5 * 8)  # 5 uint64 values
        
        # Copy header to GPU
        cuda.memcpy_htod(header_gpu, header_template)
        
        start_time = time.time()
        start_nonce = 0
        hashes_computed = 0
        
        while self.running:
            # Initialize results
            results_host = np.zeros(5, dtype=np.uint64)
            cuda.memcpy_htod(results_gpu, results_host)
            
            # Calculate grid and block dimensions
            threads_per_block = 256
            blocks_per_grid = (batch_size + threads_per_block - 1) // threads_per_block
            
            # Split target for comparison
            target_high = (self.target >> 192) & 0xFFFFFFFFFFFFFFFF
            target_low = (self.target >> 128) & 0xFFFFFFFFFFFFFFFF
            
            # Launch kernel
            self.mine_func(header_gpu, np.uint64(start_nonce), results_gpu,
                         np.uint64(target_high), np.uint64(target_low),
                         block=(threads_per_block, 1, 1), grid=(blocks_per_grid, 1))
            
            # Copy results back
            cuda.memcpy_dtoh(results_host, results_gpu)
            
            hashes_computed += batch_size
            self.total_hashes += batch_size
            
            # Check if nonce was found
            if results_host[0] != 0:
                nonce = results_host[0]
                block_hash = f"{results_host[1]:016x}{results_host[2]:016x}{results_host[3]:016x}{results_host[4]:016x}"
                
                elapsed = time.time() - start_time
                hash_rate = hashes_computed / elapsed
                
                print(f"[+] Block mined! Nonce: {nonce}")
                print(f"[+] Hash: {block_hash}")
                print(f"[+] GPU Hash rate: {hash_rate:,.0f} H/s")
                print(f"[+] Time elapsed: {elapsed:.2f} seconds")
                
                self.blocks_mined += 1
                self.stats["blocks_found"] += 1
                
                # Cleanup GPU memory
                header_gpu.free()
                results_gpu.free()
                
                return nonce, block_hash
            
            start_nonce += batch_size
            
            # Progress reporting
            if start_nonce % (batch_size * 10) == 0:
                elapsed = time.time() - start_time
                hash_rate = hashes_computed / elapsed
                print(f"[*] Progress: {start_nonce:,} nonces, Rate: {hash_rate:,.0f} H/s")
        
        # Cleanup
        header_gpu.free()
        results_gpu.free()
        return None

    def mine_block_cpu(self, version: int, prev_block_hash: str, merkle_root: str, 
                      timestamp: int, bits: int) -> Optional[Tuple[int, str]]:
        """Fallback CPU mining implementation"""
        print("[*] Using CPU mining (fallback)")
        
        def double_sha256(data):
            return hashlib.sha256(hashlib.sha256(data).digest()).digest()
        
        start_time = time.time()
        hashes_computed = 0
        
        for nonce in range(2**32):
            if not self.running:
                return None
                
            # Create block header
            prev_block = bytes.fromhex(prev_block_hash)[::-1]
            merkle_root_bytes = bytes.fromhex(merkle_root)[::-1]
            
            header = struct.pack("<L", version)
            header += prev_block
            header += merkle_root_bytes
            header += struct.pack("<LLL", timestamp, bits, nonce)
            
            # Calculate hash
            block_hash = double_sha256(header)
            hashes_computed += 1
            self.total_hashes += 1
            
            # Check if hash meets target
            hash_int = int.from_bytes(block_hash, byteorder='big')
            if hash_int < self.target:
                elapsed = time.time() - start_time
                hash_rate = hashes_computed / elapsed
                
                print(f"[+] Block mined! Nonce: {nonce}")
                print(f"[+] Hash: {block_hash.hex()}")
                print(f"[+] CPU Hash rate: {hash_rate:.0f} H/s")
                print(f"[+] Time elapsed: {elapsed:.2f} seconds")
                
                self.blocks_mined += 1
                self.stats["blocks_found"] += 1
                
                return nonce, block_hash.hex()
            
            if nonce % 100000 == 0:
                elapsed = time.time() - start_time
                hash_rate = hashes_computed / elapsed
                print(f"[*] CPU Progress: {nonce:,} hashes, Rate: {hash_rate:.0f} H/s")
        
        return None

    def start_mining(self, block_data: Dict, use_gpu: bool = True) -> None:
        """Start mining process"""
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        print("[*] Starting Bitcoin mining process...")
        print(f"[*] Target difficulty: {self.difficulty}")
        print(f"[*] GPU acceleration: {'Enabled' if use_gpu and HAS_CUDA else 'Disabled'}")
        
        if use_gpu and HAS_CUDA:
            result = self.mine_block_gpu(
                version=block_data.get("version", 1),
                prev_block_hash=block_data.get("prev_block_hash", "0" * 64),
                merkle_root=block_data.get("merkle_root", "0" * 64),
                timestamp=block_data.get("timestamp", int(time.time())),
                bits=block_data.get("bits", 0x1d00ffff)
            )
        else:
            result = self.mine_block_cpu(
                version=block_data.get("version", 1),
                prev_block_hash=block_data.get("prev_block_hash", "0" * 64),
                merkle_root=block_data.get("merkle_root", "0" * 64),
                timestamp=block_data.get("timestamp", int(time.time())),
                bits=block_data.get("bits", 0x1d00ffff)
            )
        
        if result:
            nonce, block_hash = result
            print(f"\n[SUCCESS] Block mined successfully!")
            print(f"Nonce: {nonce}")
            print(f"Block Hash: {block_hash}")
            print(f"Total blocks mined: {self.blocks_mined}")
            print(f"Total hashes computed: {self.total_hashes:,}")
        else:
            print("\n[FAILED] Mining unsuccessful")
        
        self.running = False

    def get_mining_stats(self) -> Dict:
        """Get current mining statistics"""
        if self.stats["start_time"]:
            elapsed = (datetime.now() - self.stats["start_time"]).total_seconds()
            self.stats["hash_rate"] = self.total_hashes / elapsed if elapsed > 0 else 0
        
        return {
            "difficulty": self.difficulty,
            "blocks_mined": self.blocks_mined,
            "total_hashes": self.total_hashes,
            "hash_rate": self.stats["hash_rate"],
            "gpu_accelerated": HAS_CUDA,
            "running": self.running
        }

    def stop_mining(self) -> None:
        """Stop mining process"""
        self.running = False
        if self.context:
            self.context.pop()
        print("[*] Mining stopped")

class MultiGPUMiner:
    """Multi-GPU Bitcoin miner for maximum performance"""
    
    def __init__(self, difficulty: int = 20):
        self.difficulty = difficulty
        self.miners = []
        self.setup_multiple_gpus()
    
    def setup_multiple_gpus(self) -> None:
        """Setup mining on all available GPUs"""
        if not HAS_CUDA:
            print("[-] CUDA not available")
            return
            
        try:
            cuda.init()
            device_count = cuda.Device.count()
            print(f"[+] Found {device_count} CUDA devices")
            
            for i in range(device_count):
                miner = GPUBitcoinMiner(difficulty=self.difficulty, device_id=i)
                self.miners.append(miner)
                print(f"[+] Initialized miner on GPU {i}: {miner.device.name()}")
                
        except Exception as e:
            print(f"[-] Multi-GPU setup failed: {e}")
    
    def start_multi_gpu_mining(self, block_data: Dict) -> None:
        """Start mining on all GPUs"""
        print(f"[*] Starting multi-GPU mining with {len(self.miners)} devices")
        
        threads = []
        for i, miner in enumerate(self.miners):
            thread = threading.Thread(
                target=miner.start_mining,
                args=(block_data, True),
                name=f"GPU-Miner-{i}"
            )
            threads.append(thread)
            thread.start()
        
        # Monitor progress
        self.monitor_multi_gpu()
        
        # Wait for completion
        for thread in threads:
            thread.join()
    
    def monitor_multi_gpu(self) -> None:
        """Monitor multi-GPU mining progress"""
        while any(miner.running for miner in self.miners):
            total_hashes = sum(miner.total_hashes for miner in self.miners)
            total_blocks = sum(miner.blocks_mined for miner in self.miners)
            
            # Calculate combined hash rate
            hash_rates = []
            for miner in self.miners:
                if miner.stats["start_time"]:
                    elapsed = (datetime.now() - miner.stats["start_time"]).total_seconds()
                    if elapsed > 0:
                        hash_rates.append(miner.total_hashes / elapsed)
            
            combined_rate = sum(hash_rates)
            
            print(f"\r[*] Multi-GPU - Hashes: {total_hashes:,} | Blocks: {total_blocks} | Rate: {combined_rate:,.0f} H/s", end="")
            time.sleep(2)
        
        print("\n[*] Multi-GPU mining completed")

def create_real_block() -> Dict:
    """Create realistic block data for mining"""
    # Use actual Bitcoin testnet or mainnet data
    return {
        "version": 0x20000000,
        "prev_block_hash": "0000000000000000000a9a43d5d5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e",  # Example
        "merkle_root": "5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e",
        "timestamp": int(time.time()),
        "bits": 0x1d00ffff,  # Standard Bitcoin difficulty
    }

# Installation script
def install_requirements():
    """Install required packages for GPU mining"""
    import subprocess
    import sys
    
    packages = [
        "pycuda",
        "numpy"
    ]
    
    for package in packages:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
            print(f"[+] Successfully installed {package}")
        except subprocess.CalledProcessError:
            print(f"[-] Failed to install {package}")

# Command Line Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Real Bitcoin Miner with GPU Acceleration")
    parser.add_argument("--difficulty", "-d", type=int, default=20, help="Mining difficulty (higher = more difficult)")
    parser.add_argument("--gpu", "-g", type=int, default=0,
                       help="GPU device ID to use")
    parser.add_argument("--multi-gpu", "-m", action="store_true",
                       help="Use all available GPUs")
    parser.add_argument("--cpu", action="store_true",
                       help="Force CPU mining (disable GPU)")
    parser.add_argument("--batch-size", "-b", type=int, default=1000000,
                       help="GPU batch size (larger = more memory usage)")
    parser.add_argument("--install", action="store_true",
                       help="Install required packages")
    
    args = parser.parse_args()
    
    if args.install:
        install_requirements()
        sys.exit(0)
    
    # Check CUDA availability
    if not HAS_CUDA:
        print("[-] CUDA not available. Install pycuda for GPU acceleration.")
        print("[-] Running in CPU mode...")
        args.cpu = True
    
    if args.multi_gpu and HAS_CUDA:
        # Multi-GPU mining
        multi_miner = MultiGPUMiner(difficulty=args.difficulty)
        block_data = create_real_block()
        multi_miner.start_multi_gpu_mining(block_data)
    else:
        # Single GPU/CPU mining
        miner = GPUBitcoinMiner(difficulty=args.difficulty, device_id=args.gpu)
        block_data = create_real_block()
        miner.start_mining(block_data, use_gpu=not args.cpu)