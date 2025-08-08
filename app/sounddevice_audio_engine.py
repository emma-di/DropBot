import numpy as np
import librosa
import sounddevice as sd
import threading
import time
import os
from calibrate.split_audio import split_song

class RealTimeStemAudioEngine:
    """Real-time audio engine using sounddevice for seamless mixing"""
    
    def __init__(self, sample_rate=44100, block_size=256):  # Smaller block for lower latency
        self.sample_rate = sample_rate
        self.block_size = block_size
        
        # Audio data storage
        self.original_stems = {}
        self.processed_stems = {}
        
        # Real-time control parameters
        self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.master_volume = 1.0
        self.is_playing = False
        self.current_position = 0
        
        # Stream
        self.stream = None
        
        # Initialize sounddevice with optimized settings
        try:
            sd.default.samplerate = self.sample_rate
            sd.default.channels = 2
            sd.default.dtype = 'float32'
            sd.default.latency = 'low'
            sd.default.never_drop_input = False  # Allow dropping for better performance
            print(f"✅ Sounddevice initialized: {sd.default.device}")
            print(f"   Sample rate: {self.sample_rate}, Block size: {self.block_size}")
        except Exception as e:
            print(f"❌ Sounddevice initialization error: {e}")
    
    def load_song_stems(self, file_path):
        """Load and prepare stems for real-time playback"""
        try:
            print("Loading stems for real-time playback...")
            
            song_name = split_song(file_path)
            stem_folder = os.path.join("data", "separated", "htdemucs", song_name)
            
            if not os.path.exists(stem_folder):
                raise FileNotFoundError(f"Stem folder not found: {stem_folder}")
            
            stem_names = ["vocals", "drums", "bass", "other"]
            loaded_stems = {}
            max_length = 0
            
            for stem_name in stem_names:
                stem_path = os.path.join(stem_folder, f"{stem_name}.wav")
                if os.path.exists(stem_path):
                    try:                        
                        # Load with exact sample rate matching
                        audio, sr = librosa.load(stem_path, sr=self.sample_rate, mono=False)
                        
                        if audio is None or len(audio) == 0:
                            print(f"⚠️ Warning: {stem_name} is empty, skipping")
                            continue
                        
                        # Ensure stereo
                        if len(audio.shape) == 1:
                            audio = np.stack([audio, audio])
                        elif audio.shape[0] == 1:
                            audio = np.vstack([audio, audio])
                        
                        # Transpose to (samples, channels) for sounddevice
                        if audio.shape[0] == 2:
                            audio = audio.T
                        
                        # Ensure contiguous memory layout
                        audio = np.ascontiguousarray(audio.astype(np.float32))
                        
                        loaded_stems[stem_name] = audio
                        max_length = max(max_length, len(audio))
                        
                    except Exception as e:
                        print(f"❌ Error loading {stem_name}: {e}")
                        # Continue with other stems
                        
                else:
                    print(f"⚠️ {stem_name} file not found at {stem_path}")
            
            if not loaded_stems:
                raise ValueError("No stems were successfully loaded")
            
            print(f"🔧 Synchronizing {len(loaded_stems)} stems to {max_length} samples")
            
            # Pad all stems to same length for perfect synchronization
            for stem_name in loaded_stems:
                current_length = len(loaded_stems[stem_name])
                if current_length < max_length:
                    padding = np.zeros((max_length - current_length, 2), dtype=np.float32)
                    loaded_stems[stem_name] = np.vstack([loaded_stems[stem_name], padding])
                    print(f"🔧 Padded {stem_name} from {current_length} to {max_length} samples")
            
            self.original_stems = loaded_stems
            self.processed_stems = loaded_stems.copy()
            
            self.current_position = 0
            
            print(f"✅ Successfully loaded {len(loaded_stems)} stems")
            return song_name
            
        except Exception as e:
            print(f"❌ CRITICAL ERROR in load_song_stems: {e}")
            import traceback
            traceback.print_exc()
            raise  # Re-raise so the GUI can handle it
    
    def apply_effects_to_stems(self, speed=1.0, pitch_shift=0):
        """Apply speed and pitch effects to all stems"""
        print(f"Applying effects: speed={speed}x, pitch={pitch_shift} semitones")
        
        for stem_name in self.original_stems:
            audio = self.original_stems[stem_name].copy()
            
            # Convert back to (channels, samples) for librosa
            if len(audio.shape) == 2 and audio.shape[1] == 2:
                audio = audio.T
            
            # Apply pitch shift
            if pitch_shift != 0:
                audio = librosa.effects.pitch_shift(audio, sr=self.sample_rate, n_steps=pitch_shift)
            
            # Apply time stretch
            if speed != 1.0:
                audio = librosa.effects.time_stretch(audio, rate=speed)
            
            # Convert back to (samples, channels)
            if len(audio.shape) == 2 and audio.shape[0] == 2:
                audio = audio.T
            
            self.processed_stems[stem_name] = audio.astype(np.float32)
        
        # Reset position when effects change
        self.current_position = 0
    
    def audio_callback(self, outdata, frames, time, status):
        """Optimized real-time audio callback"""
        # Remove all status printing - it causes lag
        
        # Clear output buffer first
        outdata.fill(0)
        
        if not self.is_playing or not self.processed_stems:
            return
        
        try:
            current_pos = self.current_position
            
            # Mix stems efficiently
            for stem_name, audio in self.processed_stems.items():
                volume = self.volumes.get(stem_name, 1.0)
                
                if volume > 0.001 and len(audio) > current_pos:
                    available = len(audio) - current_pos
                    to_copy = min(frames, available)
                    
                    if to_copy > 0:
                        chunk = audio[current_pos:current_pos + to_copy] * volume
                        outdata[:to_copy] += chunk
            
            # Apply master volume and soft limiting
            outdata *= self.master_volume
            np.clip(outdata, -0.95, 0.95, out=outdata)
            
            # Update position
            self.current_position += frames
            
            # Handle looping
            if self.processed_stems:
                max_len = max(len(audio) for audio in self.processed_stems.values())
                if self.current_position >= max_len:
                    self.current_position = 0
                        
        except Exception:
            # Don't print errors in audio callback - causes lag
            outdata.fill(0)
    
    def start_playback(self):
        """Start real-time audio playback"""
        if self.is_playing:
            return
        
        try:
            self.stream = sd.OutputStream(
                callback=self.audio_callback,
                samplerate=self.sample_rate,
                channels=2,
                blocksize=self.block_size,
                dtype='float32'
            )
            
            self.stream.start()
            self.is_playing = True
            print("🎵 Real-time playback started")
            
        except Exception as e:
            print(f"❌ Failed to start playback: {e}")
    
    def stop_playback(self):
        """Stop real-time audio playback"""
        if not self.is_playing:
            return
        
        self.is_playing = False
        
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        
        print("⏹️ Playback stopped")
    
    def set_volume(self, stem_name, volume):
        """Set volume for a specific stem in real-time"""
        if stem_name in self.volumes:
            self.volumes[stem_name] = max(0.0, min(2.0, volume))  # Allow up to 200%
            # No restart needed - change happens in real-time!
    
    def set_master_volume(self, volume):
        """Set master volume in real-time"""
        self.master_volume = max(0.0, min(2.0, volume))
    
    def get_position_seconds(self):
        """Get current playback position in seconds"""
        return self.current_position / self.sample_rate if self.sample_rate > 0 else 0
    
    def set_position_seconds(self, seconds):
        """Set playback position in seconds"""
        new_position = int(seconds * self.sample_rate)
        
        # Ensure position is within bounds
        if self.processed_stems:
            max_length = max(len(audio) for audio in self.processed_stems.values())
            new_position = max(0, min(new_position, max_length - 1))
        
        # Set position
        self.current_position = new_position
    
    def get_duration_seconds(self):
        """Get total duration in seconds"""
        if not self.processed_stems:
            return 0
        max_length = max(len(audio) for audio in self.processed_stems.values())
        return max_length / self.sample_rate
    
    def cleanup(self):
        """Clean up resources"""
        self.stop_playback()
        print("🧹 Audio engine cleaned up")