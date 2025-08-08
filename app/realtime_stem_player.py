# python -m app.realtime_stem_player

import pygame
import numpy as np
import librosa
import soundfile as sf
import threading
import time
from tkinter import Tk, Label, Scale, Button, filedialog, Frame
from tkinter import HORIZONTAL
from calibrate.split_audio import split_song
import os

class RealTimeStemPlayer:
    def __init__(self):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=512)
        pygame.mixer.init()
        
        self.stems = {}
        self.original_stems = {}
        self.stem_channels = {}
        self.is_playing = False
        self.position = 0
        self.song_name = ""
        
        # Control parameters
        self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.speed = 1.0
        self.pitch = 0  # semitones
        
        self.setup_gui()
        
    def load_song(self, file_path):
        """Load and split song, then prepare stems for playback"""
        self.song_name = split_song(file_path)
        stem_folder = os.path.join("data", "separated", "htdemucs", self.song_name)
        
        stem_names = ["vocals", "drums", "bass", "other"]
        
        for stem_name in stem_names:
            stem_path = os.path.join(stem_folder, f"{stem_name}.wav")
            if os.path.exists(stem_path):
                # Load stem audio data
                audio, sr = librosa.load(stem_path, sr=44100, mono=False)
                if len(audio.shape) == 1:
                    audio = np.stack([audio, audio])  # Convert to stereo
                
                self.original_stems[stem_name] = audio
                self.stems[stem_name] = audio
                print(f"✅ Loaded {stem_name}")
            else:
                print(f"❌ {stem_name} not found")
        
        self.update_title()
    
    def apply_effects(self, audio, speed=1.0, pitch_shift=0):
        """Apply speed and pitch effects to audio"""
        if speed != 1.0:
            # Time stretching
            audio = librosa.effects.time_stretch(audio, rate=speed)
        
        if pitch_shift != 0:
            # Pitch shifting
            audio = librosa.effects.pitch_shift(audio, sr=44100, n_steps=pitch_shift)
        
        return audio
    
    def mix_stems(self):
        """Mix all active stems with their current volume levels"""
        if not self.stems:
            return np.zeros((2, 1024))  # Return silence
        
        mixed = None
        
        for stem_name, audio in self.stems.items():
            volume = self.volumes[stem_name]
            if volume > 0:
                # Apply volume
                processed_audio = audio * volume
                
                if mixed is None:
                    mixed = processed_audio
                else:
                    # Make sure both arrays have the same length
                    min_len = min(mixed.shape[1], processed_audio.shape[1])
                    mixed = mixed[:, :min_len] + processed_audio[:, :min_len]
        
        return mixed if mixed is not None else np.zeros((2, 1024))
    
    def update_stems_realtime(self):
        """Update all stems with current speed/pitch settings"""
        for stem_name in self.original_stems:
            processed = self.apply_effects(
                self.original_stems[stem_name], 
                speed=self.speed, 
                pitch_shift=self.pitch
            )
            self.stems[stem_name] = processed
    
    def play_mixed_audio(self):
        """Play the mixed audio using pygame"""
        mixed_audio = self.mix_stems()
        
        # Convert to pygame format
        if mixed_audio.shape[0] == 2:  # Stereo
            # Interleave stereo channels
            audio_data = np.zeros(mixed_audio.shape[1] * 2, dtype=np.float32)
            audio_data[0::2] = mixed_audio[0]  # Left channel
            audio_data[1::2] = mixed_audio[1]  # Right channel
        else:
            audio_data = mixed_audio.flatten()
        
        # Convert to int16 and scale
        audio_data = (audio_data * 32767).astype(np.int16)
        
        # Create pygame sound object
        sound = pygame.sndarray.make_sound(audio_data)
        sound.play()
    
    def on_volume_change(self, stem_name, value):
        """Handle volume slider changes"""
        self.volumes[stem_name] = float(value) / 100.0
        if self.is_playing:
            self.restart_playback()
    
    def on_speed_change(self, value):
        """Handle speed slider changes"""
        new_speed = float(value) / 100.0
        if abs(new_speed - self.speed) > 0.01:  # Only update if significant change
            self.speed = new_speed
            self.update_stems_realtime()
            if self.is_playing:
                self.restart_playback()
    
    def on_pitch_change(self, value):
        """Handle pitch slider changes"""
        new_pitch = int(value)
        if new_pitch != self.pitch:
            self.pitch = new_pitch
            self.update_stems_realtime()
            if self.is_playing:
                self.restart_playback()
    
    def play_pause(self):
        """Toggle play/pause"""
        if self.is_playing:
            pygame.mixer.stop()
            self.is_playing = False
            self.play_button.config(text="▶ Play")
        else:
            self.play_mixed_audio()
            self.is_playing = True
            self.play_button.config(text="⏸ Pause")
    
    def restart_playback(self):
        """Restart playback with current settings"""
        if self.is_playing:
            pygame.mixer.stop()
            self.play_mixed_audio()
    
    def setup_gui(self):
        """Setup the GUI"""
        self.root = Tk()
        self.root.title("🎛️ Real-Time AI DJ Stem Player")
        self.root.geometry("600x500")
        
        # File selection
        Button(self.root, text="📁 Load Song", command=self.select_file).pack(pady=10)
        
        self.title_label = Label(self.root, text="No song loaded", font=("Arial", 12, "bold"))
        self.title_label.pack()
        
        # Play/Pause button
        self.play_button = Button(self.root, text="▶ Play", command=self.play_pause, 
                                 font=("Arial", 14), bg="#4CAF50", fg="white")
        self.play_button.pack(pady=10)
        
        # Volume controls frame
        vol_frame = Frame(self.root)
        vol_frame.pack(pady=10)
        
        Label(vol_frame, text="🎚️ VOLUME CONTROLS", font=("Arial", 12, "bold")).pack()
        
        self.volume_sliders = {}
        stem_names = ["vocals", "drums", "bass", "other"]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
        
        for i, stem_name in enumerate(stem_names):
            frame = Frame(vol_frame)
            frame.pack(fill='x', padx=20, pady=5)
            
            Label(frame, text=f"{stem_name.title()}:", width=8, anchor='w').pack(side='left')
            
            slider = Scale(frame, from_=0, to=150, orient=HORIZONTAL, 
                          command=lambda val, name=stem_name: self.on_volume_change(name, val))
            slider.set(100)  # Default volume
            slider.pack(side='right', fill='x', expand=True)
            
            self.volume_sliders[stem_name] = slider
        
        # Speed control
        speed_frame = Frame(self.root)
        speed_frame.pack(pady=10, fill='x')
        
        Label(speed_frame, text="🏃 SPEED", font=("Arial", 12, "bold")).pack()
        Label(speed_frame, text="50% = Half Speed | 100% = Normal | 200% = Double Speed").pack()
        
        self.speed_slider = Scale(speed_frame, from_=50, to=200, orient=HORIZONTAL, 
                                 command=lambda val: self.on_speed_change(val))
        self.speed_slider.set(100)
        self.speed_slider.pack(fill='x', padx=20)
        
        # Pitch control
        pitch_frame = Frame(self.root)
        pitch_frame.pack(pady=10, fill='x')
        
        Label(pitch_frame, text="🎵 PITCH", font=("Arial", 12, "bold")).pack()
        Label(pitch_frame, text="-12 = One Octave Down | 0 = Normal | +12 = One Octave Up").pack()
        
        self.pitch_slider = Scale(pitch_frame, from_=-12, to=12, orient=HORIZONTAL,
                                 command=lambda val: self.on_pitch_change(val))
        self.pitch_slider.set(0)
        self.pitch_slider.pack(fill='x', padx=20)
        
        # Instructions
        instructions = Label(self.root, 
                           text="💡 Tip: Adjust sliders while playing for real-time effects!",
                           font=("Arial", 10), fg="gray")
        instructions.pack(pady=10)
    
    def select_file(self):
        """File selection dialog"""
        file_path = filedialog.askopenfilename(
            title="Select an audio file",
            filetypes=[("Audio Files", "*.mp3 *.wav")],
            initialdir="data/mp3s"
        )
        
        if file_path:
            self.load_song(file_path)
    
    def update_title(self):
        """Update the title label with current song"""
        if self.song_name:
            self.title_label.config(text=f"🎵 {self.song_name}")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = RealTimeStemPlayer()
    app.run()