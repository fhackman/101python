#!/bin/bash
set -e

# Setup Directories
mkdir -p ~/.local/bin
mkdir -p ~/.local/java
mkdir -p ~/.buildozer/android/platform
mkdir -p ~/.buildozer/android/platform/android-sdk

# 0. Install System Dependencies
# echo "Installing system dependencies..."
# sudo apt-get update
# sudo apt-get install -y \
#     python3-pip \
#     build-essential \
#     git \
#     python3 \
#     python3-dev \
#     ffmpeg \
#     libsdl2-dev \
#     libsdl2-image-dev \
#     libsdl2-mixer-dev \
#     libsdl2-ttf-dev \
#     libportmidi-dev \
#     libswscale-dev \
#     libavformat-dev \
#     libavcodec-dev \
#     zlib1g-dev \
#     libffi-dev \
#     libssl-dev \
#     autoconf \
#     libtool \
#     pkg-config \
#     zip \
#     unzip

# 1. Install Java (OpenJDK 17)
if [ ! -d "$HOME/.local/java/jdk-17.0.2" ]; then
    echo "Downloading OpenJDK 17..."
    curl -L https://download.java.net/java/GA/jdk17.0.2/dfd4a8d0985749f896bed50d7138ee7f/8/GPL/openjdk-17.0.2_linux-x64_bin.tar.gz -o openjdk.tar.gz
    echo "Extracting OpenJDK 17..."
    tar -xzf openjdk.tar.gz -C ~/.local/java/
    rm openjdk.tar.gz
fi
export JAVA_HOME="$HOME/.local/java/jdk-17.0.2"
export PATH="$JAVA_HOME/bin:$PATH"

# 2. Create zip/unzip wrappers using Python
# zip wrapper
cat > ~/.local/bin/zip << 'EOF'
#!/usr/bin/env python3
import sys
import zipfile
import os

def zip_files(output_filename, source_paths):
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for path in source_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, os.path.dirname(path))
                        zf.write(file_path, arcname)
            else:
                if os.path.exists(path):
                     zf.write(path, os.path.basename(path))

args = sys.argv[1:]
files = []
output = None
skip_next = False

for i, arg in enumerate(args):
    if skip_next:
        skip_next = False
        continue
    if arg.startswith('-'):
        continue
    if output is None:
        output = arg
    else:
        files.append(arg)

if output and files:
    zip_files(output, files)
EOF
chmod +x ~/.local/bin/zip

# unzip wrapper
cat > ~/.local/bin/unzip << 'EOF'
#!/usr/bin/env python3
import sys
import zipfile
import os
import stat

def unzip_file(zip_filename, dest_dir):
    with zipfile.ZipFile(zip_filename, 'r') as zf:
        for info in zf.infolist():
            extracted_path = zf.extract(info, dest_dir)
            
            # Restore permissions
            perm = info.external_attr >> 16
            if perm:
                os.chmod(extracted_path, perm)
            
            # Handle symlinks
            if stat.S_ISLNK(perm):
                # The extracted file contains the target path
                with open(extracted_path, 'r') as f:
                    target = f.read()
                os.remove(extracted_path)
                try:
                    os.symlink(target, extracted_path)
                except FileExistsError:
                    pass

args = sys.argv[1:]
zip_file = None
dest_dir = "."

skip_next = False
for i, arg in enumerate(args):
    if skip_next:
        skip_next = False
        continue
    if arg == '-d':
        if i + 1 < len(args):
            dest_dir = args[i+1]
            skip_next = True
        continue
    if arg.startswith('-'):
        continue
    if zip_file is None:
        zip_file = arg

if zip_file:
    unzip_file(zip_file, dest_dir)
EOF
chmod +x ~/.local/bin/unzip

export PATH="$HOME/.local/bin:$PATH"

# 3. Manually Install Android NDK r25b
NDK_DIR="$HOME/.buildozer/android/platform/android-ndk-r25b"
if [ ! -d "$NDK_DIR" ]; then
    echo "Downloading Android NDK r25b..."
    curl -L -C - https://dl.google.com/android/repository/android-ndk-r25b-linux.zip -o ndk.zip
    echo "Extracting Android NDK..."
    python3 -c "import zipfile; zipfile.ZipFile('ndk.zip').extractall('$HOME/.buildozer/android/platform/')"
    rm ndk.zip
    echo "NDK Installed."
else
    echo "Android NDK already exists."
fi

# 4. Manually Install Android SDK Command Line Tools
SDK_TOOLS_DIR="$HOME/.buildozer/android/platform/android-sdk/tools"
if [ ! -d "$SDK_TOOLS_DIR" ]; then
    echo "Downloading Android SDK Command Line Tools..."
    curl -L -C - https://dl.google.com/android/repository/commandlinetools-linux-6514223_latest.zip -o cmdline-tools.zip
    echo "Extracting SDK Tools..."
    python3 -c "import zipfile; zipfile.ZipFile('cmdline-tools.zip').extractall('$HOME/.buildozer/android/platform/android-sdk/')"
    rm cmdline-tools.zip
    echo "SDK Tools Installed."
else
    echo "Android SDK Tools already exists."
fi

# Fix permissions for SDK tools
chmod +x "$SDK_TOOLS_DIR/bin/sdkmanager"
chmod +x "$SDK_TOOLS_DIR/bin/avdmanager"

# 5. Run Buildozer
echo "Starting Buildozer..."
pip3 install cython==0.29.33
# Force accept license if needed
yes | buildozer android debug > build_log.txt 2>&1
