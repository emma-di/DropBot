# to run: python split_audio.py

import os
import subprocess
from pydub import AudioSegment
import simpleaudio as sa
from tkinter import filedialog, Tk

# STEP 1: Let user pick a file
def pick_audio_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select an audio file",
        filetypes=[("Audio Files", "*.mp3")],
        initialdir=os.path.join("data", "mp3s")
    )
    return file_path

# STEP 2: Split using Demucs via CLI
def split_song(file_path):
    song_name = os.path.splitext(os.path.basename(file_path))[0]
    stem_folder = os.path.join("data", "separated", "htdemucs", song_name)

    if not os.path.exists(stem_folder):
        print("Running Demucs to split stems...")
        subprocess.run(["demucs", "--name", "htdemucs", "--out", "data", file_path], check=True)
    else:
        print(f"Using existing stems: {stem_folder}")

    return song_name

# STEP 3: Play selected stem
def play_stem(stem_file):
    sound = AudioSegment.from_wav(stem_file)
    play_obj = sa.play_buffer(
        sound.raw_data,
        num_channels=sound.channels,
        bytes_per_sample=sound.sample_width,
        sample_rate=sound.frame_rate
    )
    play_obj.wait_done()

# === RUN ===
if __name__ == "__main__":
    file_path = pick_audio_file()
    if not file_path:
        print("No file selected.")
        exit()

    song_name = split_song(file_path)

    # Example: Play vocals
    stem_folder = os.path.join("data", "separated", "htdemucs", song_name)
    stem_path = os.path.join(stem_folder, "vocals.wav")
    play_stem(stem_path)