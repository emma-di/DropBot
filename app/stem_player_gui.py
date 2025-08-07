# python -m app.stem_player_gui

import os
from pydub import AudioSegment
import simpleaudio as sa
from tkinter import Tk, Label, Button, StringVar, filedialog
from tkinter import Checkbutton, BooleanVar
from calibrate.split_audio import split_song  # import your splitting logic

# Global state
stem_status = {
    "vocals": True,
    "drums": True,
    "bass": True,
    "other": True
}
song_name = ""
status_vars = {}

def pick_audio_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select an audio file",
        filetypes=[("Audio Files", "*.mp3")],
        initialdir="data/mp3s"
    )
    root.destroy()
    return file_path

def play_current_mix():
    folder = os.path.join("data", "separated", "htdemucs", song_name)
    mixed = None
    print("🎛️ Mixing the following stems:")

    for stem, enabled in stem_status.items():
        path = os.path.join(folder, f"{stem}.wav")
        if enabled and os.path.exists(path):
            print(f"✅ {stem}")
            audio = AudioSegment.from_wav(path)
            mixed = audio if mixed is None else mixed.overlay(audio)
        else:
            print(f"❌ {stem} skipped")

    if mixed is None:
        print("No stems selected!")
        return

    play_obj = sa.play_buffer(
        mixed.raw_data,
        num_channels=mixed.channels,
        bytes_per_sample=mixed.sample_width,
        sample_rate=mixed.frame_rate
    )
    play_obj.wait_done()

def toggle_stem(event):
    key_map = {
        "1": "vocals",
        "2": "drums",
        "3": "bass",
        "4": "other"
    }
    key = event.char
    if key in key_map:
        stem = key_map[key]
        stem_status[stem] = not stem_status[stem]
        update_stem_labels()

def update_stem_labels():
    for stem, var in status_vars.items():
        state = "ON ✅" if stem_status[stem] else "OFF ❌"
        var.set(f"{stem.title()}: {state}")

# === GUI setup ===
if __name__ == "__main__":
    file_path = pick_audio_file()
    if not file_path:
        print("No file selected.")
        exit()

    song_name = split_song(file_path)

    app = Tk()
    app.title("AI DJ Stem Player")

    Label(app, text="Select which stems to include:").pack()

    stem_vars = {}

    for stem in stem_status:
        var = BooleanVar(value=True)
        stem_vars[stem] = var
        cb = Checkbutton(app, text=stem.title(), variable=var)
        cb.pack()

    def sync_stems():
        print("🔄 Syncing checkbox values to stem_status:")
        for stem in stem_vars:
            checked = stem_vars[stem].get()
            print(f"  {stem}: {'✅' if checked else '❌'}")
            stem_status[stem] = checked
        play_current_mix()

    Button(app, text="Play Current Mix", command=sync_stems).pack()
    
    app.mainloop()