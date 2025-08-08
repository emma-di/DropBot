# python -m calibrate.calibrate_track

from calibrate.split_audio import split_song
from calibrate.analyze_audio_2 import analyze_song
import json
import os

def format_dj_summary(metadata):
    """Create a human-readable summary for DJs"""
    summary = []
    summary.append(f"🎵 {metadata['key']} | {metadata['bpm']} BPM | {metadata['duration']}s")
    
    # Mix-in points
    mix_ins = metadata['dj_cues']['mix_in_points']
    if mix_ins:
        best_mix_in = min(mix_ins, key=lambda x: x['time'])
        summary.append(f"🔄 Best mix-in: {best_mix_in['time']}s ({best_mix_in['reason']})")
    
    # Mix-out points
    mix_outs = metadata['dj_cues']['mix_out_points']
    if mix_outs:
        high_conf_outs = [m for m in mix_outs if m['confidence'] == 'high']
        if high_conf_outs:
            best_mix_out = min(high_conf_outs, key=lambda x: x['time'])
            summary.append(f"🔄 Best mix-out: {best_mix_out['time']}s ({best_mix_out['reason']})")
    
    # Breakdowns for creative mixing
    breakdowns = metadata['dj_cues']['breakdown_points']
    if breakdowns:
        summary.append(f"🎛️ {len(breakdowns)} breakdown sections found")
    
    # Section overview
    intro_sections = [s for s in metadata['sections'] if 'intro' in s['dj_label']]
    outro_sections = [s for s in metadata['sections'] if 'outro' in s['dj_label']]
    summary.append(f"📊 Structure: {len(intro_sections)} intro, {len(outro_sections)} outro sections")
    
    return "\n".join(summary)

def calibrate_track(file_path):
    # Step 1: Split if needed
    song_name = split_song(file_path)

    # Step 2: Analyze song (BPM, key, structure, DJ cues)
    metadata = analyze_song(file_path)

    # Step 3: Save metadata
    out_path = os.path.join("data", "metadata", f"{song_name}.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✅ Calibrated and saved metadata to {out_path}")
    
    # Step 4: Display DJ-friendly summary
    print("\n" + "="*50)
    print("DJ ANALYSIS SUMMARY")
    print("="*50)
    print(format_dj_summary(metadata))
    print("="*50)
    
    # Step 5: Show detailed section breakdown
    print("\nDETAILED SECTIONS:")
    for i, section in enumerate(metadata['sections']):
        priority_icon = "🔥" if section['mix_priority'] == 'high' else "⭐" if section['mix_priority'] == 'medium' else "💫"
        print(f"{i+1:2d}. {section['start']:6.1f}s - {section['dj_label']:15s} {priority_icon} ({section['duration']:.1f}s)")

if __name__ == "__main__":
    from tkinter import filedialog, Tk
    root = Tk()
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(initialdir=os.path.join("data", "mp3s"), title="Pick a song")
    root.destroy()
    if path:
        calibrate_track(path)