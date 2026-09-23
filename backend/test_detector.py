import sys
sys.path.append('.')
import numpy as np
import scipy.signal as signal

def extract_advanced_aasist_features(samples: np.ndarray, sr: int = 16000):
    if len(samples) < 320:
        return {"authenticity": 90.0, "isSynthetic": False, "reason": "Too short"}
    
    # Normalize
    samples = samples - np.mean(samples)
    max_amp = np.max(np.abs(samples))
    if max_amp > 1e-6:
        samples = samples / max_amp

    # 1. Pitch Jitter & Shimmer via Autocorrelation
    frame_len = int(sr * 0.04) # 40ms frames
    hop_len = int(sr * 0.01)   # 10ms hop
    num_frames = (len(samples) - frame_len) // hop_len
    
    pitch_periods = []
    peak_amps = []
    
    min_lag = int(sr / 450) # 450 Hz max human pitch
    max_lag = int(sr / 70)  # 70 Hz min human pitch
    
    for i in range(min(num_frames, 100)):
        frame = samples[i * hop_len : i * hop_len + frame_len]
        # Autocorrelation
        corr = np.correlate(frame, frame, mode='full')
        corr = corr[len(corr)//2 :]
        
        if len(corr) > max_lag:
            window = corr[min_lag:max_lag]
            peak_idx = np.argmax(window) + min_lag
            # Check voicing strength
            if corr[peak_idx] > 0.3 * corr[0]:
                pitch_periods.append(peak_idx)
                peak_amps.append(np.max(np.abs(frame)))
                
    # Jitter calculation: cycle-to-cycle perturbation
    if len(pitch_periods) > 5:
        periods = np.array(pitch_periods, dtype=np.float32)
        diffs = np.abs(np.diff(periods))
        mean_period = np.mean(periods)
        local_jitter = (np.mean(diffs) / (mean_period + 1e-6)) * 100.0
        
        # Shimmer calculation: peak amp variation
        amps = np.array(peak_amps, dtype=np.float32)
        amp_diffs = np.abs(np.diff(amps))
        mean_amp = np.mean(amps)
        local_shimmer = (np.mean(amp_diffs) / (mean_amp + 1e-6)) * 100.0
    else:
        local_jitter = 0.8
        local_shimmer = 2.5

    # 2. Spectral Analysis (FFT)
    chunk = samples[: min(len(samples), 32768)]
    fft_mags = np.abs(np.fft.rfft(chunk))
    freqs = np.fft.rfftfreq(len(chunk), 1.0 / sr)
    psd = fft_mags ** 2 + 1e-12
    
    # 2a. Spectral Flatness (Wiener Entropy)
    # Measures whether spectrum is peaky/harmonic (human formants) or flat/noisy
    log_psd = np.log(psd)
    geo_mean = np.exp(np.mean(log_psd))
    arith_mean = np.mean(psd)
    spectral_flatness = float(geo_mean / (arith_mean + 1e-12))
    
    # 2b. High-Frequency Brickwall / Mel-Cutoff Detection
    # Many TTS models cutoff sharply around 7.5kHz - 8kHz or 11kHz
    band_low = psd[freqs < 3500]
    band_mid = psd[(freqs >= 3500) & (freqs < 7500)]
    band_high = psd[freqs >= 7500] if np.any(freqs >= 7500) else np.array([1e-12])
    
    power_low = np.mean(band_low) if len(band_low) > 0 else 1e-6
    power_mid = np.mean(band_mid) if len(band_mid) > 0 else 1e-6
    power_high = np.mean(band_high) if len(band_high) > 0 else 1e-6
    
    hf_drop_ratio = float(power_high / (power_mid + 1e-12))
    
    # 2c. Transposed Convolution / Aliasing Checkerboard Artifacts
    # Vocoders produce periodic high-frequency harmonic peaks
    diff_psd = np.diff(np.log(psd + 1e-6))
    hf_fluctuation = float(np.std(diff_psd))
    
    # 3. Dynamic Range & Pause Acoustics
    # Detect pauses and measure if pause is true digital silence (TTS artifact)
    frame_energies = [np.mean(samples[i * frame_len : (i+1) * frame_len] ** 2) for i in range(len(samples)//frame_len)]
    min_energy = min(frame_energies) if frame_energies else 0.0
    max_energy = max(frame_energies) if frame_energies else 1.0
    dynamic_range_db = 10 * np.log10((max_energy + 1e-12) / (min_energy + 1e-12))
    is_digital_silence = (min_energy < 1e-8 and len(frame_energies) > 5)

    return {
        "jitter": round(float(local_jitter), 3),
        "shimmer": round(float(local_shimmer), 3),
        "spectral_flatness": round(float(spectral_flatness), 4),
        "hf_drop_ratio": round(float(hf_drop_ratio), 4),
        "hf_fluctuation": round(float(hf_fluctuation), 3),
        "dynamic_range_db": round(float(dynamic_range_db), 1),
        "is_digital_silence": is_digital_silence
    }

print("Extractor function ready")
