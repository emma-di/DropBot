import librosa
import numpy as np
import msaf

def estimate_key(chroma):
    chroma_avg = chroma.mean(axis=1)
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F',
            'F#', 'G', 'G#', 'A', 'A#', 'B']
    return keys[int(chroma_avg.argmax())]

def analyze_song(file_path):
    # Load audio
    y, sr = librosa.load(file_path, mono=True)
    bpm, _ = librosa.beat.beat_track(y=y, sr=sr)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key = estimate_key(chroma)
    duration = librosa.get_duration(y=y, sr=sr)

    # Structure analysis using MSAF
    boundaries, labels = msaf.process(file_path, "cnmf")
    
    # Package the result
    section_info = [
        {"start": round(float(start), 2), "label": label}
        for start, label in zip(boundaries, labels)
    ]

    return {
        "bpm": round(bpm),
        "key": key,
        "duration": round(duration, 2),
        "sections": section_info
    }