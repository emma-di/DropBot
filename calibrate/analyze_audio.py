# Version used as of 2025-08-27

import librosa
import numpy as np
import soundfile as sf
import tempfile
import os

def estimate_key(chroma):
    """Estimate musical key using Krumhansl-Schmuckler profiles"""
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    chroma_avg = chroma.mean(axis=1)
    if chroma_avg.sum() > 0:
        chroma_avg = chroma_avg / chroma_avg.sum()
    
    best_correlation = -1
    best_key = 'C'
    best_mode = 'major'
    
    for shift in range(12):
        # Major key test
        shifted_major = np.roll(major_profile, shift)
        try:
            correlation = np.corrcoef(chroma_avg, shifted_major)[0, 1]
            if not np.isnan(correlation) and correlation > best_correlation:
                best_correlation = correlation
                best_key = keys[shift]
                best_mode = 'major'
        except:
            pass
        
        # Minor key test
        shifted_minor = np.roll(minor_profile, shift)
        try:
            correlation = np.corrcoef(chroma_avg, shifted_minor)[0, 1]
            if not np.isnan(correlation) and correlation > best_correlation:
                best_correlation = correlation
                best_key = keys[shift]
                best_mode = 'minor'
        except:
            pass
    
    return f"{best_key} {best_mode}"

def safe_array_operation(arr1, arr2, operation='add'):
    """Safely perform operations on arrays of different lengths"""
    min_len = min(len(arr1), len(arr2))
    arr1_safe = arr1[:min_len]
    arr2_safe = arr2[:min_len]
    
    if operation == 'add':
        return arr1_safe + arr2_safe
    elif operation == 'multiply':
        return arr1_safe * arr2_safe
    else:
        return arr1_safe

def find_structural_boundaries_simple(y, sr, duration):
    """Simple, reliable boundary detection"""
    print("🎯 Finding structural boundaries...")
    
    try:
        # Use a reliable hop length
        hop_length = 512
        
        # Calculate RMS energy with error handling
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        
        print(f"🔍 RMS frames: {len(rms)}, time frames: {len(times)}")
        
        # Ensure arrays are same length
        min_len = min(len(rms), len(times))
        rms = rms[:min_len]
        times = times[:min_len]
        
        # Simple energy-based segmentation
        # Smooth the RMS to reduce noise
        window_size = max(1, int(sr / hop_length))  # ~1 second window
        if len(rms) >= window_size:
            # Use simple moving average instead of convolve to avoid size issues
            rms_smooth = []
            for i in range(len(rms)):
                start_idx = max(0, i - window_size//2)
                end_idx = min(len(rms), i + window_size//2 + 1)
                rms_smooth.append(np.mean(rms[start_idx:end_idx]))
            rms_smooth = np.array(rms_smooth)
        else:
            rms_smooth = rms
        
        # Find significant energy changes
        if len(rms_smooth) > 1:
            energy_diff = np.diff(rms_smooth)
            energy_threshold = np.std(energy_diff) * 1.2
            
            # Find boundaries where energy changes significantly
            boundaries = [0.0]  # Always start at beginning
            
            # Look for significant drops or increases in energy
            for i, diff in enumerate(energy_diff):
                time_point = times[i + 1] if i + 1 < len(times) else times[i]
                
                # Skip if too close to start/end
                if time_point < 10 or time_point > duration - 15:
                    continue
                
                # Skip if too close to existing boundary
                if boundaries and min(abs(time_point - b) for b in boundaries) < 20:
                    continue
                
                # Add boundary if energy change is significant
                if abs(diff) > energy_threshold:
                    boundaries.append(float(time_point))
            
            # Always end at the end
            boundaries.append(float(duration))
            
            # Sort and remove duplicates
            boundaries = sorted(list(set(boundaries)))
            
        else:
            # Fallback: just create simple time-based sections
            print("⚠️ Using fallback time-based segmentation")
            section_length = duration / 5  # 5 equal sections
            boundaries = [0.0]
            for i in range(1, 5):
                boundaries.append(float(i * section_length))
            boundaries.append(float(duration))
        
        print(f"✅ Found {len(boundaries)-1} sections: {[round(b, 1) for b in boundaries]}")
        return boundaries
        
    except Exception as e:
        print(f"⚠️ Error in boundary detection: {e}")
        # Ultimate fallback: create 5 equal sections
        section_length = duration / 5
        boundaries = [float(i * section_length) for i in range(6)]
        print(f"✅ Using fallback: 5 equal sections")
        return boundaries

def create_dj_sections(boundaries, y, sr, duration, bpm):
    """Create DJ sections with robust error handling"""
    print("🎵 Creating DJ sections...")
    
    sections = []
    
    try:
        # Calculate RMS for energy analysis
        hop_length = 512
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
        times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
        
        # Ensure consistent lengths
        min_len = min(len(rms), len(times))
        rms = rms[:min_len]
        times = times[:min_len]
        
        avg_energy = np.mean(rms)
        
    except Exception as e:
        print(f"⚠️ Error calculating energy features: {e}")
        avg_energy = 1.0
        rms = np.ones(100)  # Dummy data
        times = np.linspace(0, duration, 100)
    
    # Create sections from boundaries
    for i in range(len(boundaries) - 1):
        start_time = boundaries[i]
        end_time = boundaries[i + 1]
        section_duration = end_time - start_time
        
        # Calculate section energy safely
        try:
            start_idx = np.argmin(np.abs(times - start_time))
            end_idx = np.argmin(np.abs(times - end_time))
            
            if start_idx < len(rms) and end_idx <= len(rms) and end_idx > start_idx:
                section_energy = np.mean(rms[start_idx:end_idx])
            else:
                section_energy = avg_energy
        except:
            section_energy = avg_energy
        
        # Classify section
        dj_label, confidence = classify_dj_section_simple(
            i, len(boundaries) - 1, start_time, section_duration, 
            duration, section_energy, avg_energy
        )
        
        section = {
            "start": round(start_time, 2),
            "end": round(end_time, 2), 
            "duration": round(section_duration, 2),
            "dj_label": dj_label,
            "confidence": round(confidence, 2),
            "energy_level": get_energy_level_safe(section_energy, avg_energy),
            "mix_priority": get_mix_priority_safe(dj_label, confidence)
        }
        
        sections.append(section)
        print(f"📍 {i+1}. {start_time:5.1f}s - {dj_label:12s} ({section_duration:4.1f}s)")
    
    return sections

def classify_dj_section_simple(section_index, total_sections, start_time, duration_sec, total_duration, section_energy, avg_energy):
    """Simple, reliable DJ section classification"""
    
    position_ratio = start_time / total_duration if total_duration > 0 else 0
    energy_ratio = section_energy / avg_energy if avg_energy > 0 else 1.0
    
    # INTRO: Always first section
    if section_index == 0:
        return 'intro', 0.9
    
    # OUTRO: Always last section
    if section_index == total_sections - 1:
        return 'outro', 0.9
    
    # BREAKDOWN: Low energy sections
    if energy_ratio < 0.6:
        return 'breakdown', 0.8
    
    # CHORUS: High energy sections in middle/later part
    if energy_ratio > 1.2 and position_ratio > 0.25:
        return 'chorus', 0.8
    
    # BRIDGE: Middle sections
    if 0.4 < position_ratio < 0.8 and total_sections > 4:
        return 'bridge', 0.7
    
    # VERSE: Everything else in early-mid song
    if position_ratio < 0.6:
        return 'verse_1', 0.7
    else:
        return 'verse_2', 0.6

def get_energy_level_safe(section_energy, avg_energy):
    """Safe energy level calculation"""
    try:
        ratio = section_energy / avg_energy if avg_energy > 0 else 1.0
        
        if ratio > 1.3:
            return 'high'
        elif ratio > 0.8:
            return 'medium'
        else:
            return 'low'
    except:
        return 'medium'

def get_mix_priority_safe(dj_label, confidence):
    """Safe mix priority calculation"""
    try:
        high_priority = ['intro', 'outro', 'breakdown']
        medium_priority = ['chorus', 'bridge']
        
        if dj_label in high_priority:
            return 'high'
        elif dj_label in medium_priority:
            return 'medium' 
        else:
            return 'low'
    except:
        return 'medium'

def find_dj_cue_points_safe(sections, duration, bpm):
    """Safe DJ cue point detection"""
    cue_points = {
        "mix_in_points": [],
        "mix_out_points": [],
        "breakdown_points": []
    }
    
    try:
        for section in sections:
            # Mix-in points
            if section['dj_label'] == 'intro':
                cue_points["mix_in_points"].append({
                    "time": section['end'],
                    "confidence": "high",
                    "reason": "end_of_intro"
                })
            
            # Breakdown points
            if section['dj_label'] == 'breakdown':
                cue_points["breakdown_points"].append({
                    "time": section['start'],
                    "duration": section['duration'],
                    "confidence": "high"
                })
            
            # Mix-out points
            if section['dj_label'] == 'outro' or section['start'] > duration * 0.75:
                cue_points["mix_out_points"].append({
                    "time": section['start'],
                    "confidence": "high" if section['dj_label'] == 'outro' else "medium",
                    "reason": section['dj_label']
                })
                
    except Exception as e:
        print(f"⚠️ Error finding cue points: {e}")
    
    return cue_points

def analyze_song(file_path):
    """Main analysis function with comprehensive error handling"""
    print(f"🎧 Analyzing: {os.path.basename(file_path)}")
    
    try:
        # Load audio with error handling
        try:
            y, sr = librosa.load(file_path, mono=True)
            duration = librosa.get_duration(y=y, sr=sr)
            print(f"📊 Loaded: {duration:.1f}s at {sr}Hz")
        except Exception as e:
            print(f"❌ Error loading audio: {e}")
            return None
        
        # Extract basic features safely
        try:
            bpm, _ = librosa.beat.beat_track(y=y, sr=sr)
            bpm = max(60, min(200, int(round(float(bpm)))))  # Clamp to reasonable range
        except Exception as e:
            print(f"⚠️ BPM detection failed: {e}, using 120")
            bpm = 120
        
        try:
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            key = estimate_key(chroma)
        except Exception as e:
            print(f"⚠️ Key detection failed: {e}, using C major")
            key = "C major"
        
        print(f"🎵 Features: {bpm} BPM, {key}")
        
        # Find boundaries
        boundaries = find_structural_boundaries_simple(y, sr, duration)
        
        # Create sections
        sections = create_dj_sections(boundaries, y, sr, duration, bpm)
        
        # Find cue points
        dj_cues = find_dj_cue_points_safe(sections, duration, bpm)
        
        result = {
            "bpm": bpm,
            "key": key,
            "duration": round(float(duration), 2),
            "sections": sections,
            "dj_cues": dj_cues,
            "analysis_version": "2.1_robust"
        }
        
        print(f"✅ Analysis complete: {len(sections)} sections")
        return result
        
    except Exception as e:
        print(f"❌ Analysis failed completely: {e}")
        import traceback
        traceback.print_exc()
        return None