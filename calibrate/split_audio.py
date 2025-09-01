# to run: python split_audio.py

import os
import subprocess
import glob
from pydub import AudioSegment
import simpleaudio as sa
from tkinter import filedialog, Tk

# STEP 1: Let user pick a file
def pick_audio_file():
    root = Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(
        title="Select an audio file",
        filetypes=[("Audio Files", "*.mp3 *.wav")],
        initialdir=os.path.join("data", "mp3s")
    )
    root.destroy()
    return file_path

# STEP 2: Split using Demucs via CLI with better folder detection
def split_song(file_path):
    song_name = os.path.splitext(os.path.basename(file_path))[0]
    
    # Clean up song name (remove special characters that might cause issues)
    clean_song_name = "".join(c for c in song_name if c.isalnum() or c in (' ', '-', '_')).strip()
    clean_song_name = clean_song_name.replace(' ', '_')
    
    print(f"🎵 Processing: {song_name}")
    print(f"🔧 Clean name: {clean_song_name}")
    
    # Expected stem folder patterns - ONLY htdemucs
    possible_folders = [
        os.path.join("data", "separated", "htdemucs", song_name),
        os.path.join("data", "separated", "htdemucs", clean_song_name)
    ]
    
    # Check if stems already exist
    existing_folder = None
    for folder in possible_folders:
        if os.path.exists(folder) and has_all_stems(folder):
            existing_folder = folder
            print(f"✅ Found existing stems: {folder}")
            break
    
    if not existing_folder:
        print("🎛️ Running Demucs to split stems...")
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        try:
            # Run Demucs with htdemucs model
            result = subprocess.run([
                "demucs", 
                "--name", "htdemucs",
                "--out", "data",
                file_path
            ], check=True, capture_output=True, text=True)
            
            print("✅ Demucs separation completed")
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Demucs failed: {e}")
            print(f"stdout: {e.stdout}")
            print(f"stderr: {e.stderr}")
            
            # Try alternative approach
            try:
                print("🔄 Trying alternative Demucs command...")
                subprocess.run([
                    "python", "-m", "demucs.separate", 
                    "--name", "htdemucs",
                    "--out", "data",
                    file_path
                ], check=True)
                print("✅ Alternative Demucs succeeded")
            except:
                print("❌ Both Demucs methods failed")
                return None
        
        # Find the actual created folder
        stem_folder = find_actual_stem_folder("data", song_name, clean_song_name)
        
    else:
        stem_folder = existing_folder
    
    if stem_folder and has_all_stems(stem_folder):
        print(f"✅ Stems ready: {stem_folder}")
        return os.path.basename(stem_folder)
    else:
        print(f"❌ Could not find or create stems for: {song_name}")
        return None

def find_actual_stem_folder(data_dir, original_name, clean_name):
    """Find the actual folder created by Demucs - ONLY in htdemucs"""
    
    # Only look in htdemucs directory
    htdemucs_dir = os.path.join(data_dir, "separated", "htdemucs")
    if not os.path.exists(htdemucs_dir):
        print(f"❌ No htdemucs directory found: {htdemucs_dir}")
        return None
    
    print(f"🔍 Checking htdemucs directory...")
    
    # Look for folders matching our song names
    potential_names = [original_name, clean_name]
    
    for folder_name in os.listdir(htdemucs_dir):
        folder_path = os.path.join(htdemucs_dir, folder_name)
        
        if os.path.isdir(folder_path):
            print(f"   Found folder: {folder_name}")
            
            # Check if this folder contains stems
            if has_all_stems(folder_path):
                print(f"✅ Found valid stem folder: {folder_path}")
                return folder_path
            
            # Also check if folder name is similar to our song
            for potential_name in potential_names:
                if (potential_name.lower() in folder_name.lower() or 
                    folder_name.lower() in potential_name.lower()):
                    if has_all_stems(folder_path):
                        print(f"✅ Found matching stem folder: {folder_path}")
                        return folder_path
    
    print("❌ No valid stem folder found in htdemucs")
    return None

def has_all_stems(folder_path):
    """Check if folder contains all required stem files"""
    required_stems = ["vocals.wav", "drums.wav", "bass.wav", "other.wav"]
    
    for stem in required_stems:
        stem_path = os.path.join(folder_path, stem)
        if not os.path.exists(stem_path):
            print(f"   Missing: {stem}")
            return False
    
    print(f"   ✅ All stems present in: {folder_path}")
    return True

def get_stem_folder_path(song_name):
    """Get the full path to the stem folder"""
    base_dir = "data/separated"
    
    # Try different model directories
    model_dirs = ["htdemucs", "mdx_extra", "mdx", "demucs"]
    
    for model_dir in model_dirs:
        potential_path = os.path.join(base_dir, model_dir, song_name)
        if os.path.exists(potential_path) and has_all_stems(potential_path):
            return potential_path
    
    return None

# STEP 3: Play selected stem
def play_stem(stem_file):
    try:
        if not os.path.exists(stem_file):
            print(f"❌ Stem file not found: {stem_file}")
            return
        
        print(f"🎵 Playing: {stem_file}")
        sound = AudioSegment.from_wav(stem_file)
        play_obj = sa.play_buffer(
            sound.raw_data,
            num_channels=sound.channels,
            bytes_per_sample=sound.sample_width,
            sample_rate=sound.frame_rate
        )
        play_obj.wait_done()
        
    except Exception as e:
        print(f"❌ Error playing stem: {e}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    file_path = pick_audio_file()
    if not file_path:
        print("❌ No file selected.")
        exit()

    song_name = split_song(file_path)
    if not song_name:
        print("❌ Failed to split song.")
        exit()

    # Find the actual stem folder
    stem_folder = get_stem_folder_path(song_name)
    if not stem_folder:
        print(f"❌ Could not locate stem folder for: {song_name}")
        exit()

    # Example: Play vocals
    vocals_path = os.path.join(stem_folder, "vocals.wav")
    if os.path.exists(vocals_path):
        print(f"🎤 Playing vocals from: {vocals_path}")
        play_stem(vocals_path)
    else:
        print(f"❌ Vocals not found at: {vocals_path}")
        
    print(f"🎛️ All stems available in: {stem_folder}")
    print("   - vocals.wav")  
    print("   - drums.wav")
    print("   - bass.wav")
    print("   - other.wav")