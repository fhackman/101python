# MP3Gain Normalizer - FFmpeg Setup

This document explains how to set up FFmpeg for the MP3Gain Normalizer application.

## Option 1: Automatic Setup (Recommended for Windows)

Run the provided setup script:

```bash
python setup_ffmpeg.py
```

This will automatically:

- Download FFmpeg (Windows essentials build, ~80 MB)
- Extract it to the `ffmpeg/bin/` folder
- Verify the installation

## Option 2: Manual Setup

### Windows

1. Download FFmpeg from: https://www.gyan.dev/ffmpeg/builds/
2. Download the "essentials" build (ffmpeg-release-essentials.zip)
3. Extract the zip file
4. Create folder structure: `mp3gain_folder/ffmpeg/bin/`
5. Copy these files to the bin folder:
   - `ffmpeg.exe`
   - `ffprobe.exe`
   - `ffplay.exe`

### Linux

Install system-wide:

```bash
sudo apt install ffmpeg
```

### macOS

Install using Homebrew:

```bash
brew install ffmpeg
```

## Folder Structure

After setup, your folder should look like this:

```
101Python/
├── mp3gain_gui.py
├── setup_ffmpeg.py
├── requirements.txt
└── ffmpeg/
    └── bin/
        ├── ffmpeg.exe
        ├── ffprobe.exe
        └── ffplay.exe
```

## Verification

Run the MP3Gain application:

```bash
python mp3gain_gui.py
```

If FFmpeg is set up correctly:

- No error dialog will appear
- Terminal log will show: "> Using local ffmpeg from: ffmpeg/bin/"

## Troubleshooting

**Error: "ffmpeg or avconv is required"**

- Make sure ffmpeg.exe is in the correct location: `ffmpeg/bin/ffmpeg.exe`
- Check that the bin folder contains ffmpeg.exe, ffprobe.exe, and ffplay.exe
- Try running: `python setup_ffmpeg.py` to reinstall

**Download fails in setup script**

- Check your internet connection
- Try downloading manually from: https://www.gyan.dev/ffmpeg/builds/
- Place the files in `ffmpeg/bin/` as described in Manual Setup

**Application still doesn't find FFmpeg**

- Restart the application after setting up FFmpeg
- Check that folder structure matches exactly as shown above
