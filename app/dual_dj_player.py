# python -m app.dual_dj_player

from tkinter import Tk, Label, Scale, Button, filedialog, Frame, Entry, StringVar, Canvas
from tkinter import HORIZONTAL, LEFT, RIGHT, BOTH, X, Y
from app.sounddevice_audio_engine import RealTimeStemAudioEngine
import threading
import time
import json
import os
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.patches as patches

class DualDJPlayer:
    def __init__(self):
        # Two independent audio engines
        self.deck_a = RealTimeStemAudioEngine()
        self.deck_b = RealTimeStemAudioEngine()
        
        # Deck states
        self.deck_a_playing = False
        self.deck_b_playing = False
        self.deck_a_song = ""
        self.deck_b_song = ""
        self.deck_a_metadata = None
        self.deck_b_metadata = None
        
        # Deck controls
        self.deck_a_volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        self.deck_b_volumes = {"vocals": 1.0, "drums": 1.0, "bass": 1.0, "other": 1.0}
        
        self.deck_a_muted = {"vocals": False, "drums": False, "bass": False, "other": False}
        self.deck_b_muted = {"vocals": False, "drums": False, "bass": False, "other": False}
        
        self.deck_a_speed = 1.0
        self.deck_b_speed = 1.0
        self.deck_a_pitch = 0
        self.deck_b_pitch = 0
        
        # Crossfader (0.0 = full A, 1.0 = full B)
        self.crossfader = 0.5
        
        # Position tracking
        self.position_update_thread = None
        self.should_update_positions = False
        
        self.setup_gui()
    
    def load_song_metadata(self, song_name):
        """Load song analysis metadata from JSON file, generate if missing"""
        try:
            metadata_path = f"data/metadata/{song_name}.json"
            
            if os.path.exists(metadata_path):
                print(f"Loading song analysis from: {metadata_path}")
                with open(metadata_path, 'r') as f:
                    return json.load(f)
            else:
                print(f"No analysis file found at: {metadata_path}")
                print(f"Attempting to generate analysis using calibrate...")
                
                if self.generate_song_metadata(song_name):
                    return self.load_song_metadata(song_name)
                else:
                    print(f"Failed to generate metadata for {song_name}")
                    return None
                    
        except Exception as e:
            print(f"Error loading song metadata: {e}")
            return None
    
    def generate_song_metadata(self, song_name):
        """Generate song metadata using calibrate/analyze_audio.py"""
        try:
            print(f"Generating metadata for: {song_name}")
            
            import sys
            sys.path.append('calibrate')
            from analyze_audio import analyze_song
            
            possible_audio_paths = [
                f"data/mp3s/{song_name}.mp3",
                f"data/mp3s/{song_name}.wav"
            ]
            
            audio_file_path = None
            for path in possible_audio_paths:
                if os.path.exists(path):
                    audio_file_path = path
                    break
            
            if not audio_file_path:
                print(f"Could not find audio file for {song_name} in data/mp3s/")
                return False
            
            print(f"Found audio file: {audio_file_path}")
            print(f"Running analysis... this may take a moment...")
            
            metadata = analyze_song(audio_file_path)
            
            if metadata:
                metadata_path = f"data/metadata/{song_name}.json"
                os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
                
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                print(f"Successfully generated and saved metadata to {metadata_path}")
                return True
            else:
                print(f"Analysis returned no metadata for {song_name}")
                return False
                
        except Exception as e:
            print(f"Error generating metadata: {e}")
            return False
    
    def load_song(self, deck, file_path):
        """Load song into specified deck (A or B)"""
        try:
            if deck == 'A':
                engine = self.deck_a
                if self.deck_a_playing:
                    self.toggle_play_deck('A')
            else:
                engine = self.deck_b
                if self.deck_b_playing:
                    self.toggle_play_deck('B')
            
            print(f"Loading song into Deck {deck}...")
            song_name = engine.load_song_stems(file_path)
            
            if song_name:
                # Load metadata
                metadata = self.load_song_metadata(song_name)
                
                # Apply initial effects
                if deck == 'A':
                    engine.apply_effects_to_stems(self.deck_a_speed, self.deck_a_pitch)
                    self.deck_a_song = song_name
                    self.deck_a_metadata = metadata
                else:
                    engine.apply_effects_to_stems(self.deck_b_speed, self.deck_b_pitch)
                    self.deck_b_song = song_name
                    self.deck_b_metadata = metadata
                
                # Update GUI
                self.update_deck_title(deck)
                self.update_deck_sections(deck)
                self.update_deck_position_slider(deck)
                
                print(f"Successfully loaded {song_name} into Deck {deck}")
            
        except Exception as e:
            print(f"Error loading song into Deck {deck}: {e}")
    
    def select_file_for_deck(self, deck):
        """File selection dialog for specific deck"""
        file_path = filedialog.askopenfilename(
            title=f"Select song for Deck {deck}",
            filetypes=[("Audio Files", "*.mp3 *.wav")],
            initialdir="data/mp3s"
        )
        
        if file_path:
            self.load_song(deck, file_path)
    
    def toggle_play_deck(self, deck):
        """Toggle play/pause for specific deck"""
        if deck == 'A':
            if self.deck_a_playing:
                self.deck_a.stop_playback()
                self.deck_a_playing = False
                self.deck_a_play_btn.config(text="▶ Play", bg="#4CAF50")
            else:
                self.deck_a.start_playback()
                self.deck_a_playing = True
                self.deck_a_play_btn.config(text="⏸ Pause", bg="#FF5722")
        else:
            if self.deck_b_playing:
                self.deck_b.stop_playback()
                self.deck_b_playing = False
                self.deck_b_play_btn.config(text="▶ Play", bg="#4CAF50")
            else:
                self.deck_b.start_playback()
                self.deck_b_playing = True
                self.deck_b_play_btn.config(text="⏸ Pause", bg="#FF5722")
        
        # Start/stop position updates
        if self.deck_a_playing or self.deck_b_playing:
            if not self.should_update_positions:
                self.start_position_updates()
        else:
            self.stop_position_updates()
    
    def on_crossfader_change(self, value):
        """Handle crossfader movement"""
        self.crossfader = float(value) / 100.0
        
        # Apply crossfader to master volumes
        deck_a_master = (1.0 - self.crossfader) * 2.0  # Boost when fully on this side
        deck_b_master = self.crossfader * 2.0
        
        # Cap at 1.0 to avoid distortion
        deck_a_master = min(deck_a_master, 1.0)
        deck_b_master = min(deck_b_master, 1.0)
        
        self.deck_a.set_master_volume(deck_a_master)
        self.deck_b.set_master_volume(deck_b_master)
        
        # Update crossfader label
        if self.crossfader < 0.1:
            self.crossfader_label.config(text="Deck A")
        elif self.crossfader > 0.9:
            self.crossfader_label.config(text="Deck B")
        else:
            self.crossfader_label.config(text="Mix")
    
    def on_volume_change(self, deck, stem_name, value):
        """Handle volume changes for specific deck/stem"""
        volume = float(value) / 100.0
        
        if deck == 'A':
            self.deck_a_volumes[stem_name] = volume
            self.deck_a.set_volume(stem_name, volume)
        else:
            self.deck_b_volumes[stem_name] = volume
            self.deck_b.set_volume(stem_name, volume)
    
    def toggle_mute(self, deck, stem_name):
        """Toggle mute for specific deck/stem"""
        if deck == 'A':
            muted = self.deck_a_muted[stem_name]
            if muted:
                # Unmute
                self.deck_a.set_volume(stem_name, self.deck_a_volumes[stem_name])
                self.deck_a_muted[stem_name] = False
                self.deck_a_mute_btns[stem_name].config(text="🔊", bg="#4CAF50")
            else:
                # Mute
                self.deck_a.set_volume(stem_name, 0.0)
                self.deck_a_muted[stem_name] = True
                self.deck_a_mute_btns[stem_name].config(text="🔇", bg="#F44336")
        else:
            muted = self.deck_b_muted[stem_name]
            if muted:
                # Unmute
                self.deck_b.set_volume(stem_name, self.deck_b_volumes[stem_name])
                self.deck_b_muted[stem_name] = False
                self.deck_b_mute_btns[stem_name].config(text="🔊", bg="#4CAF50")
            else:
                # Mute
                self.deck_b.set_volume(stem_name, 0.0)
                self.deck_b_muted[stem_name] = True
                self.deck_b_mute_btns[stem_name].config(text="🔇", bg="#F44336")
    
    def jump_to_section(self, deck, start_time):
        """Jump to specific section in deck"""
        if deck == 'A':
            self.deck_a.set_position_seconds(start_time)
        else:
            self.deck_b.set_position_seconds(start_time)
    
    def update_deck_title(self, deck):
        """Update deck title with song info"""
        if deck == 'A':
            if self.deck_a_song and self.deck_a_metadata:
                bpm = self.deck_a_metadata.get('bpm', 'Unknown')
                key = self.deck_a_metadata.get('key', 'Unknown')
                text = f"🎵 {self.deck_a_song} | {bpm} BPM | {key}"
            else:
                text = self.deck_a_song if self.deck_a_song else "No song loaded"
            self.deck_a_title.config(text=text)
        else:
            if self.deck_b_song and self.deck_b_metadata:
                bpm = self.deck_b_metadata.get('bpm', 'Unknown')
                key = self.deck_b_metadata.get('key', 'Unknown')
                text = f"🎵 {self.deck_b_song} | {bpm} BPM | {key}"
            else:
                text = self.deck_b_song if self.deck_b_song else "No song loaded"
            self.deck_b_title.config(text=text)
    
    def update_deck_sections(self, deck):
        """Update section visualization for deck"""
        if deck == 'A':
            canvas = self.deck_a_canvas
            metadata = self.deck_a_metadata
        else:
            canvas = self.deck_b_canvas
            metadata = self.deck_b_metadata
        
        # Clear canvas
        canvas.delete("all")
        
        if not metadata or 'sections' not in metadata:
            canvas.create_text(canvas.winfo_width()//2, 20, text="No sections", fill="gray")
            return
        
        sections = metadata['sections']
        duration = metadata.get('duration', 300)
        
        # Section colors
        section_colors = {
            'intro': '#FF6B6B', 'verse': '#45B7D1', 'chorus': '#4ECDC4',
            'outro': '#FFA726', 'bridge': '#96CEB4'
        }
        
        # Wait for canvas to update
        self.root.update_idletasks()
        canvas_width = canvas.winfo_width()
        if canvas_width < 50:
            canvas_width = 300
        
        # Draw sections
        for i, section in enumerate(sections):
            start_time = section['start']
            dj_label = section.get('dj_label', f"Section {i+1}")
            
            if i < len(sections) - 1:
                end_time = sections[i + 1]['start']
            else:
                end_time = duration
            
            x1 = int((start_time / duration) * canvas_width)
            x2 = int((end_time / duration) * canvas_width)
            
            if x2 - x1 < 1:
                continue
            
            color = section_colors.get(dj_label, '#CCCCCC')
            
            rect_id = canvas.create_rectangle(
                x1, 2, x2, 28, fill=color, outline='white', width=1,
                tags=f"section_{i}"
            )
            
            # Add click binding
            canvas.tag_bind(f"section_{i}", '<Button-1>',
                           lambda e, d=deck, t=start_time: self.jump_to_section(d, t))
    
    def update_deck_position_slider(self, deck):
        """Update position slider range for deck"""
        if deck == 'A':
            duration = self.deck_a.get_duration_seconds()
            self.deck_a_position_slider.config(to=int(duration))
            self.deck_a_position_slider.set(0)
        else:
            duration = self.deck_b.get_duration_seconds()
            self.deck_b_position_slider.config(to=int(duration))
            self.deck_b_position_slider.set(0)
    
    def start_position_updates(self):
        """Start position update thread"""
        self.should_update_positions = True
        self.position_update_thread = threading.Thread(target=self.update_positions_loop)
        self.position_update_thread.daemon = True
        self.position_update_thread.start()
    
    def stop_position_updates(self):
        """Stop position updates"""
        self.should_update_positions = False
    
    def update_positions_loop(self):
        """Update position sliders in background"""
        while self.should_update_positions:
            try:
                if self.deck_a_playing:
                    pos_a = self.deck_a.get_position_seconds()
                    self.root.after(0, self.update_deck_position_gui, 'A', pos_a)
                
                if self.deck_b_playing:
                    pos_b = self.deck_b.get_position_seconds()
                    self.root.after(0, self.update_deck_position_gui, 'B', pos_b)
                
                time.sleep(0.1)
            except Exception as e:
                print(f"Position update error: {e}")
                break
    
    def update_deck_position_gui(self, deck, position):
        """Update position GUI for specific deck"""
        if deck == 'A':
            self.deck_a_position_slider.set(int(position))
            self.deck_a_position_label.config(text=f"{int(position//60)}:{int(position%60):02d}")
        else:
            self.deck_b_position_slider.set(int(position))
            self.deck_b_position_label.config(text=f"{int(position//60)}:{int(position%60):02d}")
    
    def setup_gui(self):
        """Setup the dual DJ GUI"""
        self.root = Tk()
        self.root.title("🎛️ Dual DJ Stem Player")
        
        # Window setup
        window_width = 1200
        window_height = 800
        
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        x = (screen_width // 2) - (window_width // 2)
        y = (screen_height // 2) - (window_height // 2) - 50
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(1000, 600)
        
        # Main container
        main_frame = Frame(self.root)
        main_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)
        
        # Deck A (Left side)
        deck_a_frame = Frame(main_frame, relief="ridge", bd=2)
        deck_a_frame.pack(side=LEFT, fill=BOTH, expand=True, padx=(0, 5))
        
        # Deck B (Right side)
        deck_b_frame = Frame(main_frame, relief="ridge", bd=2)
        deck_b_frame.pack(side=RIGHT, fill=BOTH, expand=True, padx=(5, 0))
        
        # Center controls (Crossfader)
        center_frame = Frame(main_frame, width=200)
        center_frame.pack(side=LEFT, fill=Y, padx=10)
        center_frame.pack_propagate(False)
        
        # Setup individual decks
        self.setup_deck_gui(deck_a_frame, 'A')
        self.setup_deck_gui(deck_b_frame, 'B')
        
        # Setup center controls
        self.setup_center_controls(center_frame)
        
        # Cleanup handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_deck_gui(self, parent, deck):
        """Setup GUI for individual deck"""
        # Deck header
        Label(parent, text=f"DECK {deck}", font=("Arial", 16, "bold")).pack(pady=5)
        
        # Load button
        Button(parent, text=f"📁 Load Song", 
               command=lambda: self.select_file_for_deck(deck),
               font=("Arial", 10)).pack(pady=5)
        
        # Song title
        if deck == 'A':
            self.deck_a_title = Label(parent, text="No song loaded", font=("Arial", 10))
            self.deck_a_title.pack(pady=5)
        else:
            self.deck_b_title = Label(parent, text="No song loaded", font=("Arial", 10))
            self.deck_b_title.pack(pady=5)
        
        # Play button
        if deck == 'A':
            self.deck_a_play_btn = Button(parent, text="▶ Play", 
                                         command=lambda: self.toggle_play_deck('A'),
                                         font=("Arial", 12), bg="#4CAF50", fg="white")
            self.deck_a_play_btn.pack(pady=5)
        else:
            self.deck_b_play_btn = Button(parent, text="▶ Play", 
                                         command=lambda: self.toggle_play_deck('B'),
                                         font=("Arial", 12), bg="#4CAF50", fg="white")
            self.deck_b_play_btn.pack(pady=5)
        
        # Sections
        sections_frame = Frame(parent)
        sections_frame.pack(fill=X, pady=5, padx=5)
        Label(sections_frame, text="Sections:", font=("Arial", 9)).pack(anchor='w')
        
        if deck == 'A':
            self.deck_a_canvas = Canvas(sections_frame, height=30, bg='white')
            self.deck_a_canvas.pack(fill=X)
        else:
            self.deck_b_canvas = Canvas(sections_frame, height=30, bg='white')
            self.deck_b_canvas.pack(fill=X)
        
        # Position control
        pos_frame = Frame(parent)
        pos_frame.pack(fill=X, pady=5, padx=5)
        
        if deck == 'A':
            self.deck_a_position_slider = Scale(pos_frame, from_=0, to=300, orient=HORIZONTAL)
            self.deck_a_position_slider.pack(fill=X)
            self.deck_a_position_label = Label(pos_frame, text="0:00")
            self.deck_a_position_label.pack()
        else:
            self.deck_b_position_slider = Scale(pos_frame, from_=0, to=300, orient=HORIZONTAL)
            self.deck_b_position_slider.pack(fill=X)
            self.deck_b_position_label = Label(pos_frame, text="0:00")
            self.deck_b_position_label.pack()
        
        # Volume controls
        vol_frame = Frame(parent)
        vol_frame.pack(fill=BOTH, expand=True, pady=5, padx=5)
        Label(vol_frame, text="VOLUME CONTROLS", font=("Arial", 10, "bold")).pack()
        
        stem_names = ["vocals", "drums", "bass", "other"]
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]
        
        if deck == 'A':
            self.deck_a_mute_btns = {}
        else:
            self.deck_b_mute_btns = {}
        
        for i, stem_name in enumerate(stem_names):
            stem_frame = Frame(vol_frame)
            stem_frame.pack(fill=X, pady=2)
            
            Label(stem_frame, text=f"{stem_name.title()}:", width=8, anchor='w').pack(side=LEFT)
            
            slider = Scale(stem_frame, from_=0, to=150, orient=HORIZONTAL,
                          command=lambda val, d=deck, s=stem_name: self.on_volume_change(d, s, val),
                          bg=colors[i])
            slider.set(100)
            slider.pack(side=LEFT, fill=X, expand=True, padx=5)
            
            mute_btn = Button(stem_frame, text="🔊", width=3,
                             command=lambda d=deck, s=stem_name: self.toggle_mute(d, s),
                             bg="#4CAF50", fg="white")
            mute_btn.pack(side=RIGHT)
            
            if deck == 'A':
                self.deck_a_mute_btns[stem_name] = mute_btn
            else:
                self.deck_b_mute_btns[stem_name] = mute_btn
    
    def setup_center_controls(self, parent):
        """Setup center crossfader controls"""
        Label(parent, text="CROSSFADER", font=("Arial", 14, "bold")).pack(pady=10)
        
        # Deck labels
        Label(parent, text="A", font=("Arial", 12)).pack()
        
        # Crossfader
        self.crossfader_slider = Scale(parent, from_=0, to=100, orient="vertical",
                                      command=self.on_crossfader_change, length=200)
        self.crossfader_slider.set(50)
        self.crossfader_slider.pack(pady=10)
        
        Label(parent, text="B", font=("Arial", 12)).pack()
        
        # Crossfader position label
        self.crossfader_label = Label(parent, text="Mix", font=("Arial", 10))
        self.crossfader_label.pack(pady=5)
        
        # Master controls
        Label(parent, text="MASTER", font=("Arial", 12, "bold")).pack(pady=(20, 5))
        
        Button(parent, text="SYNC BPM", font=("Arial", 10), 
               command=self.sync_bpm).pack(pady=2)
        
        Button(parent, text="AUTO MIX", font=("Arial", 10),
               command=self.auto_mix).pack(pady=2)
    
    def sync_bpm(self):
        """Sync BPM between decks"""
        print("BPM sync not implemented yet")
    
    def auto_mix(self):
        """Auto crossfade between decks"""
        print("Auto mix not implemented yet")
    
    def on_closing(self):
        """Cleanup on exit"""
        self.stop_position_updates()
        self.deck_a.cleanup()
        self.deck_b.cleanup()
        self.root.destroy()
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

if __name__ == "__main__":
    app = DualDJPlayer()
    app.run()