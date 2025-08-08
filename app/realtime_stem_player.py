# python -m app.realtime_stem_player

from tkinter import Tk, Label, Scale, Button, filedialog, Frame, Entry, StringVar
from tkinter import HORIZONTAL
from app.sounddevice_audio_engine import RealTimeStemAudioEngine
import threading
import time

class RealTimeStemPlayer:
    def __init__(self):
        self.audio_engine = RealTimeStemAudioEngine()
        self.is_playing = False
        self.song_name = ""
        
        # Control parameters
        self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.muted_states = {"vocals": False, "drums": False, "bass": False, "other": False}
        self.pre_mute_volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.speed = 1.0
        self.pitch = 0
        
        # Position tracking
        self.position_update_thread = None
        self.should_update_position = False
        
        self.setup_gui()
    
    def load_song(self, file_path):
        """Load song using real-time audio engine"""
        try:
            # Stop current playback
            if self.is_playing:
                self.play_pause()
            
            # Reset all settings to defaults when loading new song
            print("🔄 Resetting to defaults for new song")
            self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
            self.muted_states = {"vocals": False, "drums": False, "bass": False, "other": False}
            self.pre_mute_volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
            self.speed = 1.0
            self.pitch = 0
            
            # Update GUI controls to defaults
            for stem_name in self.volumes.keys():
                self.volume_sliders[stem_name].set(100)
                self.volume_entries[stem_name].set("100")
                self.mute_buttons[stem_name].config(text="🔊", bg="#4CAF50")
            
            self.speed_slider.set(100)
            self.speed_entry.set("100")
            self.pitch_slider.set(0)
            self.pitch_entry.set("0")
            
            print("📁 Loading song stems...")
            
            # Load the new song
            self.song_name = self.audio_engine.load_song_stems(file_path)
            
            print("🎵 Applying initial effects...")
            # Only apply effects if loading was successful
            if self.song_name and self.audio_engine.original_stems:
                self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
            else:
                print("⚠️ Skipping effects - no stems loaded")
            
            # Reset position slider
            duration = self.audio_engine.get_duration_seconds()
            print(f"📏 Song duration: {duration:.1f} seconds")
            
            if hasattr(self, 'position_slider'):
                self.position_slider.config(to=int(duration))
                self.position_slider.set(0)
            
            self.update_title()
            print("✅ New song loaded with default settings")
            
        except Exception as e:
            print(f"❌ ERROR loading song: {e}")
            import traceback
            traceback.print_exc()
            
            # Show error to user
            from tkinter import messagebox
            messagebox.showerror("Error Loading Song", 
                               f"Failed to load song:\n{str(e)}\n\nCheck console for details.")
            
            # Reset to safe state
            self.song_name = ""
            self.update_title()
    
    # === REAL-TIME EVENT HANDLERS ===
    
    def on_volume_change(self, stem_name, value):
        """Handle volume slider changes - REAL-TIME, no restart!"""
        volume = float(value) / 100.0
        self.volumes[stem_name] = volume
        self.volume_entries[stem_name].set(str(int(float(value))))
        
        # Real-time volume change - no restart needed!
        self.audio_engine.set_volume(stem_name, volume)
    
    def on_volume_entry_change(self, stem_name):
        """Handle volume entry field changes - REAL-TIME"""
        try:
            value = float(self.volume_entries[stem_name].get())
            value = max(0, min(150, value))
            
            self.volume_sliders[stem_name].set(int(value))
            volume = value / 100.0
            self.volumes[stem_name] = volume
            
            # Real-time volume change
            self.audio_engine.set_volume(stem_name, volume)
            
        except ValueError:
            current = self.volume_sliders[stem_name].get()
            self.volume_entries[stem_name].set(str(current))
    
    def on_speed_change(self, value):
        """Handle speed slider changes - with debouncing to prevent spam"""
        new_speed = float(value) / 100.0
        
        if abs(new_speed - self.speed) > 0.01:
            self.speed = new_speed
            self.speed_entry.set(str(int(float(value))))
            
            # Cancel any pending speed change
            if hasattr(self, 'speed_change_timer'):
                self.root.after_cancel(self.speed_change_timer)
            
            # Debounce: only apply after user stops moving slider for 500ms
            self.speed_change_timer = self.root.after(500, lambda: self.apply_speed_change())
    
    def apply_speed_change(self):
        """Apply speed change in background thread"""
        print(f"🏃 Applying speed change: {self.speed}x")
        
        # Show processing indicator
        self.speed_slider.config(state='disabled')
        self.root.config(cursor='wait')
        
        # Run in background thread to prevent GUI freezing
        def process_speed():
            try:
                was_playing = self.is_playing
                if was_playing:
                    self.audio_engine.stop_playback()
                
                self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
                
                if was_playing:
                    self.audio_engine.start_playback()
                
                # Re-enable GUI on main thread
                self.root.after(0, self.speed_processing_done)
                
            except Exception as e:
                print(f"❌ Speed processing error: {e}")
                self.root.after(0, self.speed_processing_done)
        
        import threading
        threading.Thread(target=process_speed, daemon=True).start()
    
    def speed_processing_done(self):
        """Called when speed processing is complete"""
        self.speed_slider.config(state='normal')
        self.root.config(cursor='')
        print("✅ Speed change complete")
    
    def on_speed_entry_change(self):
        """Handle speed entry field changes"""
        try:
            value = float(self.speed_entry.get())
            value = max(50, min(200, value))
            
            self.speed_slider.set(int(value))
            # This will trigger on_speed_change which handles the debouncing
                    
        except ValueError:
            current = self.speed_slider.get()
            self.speed_entry.set(str(current))
    
    def on_pitch_change(self, value):
        """Handle pitch slider changes - with debouncing"""
        new_pitch = int(value)
        
        if new_pitch != self.pitch:
            self.pitch = new_pitch
            self.pitch_entry.set(str(new_pitch))
            
            # Cancel any pending pitch change
            if hasattr(self, 'pitch_change_timer'):
                self.root.after_cancel(self.pitch_change_timer)
            
            # Debounce: only apply after user stops moving slider for 500ms
            self.pitch_change_timer = self.root.after(500, lambda: self.apply_pitch_change())
    
    def apply_pitch_change(self):
        """Apply pitch change in background thread"""
        print(f"🎵 Applying pitch change: {self.pitch} semitones")
        
        # Show processing indicator
        self.pitch_slider.config(state='disabled')
        self.root.config(cursor='wait')
        
        # Run in background thread
        def process_pitch():
            try:
                was_playing = self.is_playing
                if was_playing:
                    self.audio_engine.stop_playback()
                
                self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
                
                if was_playing:
                    self.audio_engine.start_playback()
                
                # Re-enable GUI on main thread
                self.root.after(0, self.pitch_processing_done)
                
            except Exception as e:
                print(f"❌ Pitch processing error: {e}")
                self.root.after(0, self.pitch_processing_done)
        
        import threading
        threading.Thread(target=process_pitch, daemon=True).start()
    
    def pitch_processing_done(self):
        """Called when pitch processing is complete"""
        self.pitch_slider.config(state='normal')
        self.root.config(cursor='')
        print("✅ Pitch change complete")
    
    def on_pitch_entry_change(self):
        """Handle pitch entry field changes"""
        try:
            value = int(float(self.pitch_entry.get()))
            value = max(-12, min(12, value))
            
            self.pitch_slider.set(value)
            # This will trigger on_pitch_change which handles the debouncing
                    
        except ValueError:
            current = self.pitch_slider.get()
            self.pitch_entry.set(str(current))
    
    def on_position_change(self, value):
        """Handle position slider changes"""
        # Don't respond to programmatic updates during playback
        if hasattr(self, 'updating_position_from_playback') and self.updating_position_from_playback:
            return
        
        position_seconds = float(value)
        self.audio_engine.set_position_seconds(position_seconds)
        print(f"⏭️ Position changed to: {position_seconds:.1f}s")
    
    def on_position_click(self, event):
        """Handle clicking directly on the position slider to jump to position"""
        # Calculate the position based on where the user clicked
        slider_width = self.position_slider.winfo_width()
        click_x = event.x
        
        # Get the slider's range
        slider_min = self.position_slider['from']
        slider_max = self.position_slider['to']
        
        # Calculate the position based on click location
        if slider_width > 0:
            position_ratio = click_x / slider_width
            position_value = slider_min + (position_ratio * (slider_max - slider_min))
            position_value = max(slider_min, min(slider_max, position_value))  # Clamp to range
            
            # Set the slider and audio position immediately
            self.position_slider.set(position_value)
            self.audio_engine.set_position_seconds(position_value)
    
    def on_position_drag_start(self, event):
        """Called when user starts dragging position slider"""
        self.user_is_dragging_position = True
    
    def on_position_drag_end(self, event):
        """Called when user finishes dragging position slider"""
        if hasattr(self, 'user_is_dragging_position'):
            self.user_is_dragging_position = False
    
    def toggle_mute(self, stem_name):
        """Toggle mute for a specific stem"""
        if self.muted_states[stem_name]:
            # Unmute: restore previous volume
            self.volumes[stem_name] = self.pre_mute_volumes[stem_name]
            self.muted_states[stem_name] = False
            volume_percent = int(self.volumes[stem_name] * 100)
            self.volume_sliders[stem_name].set(volume_percent)
            self.volume_entries[stem_name].set(str(volume_percent))
            self.mute_buttons[stem_name].config(text="🔊", bg="#4CAF50")
        else:
            # Mute: save current volume and set to 0
            self.pre_mute_volumes[stem_name] = self.volumes[stem_name]
            self.volumes[stem_name] = 0.0
            self.muted_states[stem_name] = True
            self.volume_sliders[stem_name].set(0)
            self.volume_entries[stem_name].set("0")
            self.mute_buttons[stem_name].config(text="🔇", bg="#F44336")
        
        # Apply real-time volume change
        self.audio_engine.set_volume(stem_name, self.volumes[stem_name])
    
    def handle_keypress(self, event):
        """Handle keyboard shortcuts"""
        key = event.char.lower()
        stem_map = {"1": "vocals", "2": "drums", "3": "bass", "4": "other"}
        
        if key in stem_map:
            stem_name = stem_map[key]
            self.toggle_mute(stem_name)
            print(f"⌨️ Keyboard shortcut: {key} -> Toggle {stem_name}")
        elif key == " ":  # Spacebar
            self.play_pause()
            print("⌨️ Keyboard shortcut: Space -> Play/Pause")
            return "break"  # Prevent default space behavior
        elif key == "r":
            self.reset_to_original()
            print("⌨️ Keyboard shortcut: R -> Reset")
        elif key == "0":
            # Master mute/unmute all
            all_muted = all(self.muted_states.values())
            for stem_name in ["vocals", "drums", "bass", "other"]:
                if all_muted:
                    # Unmute all if all are muted
                    if self.muted_states[stem_name]:
                        self.toggle_mute(stem_name)
                else:
                    # Mute all if any are unmuted
                    if not self.muted_states[stem_name]:
                        self.toggle_mute(stem_name)
            print("⌨️ Keyboard shortcut: 0 -> Master mute/unmute")
    
    # === PLAYBACK CONTROL ===
    
    def play_pause(self):
        """Toggle play/pause"""
        if self.is_playing:
            self.audio_engine.stop_playback()
            self.is_playing = False
            self.play_button.config(text="▶ Play", bg="#4CAF50")
            self.stop_position_updates()
        else:
            self.audio_engine.start_playback()
            self.is_playing = True
            self.play_button.config(text="⏸ Pause", bg="#FF5722")
            self.start_position_updates()
    
    def reset_to_original(self):
        """Reset all controls to original values"""
        print("🔄 Resetting all controls to original values")
        
        # Reset volumes and mute states in real-time
        self.volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.muted_states = {"vocals": False, "drums": False, "bass": False, "other": False}
        self.pre_mute_volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        
        for stem_name in self.volumes.keys():
            self.volume_sliders[stem_name].set(100)
            self.volume_entries[stem_name].set("100")
            self.audio_engine.set_volume(stem_name, 1.0)
            self.mute_buttons[stem_name].config(text="🔊", bg="#4CAF50")
        
        # Reset speed/pitch (requires restart)
        old_speed, old_pitch = self.speed, self.pitch
        self.speed = 1.0
        self.pitch = 0
        
        self.speed_slider.set(100)
        self.speed_entry.set("100")
        self.pitch_slider.set(0)
        self.pitch_entry.set("0")
        
        # Apply effects if they changed
        if old_speed != 1.0 or old_pitch != 0:
            was_playing = self.is_playing
            if was_playing:
                self.audio_engine.stop_playback()
            
            self.audio_engine.apply_effects_to_stems(self.speed, self.pitch)
            
            if was_playing:
                self.audio_engine.start_playback()
        
        print("✅ Reset complete")
    
    # === POSITION TRACKING ===
    
    def start_position_updates(self):
        """Start updating position slider during playback"""
        self.should_update_position = True
        self.position_update_thread = threading.Thread(target=self.update_position_loop)
        self.position_update_thread.daemon = True
        self.position_update_thread.start()
    
    def stop_position_updates(self):
        """Stop updating position slider"""
        self.should_update_position = False
    
    def update_position_loop(self):
        """Update position slider in background thread"""
        while self.should_update_position and self.is_playing:
            try:
                # Don't update if user is dragging the slider
                if hasattr(self, 'user_is_dragging_position') and self.user_is_dragging_position:
                    time.sleep(0.1)
                    continue
                
                current_pos = self.audio_engine.get_position_seconds()
                
                # Update GUI in main thread
                self.root.after(0, self._update_position_gui, current_pos)
                
                time.sleep(0.1)  # Update 10 times per second
                
            except Exception as e:
                print(f"Position update error: {e}")
                break
    
    def _update_position_gui(self, current_pos):
        """Update position GUI elements (called from main thread)"""
        self.updating_position_from_playback = True
        self.position_slider.set(int(current_pos))
        self.position_label.config(text=f"{int(current_pos//60)}:{int(current_pos%60):02d}")
        self.updating_position_from_playback = False
    
    # === GUI SETUP ===
    
    def setup_gui(self):
        """Setup the GUI"""
        self.root = Tk()
        self.root.title("🎛️ Real-Time AI DJ Stem Player (Sounddevice)")
        
        # Better window sizing and positioning
        window_width = 750
        window_height = 900  # Increased from 850 to ensure everything fits
        
        # Center the window on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2) - 50  # Slightly above center
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        
        # Make window resizable but set minimum size
        self.root.minsize(650, 800)  # Also increased minimum size
        self.root.resizable(True, True)
        
        # Enable keyboard shortcuts
        self.root.bind('<Key>', self.handle_keypress)
        self.root.focus_set()  # Ensure window can receive key events
        
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
        Button(self.root, text="🔄 Reset to Original", command=self.reset_to_original,
               font=("Arial", 11), bg="#FF9800", fg="white",
               width=20, height=1).pack(pady=5)
        
        # Position control
        self._setup_position_control()
        
        # Volume, speed, pitch controls
        self._setup_volume_controls()
        self._setup_speed_control()
        self._setup_pitch_control()
        
        # Instructions
        instructions = Label(self.root,
                           text="🎚️ VOLUME CHANGES: Real-time (no restart!)\n🏃 SPEED/PITCH: Restart required\n⌨️ SHORTCUTS: 1-4=Mute, Space=Play/Pause, R=Reset, 0=Master Mute\n🎯 Powered by sounddevice for professional mixing",
                           font=("Arial", 10), fg="green", justify='center')
        instructions.pack(pady=10)
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _setup_position_control(self):
        """Setup position/seek control"""
        pos_frame = Frame(self.root)
        pos_frame.pack(pady=10, fill='x')
        
        Label(pos_frame, text="⏯️ POSITION", font=("Arial", 12, "bold")).pack()
        
        control_frame = Frame(pos_frame)
        control_frame.pack(fill='x', padx=20)
        
        self.position_slider = Scale(control_frame, from_=0, to=300, orient=HORIZONTAL,
                                   command=self.on_position_change, resolution=0.1)
        
        # Bind mouse events for both clicking and dragging
        self.position_slider.bind('<Button-1>', self.on_position_click)  # Click to jump
        self.position_slider.bind('<B1-Motion>', self.on_position_drag_start)  # Start drag
        self.position_slider.bind('<ButtonRelease-1>', self.on_position_drag_end)  # End drag
        
        self.position_slider.pack(fill='x')
        
        self.position_label = Label(control_frame, text="0:00", font=("Arial", 10))
        self.position_label.pack()
    
    def _setup_volume_controls(self):
        """Setup volume control section"""
        vol_frame = Frame(self.root)
        vol_frame.pack(pady=10, fill='x')
        
        Label(vol_frame, text="🎚️ REAL-TIME VOLUME CONTROLS", 
              font=("Arial", 12, "bold"), fg="green").pack()
        
        self.volume_sliders = {}
        self.volume_entries = {}
        self.mute_buttons = {}
        stem_names = ["vocals", "drums", "bass", "other"]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
        key_numbers = ["1", "2", "3", "4"]
        
        for i, stem_name in enumerate(stem_names):
            frame = Frame(vol_frame)
            frame.pack(fill='x', padx=20, pady=3)
            
            # Stem name with keyboard shortcut
            Label(frame, text=f"{stem_name.title()} ({key_numbers[i]}):", width=12, anchor='w',
                  fg=colors[i], font=("Arial", 10, "bold")).pack(side='left')
            
            # Mute button
            mute_btn = Button(frame, text="🔊", width=3, height=1,
                             command=lambda name=stem_name: self.toggle_mute(name),
                             bg="#4CAF50", fg="white", font=("Arial", 12))
            mute_btn.pack(side='right', padx=(5, 0))
            
            # Entry field
            entry_var = StringVar(value="100")
            entry = Entry(frame, textvariable=entry_var, width=6)
            entry.pack(side='right', padx=(5, 0))
            entry.bind('<Return>', lambda e, name=stem_name: self.on_volume_entry_change(name))
            entry.bind('<FocusOut>', lambda e, name=stem_name: self.on_volume_entry_change(name))
            
            Label(frame, text="%", width=2).pack(side='right')
            
            # Volume slider
            slider = Scale(frame, from_=0, to=150, orient=HORIZONTAL,
                          command=lambda val, name=stem_name: self.on_volume_change(name, val),
                          bg=colors[i], activebackground=colors[i])
            slider.set(100)
            slider.pack(side='right', fill='x', expand=True, padx=(0, 5))
            
            self.volume_sliders[stem_name] = slider
            self.volume_entries[stem_name] = entry_var
            self.mute_buttons[stem_name] = mute_btn
    
    def _setup_speed_control(self):
        """Setup speed control section"""
        speed_frame = Frame(self.root)
        speed_frame.pack(pady=10, fill='x')
        
        Label(speed_frame, text="🏃 SPEED (restart required)", 
              font=("Arial", 12, "bold")).pack()
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
        
        Label(pitch_frame, text="🎵 PITCH (restart required)", 
              font=("Arial", 12, "bold")).pack()
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
    
    def on_closing(self):
        """Clean up when closing the application"""
        self.stop_position_updates()
        self.audio_engine.cleanup()
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = RealTimeStemPlayer()
    app.run()