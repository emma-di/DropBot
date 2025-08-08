import sounddevice as sd
import numpy as np
import time

# Simple sine wave test
def test_callback(outdata, frames, time, status):
    if status:
        print(status)
    
    # Generate simple sine wave
    t = np.linspace(0, frames/44100, frames)
    outdata[:, 0] = 0.1 * np.sin(2 * np.pi * 440 * t)  # 440Hz tone
    outdata[:, 1] = outdata[:, 0]  # Stereo

print("Testing basic sounddevice...")
with sd.OutputStream(callback=test_callback, samplerate=44100, channels=2):
    time.sleep(3)  # Play for 3 seconds

print("Test complete. Did you hear a clean tone or clicking/popping?")