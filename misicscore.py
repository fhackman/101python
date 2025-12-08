import librosa
import numpy as np
from music21 import stream, note, tempo, meter, midi

def audio_to_notes(y, sr):
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo_val, _beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    notes = []

    pitches, _magnitudes = librosa.piptrack(y=y, sr=sr)

    for onset in librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr):
        start = onset
        end = start + 1
        pitch = pitches[:, start:end].flatten()
        pitch = pitch[pitch > 0]

        if len(pitch) > 0:
            pitch_midi = np.median(librosa.hz_to_midi(pitch))
            notes.append(pitch_midi)
    
    return notes, tempo_val

def notes_to_midi(notes, tempo_val):
    s = stream.Score()
    part = stream.Part()
    part.append(tempo.MetronomeMark(number=tempo_val))
    part.append(meter.TimeSignature('4/4'))
    
    for pitch in notes:
        if pitch > 0:
            part.append(note.Note(pitch))
        else:
            part.append(note.Rest(quarterLength=0.5))
    
    s.append(part)
    
    # Write to MIDI file
    mf = midi.translate.music21ObjectToMidiFile(s)
    mf.open('output_music_score.mid', 'wb')
    mf.write()
    mf.close()

# Load the audio file
filename = 'endless_rain.mp3'
y, sr = librosa.load(filename)

# Extract notes
notes, tempo_val = audio_to_notes(y, sr)

# Convert notes to MIDI
notes_to_midi(notes, tempo_val)
