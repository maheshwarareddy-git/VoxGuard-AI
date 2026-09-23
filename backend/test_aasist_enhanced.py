import numpy as np
import scipy.signal as signal
from scipy.stats import kurtosis

def analyze_audio_authenticity(samples: np.ndarray, sr: int = 16000) -> dict:
    if len(samples) < 320:
        return {
            "authenticity": 90.0,
            "authStatus": "Short Audio Sample (Insufficient Frames)",
            "isSynthetic": False,
            "indicators": []
        }

    # Normalize and remove DC offset
    samples = samples - np.mean(samples)
    max_amp = np.max(np.abs(samples))
    if max_amp > 1e-6:
        samples = samples / max_amp

    # 1. Glottal Closure Instants (GCI) & Excitation Kurtosis
    # Human vocal cord snapping produces high kurtosis in the derivative signal
    diff_signal = np.diff(samples)
    diff_kurt = float(kurtosis(diff_signal))

    # 2. Pitch Jitter & Biological Micro-Tremor
    frame_len = int(sr * 0.04) # 40ms frame
    hop_len = int(sr * 0.015)  # 15ms hop
    num_frames = (len(samples) - frame_len) // hop_len
    
    pitch_periods = []
    min_lag = max(2, int(sr / 450)) # 450 Hz max
    max_lag = min(frame_len - 1, int(sr / 70))  # 70 Hz min
    
    for i in range(min(num_frames, 60)):
        frame = samples[i * hop_len : i * hop_len + frame_len]
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[len(corr)//2 :]
        
        if len(corr) > max_lag:
            window = corr[min_lag:max_lag]
            if len(window) > 0:
                peak_idx = np.argmax(window) + min_lag
                if corr[peak_idx] > 0.25 * (corr[0] + 1e-12):
                    pitch_periods.append(peak_idx)

    if len(pitch_periods) > 4:
        periods = np.array(pitch_periods, dtype=np.float32)
        diffs = np.abs(np.diff(periods))
        mean_p = np.mean(periods)
        jitter = float((np.mean(diffs) / (mean_p + 1e-6)) * 100.0)
    else:
        jitter = 0.8  # Unvoiced / fallback estimate

    # 3. Spectral Analysis (FFT)
    chunk_len = min(len(samples), 32768)
    chunk = samples[:chunk_len]
    fft_mags = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)
    psd = (fft_mags ** 2) + 1e-12

    # 3a. Spectral Flatness (Wiener Entropy)
    log_psd = np.log(psd)
    spectral_flatness = float(np.exp(np.mean(log_psd)) / (np.mean(psd) + 1e-12))

    # 3b. Spectral Bands (Low: <3kHz, Mid: 3-7kHz, High: >7kHz)
    low_band = psd[freqs < 3000]
    mid_band = psd[(freqs >= 3000) & (freqs < 7000)]
    high_band = psd[freqs >= 7000] if np.any(freqs >= 7000) else np.array([1e-12])

    p_low = np.mean(low_band) if len(low_band) > 0 else 1e-6
    p_mid = np.mean(mid_band) if len(mid_band) > 0 else 1e-6
    p_high = np.mean(high_band) if len(high_band) > 0 else 1e-6

    # 4. Silence & Noise Floor Analysis (TTS pure digital zero pauses)
    frame_energies = [np.mean(samples[i * frame_len : (i+1) * frame_len] ** 2) for i in range(len(samples)//frame_len)]
    min_energy = min(frame_energies) if frame_energies else 1e-4
    is_digital_silence = (min_energy < 1e-7 and len(frame_energies) > 4)

    # 5. Anti-Spoofing Multi-Feature Evidence Fusion
    synthetic_indicators = []
    spoof_risk = 0.0

    # Test 1: Excitation Dispersion (Lack of sharp glottal closure)
    if diff_kurt < 4.0:
        spoof_risk += 35.0
        synthetic_indicators.append(f"Diffuse Neural Vocoder Excitation (Kurtosis: {diff_kurt:.1f} < 4.0)")
    elif diff_kurt < 7.0:
        spoof_risk += 15.0
        synthetic_indicators.append(f"Sub-Harmonic Phase Dispersion (Kurtosis: {diff_kurt:.1f})")

    # Test 2: Pitch Invariance / Jitter
    if jitter < 0.20:
        spoof_risk += 30.0
        synthetic_indicators.append(f"Unnatural Pitch Invariance (Jitter: {jitter:.2f}% — Robotic Regularity)")
    elif jitter > 2.8:
        spoof_risk += 25.0
        synthetic_indicators.append(f"Vocoder Phase Discontinuity / Pitch Glitch (Jitter: {jitter:.2f}%)")

    # Test 3: High-Frequency Mel Cutoff or Aliased Conv Artifacts
    if sr >= 16000 and p_high < 0.005 * p_mid and p_mid > 1e-4:
        spoof_risk += 25.0
        synthetic_indicators.append("Mel-Filterbank High-Frequency Brickwall Cutoff (<7.5kHz)")
    elif p_high > 1.2 * p_mid and p_mid > 0.01:
        spoof_risk += 30.0
        synthetic_indicators.append("Vocoder Transposed-Convolution Checkerboard Aliasing")

    # Test 4: Pure Digital Silence
    if is_digital_silence:
        spoof_risk += 20.0
        synthetic_indicators.append("Synthetic Zero-Noise Floor (Pure Digital Silence in Pauses)")

    # Test 5: Spectral Flatness
    if spectral_flatness > 0.035:
        spoof_risk += 20.0
        synthetic_indicators.append("Excessive Spectral Flatness (Loss of Vocal Tract Formants)")

    authenticity = float(np.clip(100.0 - spoof_risk, 8.0, 99.5))
    is_synthetic = authenticity < 65.0

    if is_synthetic:
        auth_status = f"SYNTHETIC SPEECH DETECTED ({authenticity:.1f}%): " + "; ".join(synthetic_indicators[:2])
    elif authenticity < 80.0:
        auth_status = f"Suspect Audio Quality / Artifacts ({authenticity:.1f}%)"
    else:
        auth_status = f"Bona Fide Human Voice ({authenticity:.1f}%)"

    return {
        "authenticity": round(authenticity, 1),
        "authStatus": auth_status,
        "isSynthetic": is_synthetic,
        "kurtosis": round(diff_kurt, 2),
        "jitter": round(jitter, 3),
        "spectralFlatness": round(spectral_flatness, 4),
        "syntheticIndicators": synthetic_indicators
    }

if __name__ == "__main__":
    sr = 16000
    duration = 2.5
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples)

    # 1. Real Human Voice Simulation
    # Glottal impulses at ~135 Hz with 0.8% natural jitter
    pitch_period = int(sr / 135)
    t_impulse = np.zeros(n_samples)
    for p in range(0, n_samples, pitch_period):
        if p + 1 < n_samples:
            jitter_offset = np.random.randint(-2, 3)
            idx = max(0, min(n_samples - 1, p + jitter_offset))
            t_impulse[idx] = 1.0
    b, a = signal.butter(4, [250/(sr/2), 3200/(sr/2)], btype='band')
    human_vocal = signal.lfilter(b, a, t_impulse)
    # Natural breathing pause and room ambiance
    env = 0.5 * (1 + np.sin(2 * np.pi * 1.0 * t))
    human_mic = human_vocal * env + np.random.normal(0, 0.003, n_samples)
    res_human = analyze_audio_authenticity(human_mic, sr)
    print("HUMAN AUDIO RESULT:", res_human)

    # 2. AI Generated Voice (ElevenLabs / Neural Vocoder Simulation)
    # Neural vocoder phase dispersion (low kurtosis) + perfectly smooth pitch + digital silence
    ai_phase = 2 * np.pi * 135 * t
    ai_speech = np.sin(ai_phase) + 0.7 * np.sin(2 * ai_phase) + 0.4 * np.sin(3 * ai_phase)
    # Gated digital zero pause (no room ambiance)
    ai_env = np.where(np.sin(2 * np.pi * 1.0 * t) > 0, 1.0, 0.0)
    ai_mic = ai_speech * ai_env
    res_ai = analyze_audio_authenticity(ai_mic, sr)
    print("AI AUDIO RESULT:", res_ai)
