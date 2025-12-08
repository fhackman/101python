# Android Build Instructions for PA Scanner

Since you are on Windows, the easiest way to build the APK is using **Google Colab**. Buildozer (the tool used to package Python apps for Android) works best in a Linux environment.

## Steps to Build APK

1.  **Download the Source Files**
    Ensure you have the following files ready:

    - `main.py` (This is the Android-compatible version of your scanner)
    - `buildozer.spec` (Configuration file)

2.  **Open Google Colab**
    Go to [Google Colab](https://colab.research.google.com/) and create a new notebook.

3.  **Upload Files**
    Click the folder icon on the left sidebar and upload `main.py` and `buildozer.spec`.

4.  **Run Build Commands**
    Copy and paste the following commands into a code cell in Colab and run it:

    ```python
    !pip install buildozer cython==0.29.33
    !sudo apt-get install -y \
        python3-pip \
        build-essential \
        git \
        python3 \
        python3-dev \
        ffmpeg \
        libsdl2-dev \
        libsdl2-image-dev \
        libsdl2-mixer-dev \
        libsdl2-ttf-dev \
        libportmidi-dev \
        libswscale-dev \
        libavformat-dev \
        libavcodec-dev \
        zlib1g-dev

    !buildozer android debug
    ```

5.  **Download APK**

    - The build process will take 15-20 minutes.
    - Once finished, the APK file will be in the `bin/` directory.
    - Right-click the `.apk` file and download it.

6.  **Install on Android**
    - Transfer the APK to your Android phone.
    - Enable "Install from Unknown Sources" in your settings.
    - Install and run the app.

## Features Added

- **Mock MT5**: Since standard MT5 Python library doesn't work on Android, a simulation layer is used.
- **Trading Controls**: Added Buy/Sell buttons with TP (Take Profit) and SL (Stop Loss) inputs.
- **Kivy UI**: A touch-friendly interface replacing the desktop Tkinter GUI.
