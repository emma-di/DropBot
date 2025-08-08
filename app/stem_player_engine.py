from tkinter import Tk, Label, Scale, Button, filedialog, Frame, Entry, StringVar
from tkinter import HORIZONTAL
from app.stem_audio_helpers import StemAudioEngine

class RealTimeStemPlayer:
    def __init__(self):
        self.audio_engine = StemAudioEngine()
        self.is_playing = False
        self.song_name = ""
        self.current_sound = None
        
        # Control parameters
        self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.speed = 1.0
        self.pitch = 0  # semitones
        
        self.setup_gui()
    
    def load_song(self, file_path):
        """Load song using audio engine"""
        self.song_name = self.audio_engine.load_song_stems(file_path)
        # Reset effects
        self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
        self.update_title()
    
    # === EVENT HANDLERS ===
    
    def on_volume_change(self, stem_name, value):
        """Handle volume slider changes"""
        print(f"Volume change: {stem_name} = {value}%")
        
        old_volume = self.volumes[stem_name]
        self.volumes[stem_name] = float(value) / 100.0
        self.volume_entries[stem_name].set(str(int(float(value))))
        
        # Only restart if actually playing AND volume actually changed
        if self.is_playing and abs(old_volume - self.volumes[stem_name]) > 0.01:
            print("  -> Restarting playback with new volume")
            self.current_sound = self.audio_engine.play_audio(self.volumes)
        else:
            print("  -> Volume updated, not playing or no change")
    
    def on_volume_entry_change(self, stem_name):
        """Handle volume entry field changes"""
        try:
            value = float(self.volume_entries[stem_name].get())
            value = max(0, min(150, value))
            print(f"Volume entry change: {stem_name} = {value}%")
            
            old_volume = self.volumes[stem_name]
            self.volume_sliders[stem_name].set(int(value))
            self.volumes[stem_name] = value / 100.0
            
            # Only restart if actually playing AND volume actually changed
            if self.is_playing and abs(old_volume - self.volumes[stem_name]) > 0.01:
                print("  -> Restarting playback with new volume")
                self.current_sound = self.audio_engine.play_audio(self.volumes)
            else:
                print("  -> Volume updated, not playing or no change")
                
        except ValueError:
            current = self.volume_sliders[stem_name].get()
            self.volume_entries[stem_name].set(str(current))
            print("  -> Invalid input, reset to current value")
    
    def on_speed_change(self, value):
        """Handle speed slider changes"""
        new_speed = float(value) / 100.0
        print(f"Speed changed to: {new_speed}")
        
        if abs(new_speed - self.speed) > 0.01:
            self.speed = new_speed
            self.speed_entry.set(str(int(float(value))))
            
            # Apply effects and restart if playing
            self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
            if self.is_playing:
                self.current_sound = self.audio_engine.play_audio(self.volumes)
    
    def on_speed_entry_change(self):
        """Handle speed entry field changes"""
        try:
            value = float(self.speed_entry.get())
            value = max(50, min(200, value))
            print(f"Speed entry changed to: {value}")
            
            self.speed_slider.set(int(value))
            new_speed = value / 100.0
            
            if abs(new_speed - self.speed) > 0.01:
                self.speed = new_speed
                self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
                if self.is_playing:
                    self.current_sound = self.audio_engine.play_audio(self.volumes)
        except ValueError:
            current = self.speed_slider.get()
            self.speed_entry.set(str(current))
    
    def on_pitch_change(self, value):
        """Handle pitch slider changes"""
        new_pitch = int(value)
        print(f"Pitch changed to: {new_pitch}")
        
        if new_pitch != self.pitch:
            self.pitch = new_pitch
            self.pitch_entry.set(str(new_pitch))
            
            # Apply effects and restart if playing
            self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
            if self.is_playing:
                self.current_sound = self.audio_engine.play_audio(self.volumes)
    
    def on_pitch_entry_change(self):
        """Handle pitch entry field changes"""
        try:
            value = int(float(self.pitch_entry.get()))
            value = max(-12, min(12, value))
            print(f"Pitch entry changed to: {value}")
            
            self.pitch_slider.set(value)
            if value != self.pitch:
                self.pitch = value
                self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
                if self.is_playing:
                    self.current_sound = self.audio_engine.play_audio(self.volumes)
        except ValueError:
            current = self.pitch_slider.get()
            self.pitch_entry.set(str(current))
    
    def reset_to_original(self):
        """Reset all controls to original/default values"""
        print("Resetting all controls to original values")
        
        # Reset internal values
        self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.speed = 1.0
        self.pitch = 0
        
        # Reset GUI controls
        for stem_name in self.volumes.keys():
            self.volume_sliders[stem_name].set(100)
            self.volume_entries[stem_name].set("100")
        
        self.speed_slider.set(100)
        self.speed_entry.set("100")
        
        self.pitch_slider.set(0)
        self.pitch_entry.set("0")
        
        # Apply reset effects and restart if playing
        if self.song_name:  # Only if a song is loaded
            self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
            if self.is_playing:
                self.current_sound = self.audio_engine.play_audio(self.volumes)
        
        print("✅ Reset complete")
    
    # === PLAYBACK CONTROL ===
    
    def play_pause(self):
        """Toggle play/pause"""
        if self.is_playing:
            self.audio_engine.stop_playback()
            self.is_playing = False
            self.current_sound = None
            self.play_button.config(text="▶ Play")
        else:
            self.current_sound = self.audio_engine.play_audio(self.volumes)
            self.is_playing = True
            self.play_button.config(text="⏸ Pause")
    
    # === GUI SETUP ===
    
    def setup_gui(self):
        """Setup the GUI"""
        self.root = Tk()
        self.root.title("🎛️ Real-Time AI DJ Stem Player")
        self.root.geometry("600x650")
        
        # File selection
        Button(self.root, text="📁 Load Song", command=self.select_file, 
               font=("Arial", 12)).pack(pady=10)
        
        self.title_label = Label(self.root, text="No song loaded", 
                                font=("Arial", 12, "bold"))
        self.title_label.pack()
        
        # Play/Pause button
        self.play_button = Button(self.root, text="▶ Play", command=self.play_pause, 
                                 font=("Arial", 14), bg="#4CAF50", fg="white",
                                 width=15, height=2)
        self.play_button.pack(pady=10)
        
        # Reset button
        reset_button = Button(self.root, text="🔄 Reset to Original", 
                             command=self.reset_to_original,
                             font=("Arial", 11), bg="#FF9800", fg="white",
                             width=20, height=1)
        reset_button.pack(pady=5)
        
        self._setup_volume_controls()
        self._setup_speed_control()
        self._setup_pitch_control()
        
        # Instructions
        instructions = Label(self.root, 
                           text="💡 All changes will restart playback (limitation of pygame mixer)",
                           font=("Arial", 10), fg="gray")
        instructions.pack(pady=10)
    
    def _setup_volume_controls(self):
        """Setup volume control section"""
        vol_frame = Frame(self.root)
        vol_frame.pack(pady=10, fill='x')
        
        Label(vol_frame, text="🎚️ VOLUME CONTROLS", 
              font=("Arial", 12, "bold")).pack()
        
        self.volume_sliders = {}
        self.volume_entries = {}
        stem_names = ["vocals", "drums", "bass", "other"]
        
        for stem_name in stem_names:
            frame = Frame(vol_frame)
            frame.pack(fill='x', padx=20, pady=3)
            
            Label(frame, text=f"{stem_name.title()}:", 
                  width=8, anchor='w').pack(side='left')
            
            # Entry field
            entry_var = StringVar(value="100")
            entry = Entry(frame, textvariable=entry_var, width=6)
            entry.pack(side='right', padx=(5, 0))
            entry.bind('<Return>', lambda e, name=stem_name: self.on_volume_entry_change(name))
            entry.bind('<FocusOut>', lambda e, name=stem_name: self.on_volume_entry_change(name))
            
            Label(frame, text="%", width=2).pack(side='right')
            
            # Slider
            slider = Scale(frame, from_=0, to=150, orient=HORIZONTAL, 
                          command=lambda val, name=stem_name: self.on_volume_change(name, val))
            slider.set(100)
            slider.pack(side='right', fill='x', expand=True, padx=(0, 5))
            
            self.volume_sliders[stem_name] = slider
            self.volume_entries[stem_name] = entry_var
    
    def _setup_speed_control(self):
        """Setup speed control section"""
        speed_frame = Frame(self.root)
        speed_frame.pack(pady=10, fill='x')
        
        Label(speed_frame, text="🏃 SPEED", font=("Arial", 12, "bold")).pack()
        Label(speed_frame, text="50% = Half Speed | 100% = Normal | 200% = Double Speed",
              font=("Arial", 9)).pack()
        
        control_frame = Frame(speed_frame)
        control_frame.pack(fill='x', padx=20, pady=5)
        
        self.speed_slider = Scale(control_frame, from_=50, to=200, orient=HORIZONTAL, 
                                 command=lambda val: self.on_speed_change(val))
        self.speed_slider.set(100)
        self.speed_slider.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.speed_entry = StringVar(value="100")
        speed_entry = Entry(control_frame, textvariable=self.speed_entry, width=6)
        speed_entry.pack(side='right', padx=(5, 0))
        speed_entry.bind('<Return>', lambda e: self.on_speed_entry_change())
        speed_entry.bind('<FocusOut>', lambda e: self.on_speed_entry_change())
        
        Label(control_frame, text="%", width=2).pack(side='right')
    
    def _setup_pitch_control(self):
        """Setup pitch control section"""
        pitch_frame = Frame(self.root)
        pitch_frame.pack(pady=10, fill='x')
        
        Label(pitch_frame, text="🎵 PITCH", font=("Arial", 12, "bold")).pack()
        Label(pitch_frame, text="-12 = One Octave Down | 0 = Normal | +12 = One Octave Up",
              font=("Arial", 9)).pack()
        
        control_frame = Frame(pitch_frame)
        control_frame.pack(fill='x', padx=20, pady=5)
        
        self.pitch_slider = Scale(control_frame, from_=-12, to=12, orient=HORIZONTAL,
                                 command=lambda val: self.on_pitch_change(val))
        self.pitch_slider.set(0)
        self.pitch_slider.pack(side='left', fill='x', expand=True, padx=(0, 5))
        
        self.pitch_entry = StringVar(value="0")
        pitch_entry = Entry(control_frame, textvariable=self.pitch_entry, width=6)
        pitch_entry.pack(side='right', padx=(5, 0))
        pitch_entry.bind('<Return>', lambda e: self.on_pitch_entry_change())
        pitch_entry.bind('<FocusOut>', lambda e: self.on_pitch_entry_change())
        
        Label(control_frame, text="semitones", width=10).pack(side='right')
    
    # === UTILITY METHODS ===
    
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