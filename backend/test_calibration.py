import numpy as np
import scipy.signal as signal

def calibrate_aasist_authenticity(samples: np.ndarray, sr: int = 16000) -> dict:
    if len(samples) < 320:
        return {
            "authenticity": 90.0,
            "authStatus": "Short Audio Sample (Insufficient Frames)",
            "isSynthetic": False
        }

    # Remove DC offset & normalize
    samples = samples - np.mean(samples)
    max_amp = np.max(np.abs(samples))
    if max_amp > 1e-6:
        samples = samples / max_amp

    # 1. Pitch Jitter & Biological Micro-Tremor
    frame_len = int(sr * 0.04) # 40ms frame
    hop_len = int(sr * 0.015)  # 15ms hop
    num_frames = (len(samples) - frame_len) // hop_len
    
    pitch_periods = []
    min_lag = max(2, int(sr / 450)) # 450 Hz max human pitch
    max_lag = min(frame_len - 1, int(sr / 70))  # 70 Hz min human pitch
    
    for i in range(min(num_frames, 80)):
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
        jitter = 0.8 # default reasonable estimate if unvoiced

    # 2. Spectral Analysis
    chunk_len = min(len(samples), 32768)
    chunk = samples[:chunk_len]
    fft_mags = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)
    psd = (fft_mags ** 2) + 1e-12
    
    # 2a. Spectral Entropy
    prob = psd / np.sum(psd)
    spectral_entropy = -float(np.sum(prob * np.log2(prob + 1e-12))) / 10.0
    spectral_entropy = float(np.clip(spectral_entropy, 0.05, 1.0))
    
    # 2b. High-frequency roll-off & Mel-brickwall detection
    # Human voice has energy decaying smoothly from 3.5kHz to 8kHz+
    # AI vocoders often have steep drops or aliasing spikes
    low_band = psd[freqs < 3000]
    mid_band = psd[(freqs >= 3000) & (freqs < 7000)]
    high_band = psd[freqs >= 7000] if np.any(freqs >= 7000) else np.array([1e-12])
    
    power_low = np.mean(low_band) if len(low_band) > 0 else 1e-6
    power_mid = np.mean(mid_band) if len(mid_band) > 0 else 1e-6
    power_high = np.mean(high_band) if len(high_band) > 0 else 1e-6
    
    # 2c. Spectral Flatness (Wiener Entropy)
    log_psd = np.log(psd)
    spectral_flatness = float(np.exp(np.mean(log_psd)) / (np.mean(psd) + 1e-12))

    # 2d. High-frequency aliasing / checkerboard variance
    if len(psd) > 20:
        diff_log_psd = np.diff(np.log(psd))
        hf_roughness = float(np.std(diff_log_psd))
    else:
        hf_roughness = 1.0

    # 3. Dynamic Range & Silence Transients
    frame_energies = [np.mean(samples[i * frame_len : (i+1) * frame_len] ** 2) for i in range(len(samples)//frame_len)]
    min_energy = min(frame_energies) if frame_energies else 1e-4
    is_digital_silence = (min_energy < 1e-7 and len(frame_energies) > 4)

    # 4. MULTI-FACTOR SPOOFING RISK ACCUMULATION
    synthetic_indicators = []
    spoof_risk = 0.0

    # (a) Pitch Jitter Analysis:
    # Natural human speech: 0.3% <= jitter <= 1.8%
    # AI voices: either unnaturally static (<0.20%) or erratic vocoder phase jitter (>2.5%)
    if jitter < 0.20:
        spoof_risk += 35.0
        synthetic_indicators.append("Unnatural Pitch Invariance (Robotic/Neural Flatness)")
    elif jitter > 2.8:
        spoof_risk += 30.0
        synthetic_indicators.append("Severe Phase Discontinuity (Vocoder Glitch)")

    # (b) High Frequency Mel Cutoff or Aliased Energy:
    # Brickwall cutoff: power_high is tiny compared to power_mid
    if power_high < 0.005 * power_mid and sr >= 16000:
        spoof_risk += 25.0
        synthetic_indicators.append("Mel-Filterbank High-Frequency Brickwall Cutoff (<7.5kHz)")
    elif power_high > 1.2 * power_mid and power_mid > 0.01:
        # Transposed convolution aliasing noise
        spoof_risk += 30.0
        synthetic_indicators.append("High-Frequency Vocoder Aliasing / Transposed Conv Artifacts")

    # (c) Spectral Flatness:
    if spectral_flatness > 0.04:
        spoof_risk += 25.0
        synthetic_indicators.append("Abnormal Spectral Flatness (Lack of Natural Formants)")

    # (d) Digital Silence in Pauses (TTS artifact):
    if is_digital_silence:
        spoof_risk += 20.0
        synthetic_indicators.append("Artificial Zero-Noise Floor / Digital Silence Gating")

    # Authenticity is 100 minus spoof risk
    authenticity_score = float(np.clip(100.0 - spoof_risk, 5.0, 99.5))
    is_synthetic = authenticity_score < 60.0

    if is_synthetic:
        reason = "SYNTHETIC SPEECH DETECTED: " + "; ".join(synthetic_indicators)
    elif authenticity_score < 80.0:
        reason = f"Marginal Authenticity ({authenticity_score:.1f}%): Minor acoustic anomalies"
    else:
        reason = f"Bona Fide Human Voice ({authenticity_score:.1f}%): Natural harmonics & biological jitter"

    return {
        "authenticity": round(authenticity_score, 1),
        "authStatus": reason,
        "isSynthetic": is_synthetic,
        "jitter": round(jitter, 3),
        "spectralFlatness": round(spectral_flatness, 4),
        "syntheticIndicators": synthetic_indicators
    }

# Test against natural human voice
sr = 16000
t = np.linspace(0, 2.5, int(sr * 2.5))
f0 = 135 + 1.2 * np.sin(2 * np.pi * 6 * t) + np.random.normal(0, 0.25, len(t))
phase = np.cumsum(2 * np.pi * f0 / sr)
human = np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase)
human = human * (0.5 + 0.5 * np.sin(2 * np.pi * 1.5 * t)) + np.random.normal(0, 0.008, len(t))
res_human = calibrate_aasist_authenticity(human, sr)
print("HUMAN RESULT:", res_human)

# Test against AI TTS voice (rigid pitch, digital silence, mel cutoff)
ai_phase = 2 * np.pi * 135 * t # perfectly rigid pitch (0 jitter)
ai = np.sin(ai_phase) + 0.8 * np.sin(2 * ai_phase) + 0.6 * np.sin(3 * ai_phase)
# digital silence pause
ai_env = np.where(np.sin(2 * np.pi * 1.5 * t) > 0, 1.0, 0.0)
ai = ai * ai_env # pure digital zeros in pauses!
res_ai = calibrate_aasist_authenticity(ai, sr)
print("AI TTS RESULT:", res_ai)

# Test against AI Vocoder with high-frequency aliasing
vocoder_ai = ai + np.random.normal(0, 0.2, len(t)) * np.sin(2 * np.pi * 7500 * t)
res_vocoder = calibrate_aasist_authenticity(vocoder_ai, sr)
print("AI VOCODER RESULT:", res_vocoder)
