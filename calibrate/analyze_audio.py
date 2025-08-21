import librosa
import numpy as np
import msaf
from msaf import input_output, run, utils
from pathlib import Path
import tempfile
import shutil
import os
import soundfile as sf

def estimate_key(chroma):
    # Krumhansl-Schmuckler key profiles
    major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    
    keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    
    chroma_avg = chroma.mean(axis=1)
    # Normalize chroma
    chroma_avg = chroma_avg / chroma_avg.sum()
    
    best_correlation = -1
    best_key = 'C'
    best_mode = 'major'
    
    # Test all 24 keys (12 major + 12 minor)
    for shift in range(12):
        # Major key test
        shifted_major = np.roll(major_profile, shift)
        correlation = np.corrcoef(chroma_avg, shifted_major)[0, 1]
        if correlation > best_correlation:
            best_correlation = correlation
            best_key = keys[shift]
            best_mode = 'major'
        
        # Minor key test
        shifted_minor = np.roll(minor_profile, shift)
        correlation = np.corrcoef(chroma_avg, shifted_minor)[0, 1]
        if correlation > best_correlation:
            best_correlation = correlation
            best_key = keys[shift]
            best_mode = 'minor'
    
    return f"{best_key} {best_mode}"

def find_transition_points(y, sr, sections, duration, bpm):
    """Find good spots for DJ transitions"""
    
    # Calculate RMS energy
    hop_length = 512
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)
    
    # Calculate average energy (convert to Python float)
    avg_energy = float(np.mean(rms))
    
    transition_points = {
        "mix_in_points": [],
        "mix_out_points": [],
        "breakdown_points": []
    }
    
    # Find intro end (good mix-in point after intro builds up)
    intro_threshold = min(60, duration * 0.25)  # First 25% or 60 seconds max
    for i, section in enumerate(sections):
        if section['start'] > 10 and section['start'] <= intro_threshold:
            transition_points["mix_in_points"].append({
                "time": round(float(section['start']), 2),
                "confidence": "high",
                "reason": "end_of_intro"
            })
            break
    
    # Find breakdown sections (low energy moments)
    for i, section in enumerate(sections):
        if i < len(sections) - 1:
            start_time = section['start']
            end_time = sections[i+1]['start']
            
            # Get energy for this section
            start_idx = np.argmin(np.abs(times - start_time))
            end_idx = np.argmin(np.abs(times - end_time))
            
            if start_idx < len(rms) and end_idx < len(rms):
                section_energy = float(np.mean(rms[start_idx:end_idx]))
                
                # If section has notably low energy, mark as breakdown
                if section_energy < avg_energy * 0.7 and start_time > 30:
                    transition_points["breakdown_points"].append({
                        "time": round(float(start_time), 2),
                        "duration": round(float(end_time - start_time), 2),
                        "energy_ratio": round(section_energy / avg_energy, 3),
                        "confidence": "medium"
                    })
    
    # Find good mix-out points (usually in last 25% of song)
    mix_out_start = duration * 0.75
    for section in sections:
        if section['start'] > mix_out_start:
            # Check if this section repeats earlier (likely chorus/outro)
            is_repeated = any(s['label'] == section['label'] for s in sections if s['start'] < mix_out_start)
            
            confidence = "high" if is_repeated else "medium"
            transition_points["mix_out_points"].append({
                "time": round(float(section['start']), 2),
                "confidence": confidence,
                "reason": "repeated_section" if is_repeated else "outro_section"
            })
    
    return transition_points

def enhance_sections_for_dj(sections, duration, y, sr):
    """Add DJ-specific labels and information to sections using smart analysis"""
    
    # Calculate additional features for better classification
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    
    # Analyze label patterns
    label_info = analyze_label_patterns(sections)
    
    enhanced_sections = []
    
    for i, section in enumerate(sections):
        start_time = section['start']
        label = section['label']
        
        # Calculate section duration
        if i < len(sections) - 1:
            section_duration = sections[i+1]['start'] - start_time
        else:
            section_duration = duration - start_time
        
        # Calculate energy for this section
        start_idx = np.argmin(np.abs(times - start_time))
        end_idx = np.argmin(np.abs(times - (start_time + section_duration)))
        
        if start_idx < len(rms) and end_idx < len(rms) and end_idx > start_idx:
            section_energy = float(np.mean(rms[start_idx:end_idx]))
        else:
            section_energy = float(np.mean(rms))
        
        avg_energy = float(np.mean(rms))
        
        # Smart classification
        dj_label, confidence = classify_section_smart(
            section, i, sections, duration, section_energy, 
            avg_energy, label_info, section_duration
        )
        
        enhanced_section = section.copy()
        enhanced_section['dj_label'] = dj_label
        enhanced_section['confidence'] = round(confidence, 2)
        enhanced_section['duration'] = round(section_duration, 2)
        enhanced_section['energy_level'] = get_energy_level(section_energy, avg_energy)
        enhanced_section['mix_priority'] = determine_mix_priority(dj_label, confidence, section_energy, avg_energy)
        
        enhanced_sections.append(enhanced_section)
    
    return enhanced_sections

def analyze_label_patterns(sections):
    """Analyze how labels repeat to understand song structure"""
    label_counts = {}
    label_positions = {}
    
    for i, section in enumerate(sections):
        label = section['label']
        
        if label not in label_counts:
            label_counts[label] = 0
            label_positions[label] = []
        
        label_counts[label] += 1
        label_positions[label].append(i)
    
    # Find most common label (likely verse or chorus)
    most_common_label = max(label_counts, key=label_counts.get) if label_counts else None
    
    return {
        'counts': label_counts,
        'positions': label_positions,
        'most_common': most_common_label,
        'unique_labels': [label for label, count in label_counts.items() if count == 1]
    }

def classify_section_smart(section, index, all_sections, duration, section_energy, avg_energy, label_info, section_duration):
    """Smart classification using multiple musical features"""
    
    start_time = section['start']
    label = section['label']
    total_sections = len(all_sections)
    
    # Position analysis
    position_ratio = start_time / duration
    
    # Pattern analysis
    repetition_count = label_info['counts'].get(label, 1)
    is_most_common = (label == label_info['most_common'])
    is_unique = (label in label_info['unique_labels'])
    
    # Energy analysis
    energy_ratio = section_energy / avg_energy if avg_energy > 0 else 1.0
    
    confidence = 0.5  # Base confidence
    
    # INTRO (high confidence)
    if index == 0 or (position_ratio < 0.08 and start_time < 20):
        confidence = 0.9
        return 'intro', confidence
    
    # OUTRO (high confidence)  
    if index == total_sections - 1 or position_ratio > 0.9:
        confidence = 0.9
        return 'outro', confidence
    
    # CHORUS - most repeated section, usually high energy
    if is_most_common and repetition_count >= 3:
        if energy_ratio > 1.1:  # Higher energy
            confidence = 0.85
            return 'chorus', confidence
        else:
            confidence = 0.7
            return 'chorus', confidence
    
    # VERSE - repeated 2-3 times, medium energy, early-mid song
    if repetition_count >= 2 and repetition_count <= 3:
        if position_ratio < 0.6 and energy_ratio < 1.2:
            confidence = 0.8
            if any(pos <= 2 for pos in label_info['positions'][label]):
                return 'verse_1', confidence
            else:
                return 'verse_2', confidence
    
    # BRIDGE - unique section in middle of song, often lower energy
    if is_unique and 0.3 < position_ratio < 0.8:
        if energy_ratio < 0.9:  # Lower energy
            confidence = 0.75
            return 'bridge', confidence
        else:
            confidence = 0.6
            return 'bridge', confidence
    
    # BREAKDOWN - low energy, often before chorus
    if energy_ratio < 0.7 and section_duration < 20:
        confidence = 0.7
        return 'breakdown', confidence
    
    # BUILD-UP - increasing energy, short duration
    if energy_ratio > 1.3 and section_duration < 15:
        confidence = 0.65
        return 'buildup', confidence
    
    # PRE-CHORUS - before main sections, medium energy
    if position_ratio > 0.2 and repetition_count == 2:
        confidence = 0.6
        return 'pre_chorus', confidence
    
    # INSTRUMENTAL - middle sections that are unique
    if 0.4 < position_ratio < 0.7 and is_unique and section_duration > 15:
        confidence = 0.5
        return 'instrumental', confidence
    
    # DEFAULT - verse (most songs have verses)
    confidence = 0.4
    return 'verse', confidence

def get_energy_level(section_energy, avg_energy):
    """Classify energy level"""
    ratio = section_energy / avg_energy if avg_energy > 0 else 1.0
    
    if ratio > 1.2:
        return 'high'
    elif ratio > 0.8:
        return 'medium'
    else:
        return 'low'

def determine_mix_priority(dj_label, confidence, section_energy, avg_energy):
    """Determine mixing priority for DJs"""
    
    # High priority for mixing
    if dj_label in ['intro', 'outro', 'breakdown']:
        return 'high'
    
    # High priority if we're confident it's a chorus
    if dj_label == 'chorus' and confidence > 0.8:
        return 'high'
    
    # Medium priority for verses and bridges
    if dj_label in ['verse_1', 'verse_2', 'bridge', 'buildup']:
        return 'medium'
    
    # Low priority for uncertain classifications
    if confidence < 0.6:
        return 'low'
    
    return 'medium'

def analyze_song(file_path):
    y, sr = librosa.load(file_path, mono=True)
    bpm, _ = librosa.beat.beat_track(y=y, sr=sr)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    key = estimate_key(chroma)
    duration = librosa.get_duration(y=y, sr=sr)

    # Create a temporary file with a simple name to avoid path issues
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
        temp_path = tmp_file.name
        # Convert to a simple path without special characters
        temp_path = temp_path.replace('\\', '/')
    
    try:
        # Save audio to temporary file
        sf.write(temp_path, y, sr)
        
        # Use the temporary file for MSAF processing
        boundaries, labels = msaf.process(
            temp_path,
            boundaries_id="olda",
            labels_id="cnmf"  # Changed from scluster to cnmf for better stability
        )
        
        basic_sections = [
            {"start": round(float(start), 2), "label": float(label)}
            for start, label in zip(boundaries, labels)
        ]
        
        # Enhance sections with DJ information (now with smart analysis)
        enhanced_sections = enhance_sections_for_dj(basic_sections, duration, y, sr)
        
        # Find transition points
        transition_points = find_transition_points(y, sr, basic_sections, duration, bpm)
        
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except:
            pass

    return {
        "bpm": int(round(float(bpm))),
        "key": key,
        "duration": round(float(duration), 2),
        "sections": enhanced_sections,
        "dj_cues": transition_points,
        "analysis_version": "1.2"  # Track version for future compatibility
    }

# REVERTED TO VERSION 1.2 SINCE 1.3 WAS GETTING STUCK