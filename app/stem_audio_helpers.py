import numpy as np
import librosa
import pygame
import soundfile as sf
import os
from calibrate.split_audio import split_song

class StemAudioEngine:
    """Handles all audio processing operations"""
    
    def __init__(self):
        pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
        pygame.mixer.init()
        
        self.stems = {}
        self.original_stems = {}
        self.processed_stems = {}
        self.current_sound = None
        self.current_volumes = {}
        
    def load_song_stems(self, file_path):
        """Load and split song, then prepare stems for playback"""
        song_name = split_song(file_path)
        stem_folder = os.path.join("data", "separated", "htdemucs", song_name)
        
        stem_names = ["vocals", "drums", "bass", "other"]
        loaded_stems = {}
        
        for stem_name in stem_names:
            stem_path = os.path.join(stem_folder, f"{stem_name}.wav")
            if os.path.exists(stem_path):
                # Load stem audio data
                audio, sr = librosa.load(stem_path, sr=44100, mono=False)
                if len(audio.shape) == 1:
                    audio = np.stack([audio, audio])  # Convert to stereo
                
                loaded_stems[stem_name] = audio
                print(f"✅ Loaded {stem_name}")
            else:
                print(f"❌ {stem_name} not found")
        
        self.original_stems = loaded_stems
        self.processed_stems = loaded_stems.copy()
        self.current_volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        return song_name
    
    def apply_effects_to_stems(self, speed=1.0, pitch_shift=0):
        """Apply speed and pitch effects to all stems"""
        print(f"Applying effects: speed={speed}, pitch={pitch_shift}")
        
        for stem_name in self.original_stems:
            audio = self.original_stems[stem_name].copy()
            
            # Apply pitch shift first
            if pitch_shift != 0:
                print(f"  Pitch shifting {stem_name} by {pitch_shift} semitones")
                audio = librosa.effects.pitch_shift(audio, sr=44100, n_steps=pitch_shift)
            
            # Apply speed change
            if speed != 1.0:
                print(f"  Time stretching {stem_name} by {speed}x")
                audio = librosa.effects.time_stretch(audio, rate=speed)
            
            self.processed_stems[stem_name] = audio
        
        print("✅ Effects applied to all stems")
    
    def create_mixed_audio(self, volumes):
        """Create mixed audio with current volume settings"""
        if not self.processed_stems:
            return np.zeros((2, 44100))  # 1 second of silence
        
        mixed = None
        
        for stem_name, audio in self.processed_stems.items():
            volume = volumes.get(stem_name, 1.0)
            if volume > 0:
                processed_audio = audio * volume
                
                if mixed is None:
                    mixed = processed_audio
                else:
                    # Ensure same length
                    min_len = min(mixed.shape[1], processed_audio.shape[1])
                    mixed = mixed[:, :min_len] + processed_audio[:, :min_len]
        
        return mixed if mixed is not None else np.zeros((2, 44100))
    
    def play_audio(self, volumes, force_restart=False):
        """Play mixed audio with current settings"""
        print(f"play_audio called with volumes: {volumes}, force_restart: {force_restart}")
        
        # Check if only volumes changed (no restart needed)
        if not force_restart and self.current_sound and self.current_sound.get_busy():
            volumes_changed = any(
                abs(volumes.get(stem, 1.0) - self.current_volumes.get(stem, 1.0)) > 0.01
                for stem in volumes
            )
            
            if volumes_changed:
                print("  -> Only volumes changed, but pygame doesn't support real-time volume mixing")
                print("  -> Will restart playback with new volumes")
        
        # Update current volumes
        self.current_volumes = volumes.copy()
        
        mixed_audio = self.create_mixed_audio(volumes)
        
        # Convert to pygame format
        if mixed_audio.shape[0] == 2:
            # Transpose from (2, samples) to (samples, 2)
            audio_data = mixed_audio.T
        else:
            audio_data = mixed_audio.reshape(-1, 1)
        
        # Convert to int16 and ensure C-contiguous
        audio_data = (audio_data * 32767).astype(np.int16)
        audio_data = np.ascontiguousarray(audio_data)
        
        # Stop current sound if playing
        self.stop_playback()
        
        # Create and play new sound
        self.current_sound = pygame.sndarray.make_sound(audio_data)
        self.current_sound.play()
        
        return self.current_sound
    
    def stop_playback(self):
        """Stop all audio playback"""
        pygame.mixer.stop()
        if self.current_sound:
            self.current_sound.stop()
            self.current_sound = None