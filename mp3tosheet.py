import librosa
import numpy as np
from music21 import stream, note, tempo

# Function to convert audio to notes
def audio_to_notes(y, sr):
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo_val, _beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    notes = []
    
    for onset in librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr):
        start = librosa.frames_to_time(onset, sr=sr)
        _end = start + 0.5  # assuming a fixed duration for simplicity
        pitches, _magnitudes = librosa.piptrack(y=y, sr=sr, hop_length=512)
        pitch = pitches[:, onset]
        note_pitch = np.max(pitch)
        if note_pitch > 0:
            notes.append(note_pitch)
    
    return notes, tempo_val

# Function to convert notes to sheet music
def notes_to_sheet_music(notes, tempo_val, instrument):
    s = stream.Stream()
    s.append(tempo.MetronomeMark(number=tempo_val))
    
    for n in notes:
        if n > 0:
            s.append(note.Note(librosa.hz_to_midi(n)))
    
    s.write('midi', fp=f'{instrument}_output.mid')

# Load the audio file
filename = 'endless_rain.mp3'
y, sr = librosa.load(filename)

# Extract notes for different instruments (this is a simplification)
# Ideally, you should isolate the instruments first (e.g., using source separation)
guitar_notes, tempo_val = audio_to_notes(y, sr)
piano_notes, tempo_val = audio_to_notes(y, sr)
drum_notes, tempo_val = audio_to_notes(y, sr)

# Convert notes to sheet music
notes_to_sheet_music(guitar_notes, tempo_val, 'guitar')
notes_to_sheet_music(piano_notes, tempo_val, 'piano')
notes_to_sheet_music(drum_notes, tempo_val, 'drum')
