# python -m calibrate.calibrate_track

from calibrate.split_audio import split_song
from calibrate.analyze_audio import analyze_song
import json
import os

def calibrate_track(file_path):
    # Step 1: Split if needed
    song_name = split_song(file_path)

    # Step 2: Analyze song (BPM, key, structure)
    metadata = analyze_song(file_path)

    # Step 3: Save metadata
    out_path = os.path.join("data", "metadata", f"{song_name}.json")
    with open(out_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Calibrated and saved metadata to {out_path}")

if __name__ == "__main__":
    from tkinter import filedialog, Tk
    root = Tk()
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(initialdir="data/mp3s", title="Pick a song")
    root.destroy()
    if path:
        calibrate_track(path)