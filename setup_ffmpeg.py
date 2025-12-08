"""
Download and setup FFmpeg for MP3Gain application
This script downloads the ffmpeg essentials build and extracts it to the local folder
"""

import os
import sys
import urllib.request
import zipfile
from pathlib import Path
import shutil

# FFmpeg download URL (Windows essentials build)
FFMPEG_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
SCRIPT_DIR = Path(__file__).parent
FFMPEG_DIR = SCRIPT_DIR / "ffmpeg"
TEMP_ZIP = SCRIPT_DIR / "ffmpeg_temp.zip"

def download_ffmpeg():
    """Download ffmpeg zip file"""
    print("=" * 60)
    print("FFmpeg Download Tool for MP3Gain Normalizer")
    print("=" * 60)
    print(f"\nDownloading FFmpeg from: {FFMPEG_URL}")
    print("This may take a few minutes (size: ~80 MB)...\n")
    
    try:
        # Download with progress
        def progress_callback(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, (downloaded / total_size) * 100) if total_size > 0 else 0
            bar_length = 40
            filled = int(bar_length * percent / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            print(f'\rProgress: [{bar}] {percent:.1f}%', end='', flush=True)
        
        urllib.request.urlretrieve(FFMPEG_URL, TEMP_ZIP, progress_callback)
        print("\n✓ Download complete!")
        return True
        
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        return False

def extract_ffmpeg():
    """Extract ffmpeg from zip and organize files"""
    print("\nExtracting FFmpeg...")
    
    try:
        # Create ffmpeg directory if it doesn't exist
        FFMPEG_DIR.mkdir(exist_ok=True)
        
        # Extract zip
        with zipfile.ZipFile(TEMP_ZIP, 'r') as zip_ref:
            # Find the root folder in the zip
            members = zip_ref.namelist()
            root_folder = members[0].split('/')[0] if '/' in members[0] else None
            
            if root_folder:
                # Extract only bin folder contents
                bin_members = [m for m in members if '/bin/' in m and not m.endswith('/')]
                
                for member in bin_members:
                    # Get filename only
                    filename = os.path.basename(member)
                    
                    # Extract to ffmpeg/bin/
                    source = zip_ref.open(member)
                    target_dir = FFMPEG_DIR / "bin"
                    target_dir.mkdir(exist_ok=True)
                    target_file = target_dir / filename
                    
                    with open(target_file, 'wb') as target:
                        shutil.copyfileobj(source, target)
                    
                    print(f"  Extracted: {filename}")
        
        print("✓ Extraction complete!")
        return True
        
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        return False

def cleanup():
    """Remove temporary files"""
    print("\nCleaning up...")
    try:
        if TEMP_ZIP.exists():
            TEMP_ZIP.unlink()
        print("✓ Cleanup complete!")
    except Exception as e:
        print(f"Warning: Could not clean up temp files: {e}")

def verify_installation():
    """Verify ffmpeg is installed correctly"""
    print("\nVerifying installation...")
    
    ffmpeg_exe = FFMPEG_DIR / "bin" / "ffmpeg.exe"
    ffprobe_exe = FFMPEG_DIR / "bin" / "ffprobe.exe"
    
    if ffmpeg_exe.exists() and ffprobe_exe.exists():
        print(f"✓ FFmpeg installed successfully!")
        print(f"  Location: {FFMPEG_DIR / 'bin'}")
        print(f"  Files:")
        print(f"    - ffmpeg.exe")
        print(f"    - ffprobe.exe")
        print(f"    - ffplay.exe")
        return True
    else:
        print("✗ Installation verification failed!")
        return False

def main():
    """Main function"""
    # Check if already installed
    if (FFMPEG_DIR / "bin" / "ffmpeg.exe").exists():
        print("=" * 60)
        print("FFmpeg is already installed!")
        print(f"Location: {FFMPEG_DIR / 'bin'}")
        print("=" * 60)
        response = input("\nDo you want to reinstall? (y/n): ").strip().lower()
        if response != 'y':
            print("\nExiting...")
            return
        
        # Remove existing installation
        print("\nRemoving existing installation...")
        try:
            shutil.rmtree(FFMPEG_DIR)
            print("✓ Removed old installation")
        except Exception as e:
            print(f"✗ Could not remove old installation: {e}")
            return
    
    # Download
    if not download_ffmpeg():
        cleanup()
        return
    
    # Extract
    if not extract_ffmpeg():
        cleanup()
        return
    
    # Cleanup
    cleanup()
    
    # Verify
    if verify_installation():
        print("\n" + "=" * 60)
        print("SUCCESS! FFmpeg is ready to use.")
        print("You can now run mp3gain_gui.py")
        print("=" * 60)
    else:
        print("\nInstallation may have issues. Please check manually.")
    
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        cleanup()
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        cleanup()
