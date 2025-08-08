import librosa
import numpy as np
import msaf
from msaf import input_output, run, utils
from pathlib import Path
import tempfile
import shutil
import os
import soundfile as sf

def estimate_key(chroma):
    # Krumhansl-Schmuckler key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    chroma_avg = chroma.mean(axis=1)
    # Normalize chroma
    chroma_avg = chroma_avg / chroma_avg.sum()
    
    best_correlation = -1
    best_key = 'C'
    best_mode = 'major'
    
    # Test all 24 keys (12 major + 12 minor)
    for shift in range(12):
        # Major key test
        shifted_major = np.roll(major_profile, shift)
        correlation = np.corrcoef(chroma_avg, shifted_major)[0, 1]
        if correlation > best_correlation:
            best_correlation = correlation
            best_key = keys[shift]
            best_mode = 'major'
        
        # Minor key test
        shifted_minor = np.roll(minor_profile, shift)
        correlation = np.corrcoef(chroma_avg, shifted_minor)[0, 1]
        if correlation > best_correlation:
            best_correlation = correlation
            best_key = keys[shift]
            best_mode = 'minor'
    
    return f"{best_key} {best_mode}"

def analyze_song(file_path):
    y, sr = librosa.load(file_path, mono=True)
    bpm, _ = librosa.beat.beat_track(y=y, sr=sr)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key = estimate_key(chroma)
    duration = librosa.get_duration(y=y, sr=sr)

    # Create a temporary file with a simple name to avoid path issues
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        temp_path = tmp_file.name
        # Convert to a simple path without special characters
        temp_path = temp_path.replace('\\', '/')
    
    try:
        # Save audio to temporary file
        sf.write(temp_path, y, sr)
        
        # Use the temporary file for MSAF processing
        boundaries, labels = msaf.process(
            temp_path,
            boundaries_id="olda",
            labels_id="scluster"
        )
        
        section_info = [
            {"start": round(float(start), 2), "label": label}
            for start, label in zip(boundaries, labels)
        ]
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass

    return {
        "bpm": round(float(bpm)),
        "key": key,
        "duration": round(duration, 2),
        "sections": section_info
    }