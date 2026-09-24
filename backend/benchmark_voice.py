import io
import wave
import struct
import numpy as np
import scipy.signal as signal
from engines.aasist import aasist_engine

def generate_human_voice(duration=2.0, sr=16000, f0_base=140.0):
    """
    Simulates real human speech:
    - Dynamic pitch contour with prosody variation (+/- 25 Hz)
    - Biological cycle-to-cycle vocal cord jitter (0.8% - 1.6%)
    - Glottal pulse excitation filtered through 3 human vocal tract formants (F1, F2, F3)
    - Natural breathing envelope and realistic mic noise floor
    - Full vocal chest resonance (sub-220Hz bass present)
    """
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples)
    
    # 1. Human intonation: rising and falling pitch contour
    pitch_contour = f0_base + 22.0 * np.sin(2 * np.pi * 1.5 * t) + 8.0 * np.sin(2 * np.pi * 3.2 * t)
    
    # 2. Glottal pulses with natural micro-tremor
    glottal_pulses = np.zeros(n_samples, dtype=np.float32)
    phase = 0.0
    for i in range(n_samples):
        freq = pitch_contour[i]
        phase += freq / sr
        if phase >= 1.0:
            phase -= 1.0
            jitter_dev = np.random.uniform(-0.008, 0.008)
            pulse_val = 1.0 + jitter_dev
            glottal_pulses[i] = pulse_val
            
    # Formant filtering (Vocal tract transfer function)
    # F1: 650Hz, F2: 1700Hz, F3: 2600Hz
    b_f1, a_f1 = signal.iirpeak(650.0, 5.0, sr)
    b_f2, a_f2 = signal.iirpeak(1700.0, 7.0, sr)
    b_f3, a_f3 = signal.iirpeak(2600.0, 8.0, sr)
    
    vocal = signal.lfilter(b_f1, a_f1, glottal_pulses) * 1.0 + \
            signal.lfilter(b_f2, a_f2, glottal_pulses) * 0.6 + \
            signal.lfilter(b_f3, a_f3, glottal_pulses) * 0.3
            
    # Natural chest resonance (sub-220Hz low frequency)
    b_low, a_low = signal.butter(2, 220.0 / (sr / 2), btype='low')
    chest_res = signal.lfilter(b_low, a_low, glottal_pulses) * 0.7
    vocal += chest_res
    
    # Organic speech envelope (syllable pacing)
    env = 0.5 * (1.0 + np.sin(2 * np.pi * 2.2 * t)) ** 1.5
    mic_audio = vocal * env + np.random.normal(0, 0.002, n_samples)
    mic_audio = mic_audio / (np.max(np.abs(mic_audio)) + 1e-6)
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for s in mic_audio:
            sample = int(np.clip(s * 32767.0, -32768, 32767))
            w.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

def generate_speaker_replay_ai(duration=2.0, sr=16000):
    """
    Simulates AI voice played from a smartphone / external device into a microphone:
    - Flat pitch contour (robotic TTS tone)
    - Phone speaker high-pass cutoff below 300Hz (no vocal chest resonance)
    - Strong mid-range speaker resonance peaks (2.2kHz)
    - High-frequency vocoder aliasing
    """
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples)
    
    # Flat pitch (140 Hz rigid)
    phase = 2 * np.pi * 140.0 * t
    ai_raw = (
        1.0 * np.sin(phase) +
        0.7 * np.sin(2 * phase) +
        0.5 * np.sin(3 * phase) +
        0.4 * np.sin(4 * phase) +
        0.3 * np.sin(5 * phase) +
        0.25 * np.sin(6 * phase) +
        0.2 * np.sin(7 * phase)
    )
    
    # Add vocoder mirror aliasing at 7kHz+
    ai_raw += 0.22 * np.sin(2 * np.pi * 7200.0 * t)
    ai_raw += 0.18 * np.sin(2 * np.pi * 7800.0 * t)
    
    # Phone speaker acoustic transfer function:
    # High-pass filter at 320Hz (steep bass cutoff)
    b_hpf, a_hpf = signal.butter(4, 320.0 / (sr / 2), btype='high')
    speaker_audio = signal.lfilter(b_hpf, a_hpf, ai_raw)
    
    # Phone speaker cabinet resonance at 2400Hz
    b_res, a_res = signal.iirpeak(2400.0, 4.0, sr)
    speaker_audio += signal.lfilter(b_res, a_res, speaker_audio) * 0.8
    
    # Speaker clipping & distortion
    speaker_audio = np.tanh(speaker_audio * 1.6)
    speaker_audio = speaker_audio / (np.max(np.abs(speaker_audio)) + 1e-6)
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        for s in speaker_audio:
            sample = int(np.clip(s * 32767.0, -32768, 32767))
            w.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

if __name__ == "__main__":
    human_pcm = generate_human_voice()
    replay_pcm = generate_speaker_replay_ai()
    
    res_h = aasist_engine.analyze_live_chunk(human_pcm)
    res_r = aasist_engine.analyze_live_chunk(replay_pcm)
    
    print("--- 1. HUMAN VOICE TEST ---")
    print(f"Authenticity: {res_h['authenticity']}% | Status: {res_h['authStatus']}")
    print(f"Indicators: {res_h['syntheticIndicators']}")
    print(f"ML Confidence: {res_h.get('mlConfidence')}% | Jitter: {res_h.get('jitter')}% | Kurt: {res_h.get('kurtosis')}")
    
    print("\n--- 2. EXTERNAL SPEAKER / AI VOICE REPLAY TEST ---")
    print(f"Authenticity: {res_r['authenticity']}% | Status: {res_r['authStatus']}")
    print(f"Indicators: {res_r['syntheticIndicators']}")
    print(f"ML Confidence: {res_r.get('mlConfidence')}% | Jitter: {res_r.get('jitter')}% | Kurt: {res_r.get('kurtosis')}")
