import numpy as np
from scipy import signal
import os
import soundfile as sf

def apply_telephony_bandpass(samples: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Standard ITU-T G.712 300 Hz - 3400 Hz PSTN / Cellular bandpass filter."""
    nyq = sr / 2.0
    low = 300.0 / nyq
    high = min(3400.0 / nyq, 0.98)
    b, a = signal.butter(4, [low, high], btype='band')
    return signal.filtfilt(b, a, samples).astype(np.float32)

def apply_8k_resampling(samples: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Downsamples audio to 8 kHz telephony rate, then reconstructs to 16 kHz."""
    if sr != 16000:
        return samples
    # Downsample by factor of 2 (16kHz -> 8kHz)
    down = signal.resample_poly(samples, 1, 2)
    # Reconstruct back to 16kHz
    up = signal.resample_poly(down, 2, 1)
    # Ensure length matches
    if len(up) > len(samples):
        up = up[:len(samples)]
    elif len(up) < len(samples):
        up = np.pad(up, (0, len(samples) - len(up)))
    return up.astype(np.float32)

def apply_g711_mu_law(samples: np.ndarray, mu: int = 255) -> np.ndarray:
    """
    Simulates ITU-T G.711 mu-law 8-bit logarithmic companding.
    Quantizes 16-bit linear PCM into 8-bit logarithmic dynamic range.
    """
    # Normalize to [-1.0, 1.0]
    mx = np.max(np.abs(samples))
    if mx > 1e-6:
        norm = samples / mx
    else:
        norm = samples

    # Compress
    comp = np.sign(norm) * np.log(1.0 + mu * np.abs(norm)) / np.log(1.0 + mu)
    # 8-bit quantization (256 discrete levels)
    quant = np.round(comp * 127.0) / 127.0
    # Expand
    expanded = np.sign(quant) * (1.0 / mu) * ((1.0 + mu) ** np.abs(quant) - 1.0)

    if mx > 1e-6:
        return (expanded * mx).astype(np.float32)
    return expanded.astype(np.float32)

def apply_telephony_channel_noise(samples: np.ndarray, sr: int = 16000) -> np.ndarray:
    """Adds realistic line hum (50Hz + harmonics) and random 20ms burst packet jitter."""
    out = np.copy(samples)
    t = np.arange(len(out)) / sr

    # 50 Hz power line hum + 150 Hz 3rd harmonic (-36 dB)
    hum = 0.003 * np.sin(2 * np.pi * 50 * t) + 0.001 * np.sin(2 * np.pi * 150 * t)
    # Low-level comfort noise (-42 dB)
    noise = 0.002 * np.random.randn(len(out))
    out = out + hum + noise

    # Occasional 20ms packet drop / VoIP burst jitter (1-2 per 3 seconds)
    frame_drop_len = int(sr * 0.020)
    n_drops = np.random.randint(0, 3)
    for _ in range(n_drops):
        start = np.random.randint(0, max(1, len(out) - frame_drop_len))
        out[start : start + frame_drop_len] *= 0.05

    return out.astype(np.float32)

def simulate_telephony_call(samples: np.ndarray, sr: int = 16000) -> np.ndarray:
    """
    Full End-to-End PSTN / GSM / Cellular Telephony Codec Pipeline:
    1. 8 kHz decimation & reconstruction
    2. 300 - 3400 Hz bandpass filter
    3. G.711 mu-law 8-bit companding
    4. Line hum & packet jitter noise
    """
    s = apply_8k_resampling(samples, sr)
    s = apply_telephony_bandpass(s, sr)
    s = apply_g711_mu_law(s)
    s = apply_telephony_channel_noise(s, sr)
    return s

def augment_dataset_with_telephony(src_dir: str, dst_dir: str, tag: str, max_files: int = 250):
    """Augments a selection of audio files with telephony codec degradation."""
    os.makedirs(dst_dir, exist_ok=True)
    files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.lower().endswith(('.wav', '.mp3', '.flac', '.ogg'))]
    print(f"\n[TELEPHONY AUGMENTATION] Processing up to {max_files} files from {os.path.basename(src_dir)}...")
    augmented = 0
    for i, fpath in enumerate(files[:max_files]):
        fname = os.path.basename(fpath)
        stem, ext = os.path.splitext(fname)
        out_name = f"{tag}_telephony_{stem}.wav"
        out_path = os.path.join(dst_dir, out_name)
        if os.path.exists(out_path):
            continue
        try:
            data, sr = sf.read(fpath, dtype='float32')
            if data.ndim > 1:
                data = np.mean(data, axis=1)
            if sr != 16000:
                num_out = int(len(data) * 16000 / sr)
                data = signal.resample(data, num_out).astype(np.float32)
                sr = 16000
            
            telephony_audio = simulate_telephony_call(data, sr)
            sf.write(out_path, telephony_audio, 16000)
            augmented += 1
        except Exception:
            pass
    print(f"[DONE] Created {augmented} telephony-augmented audio files in {dst_dir}.")
    return augmented

if __name__ == "__main__":
    BASE_DIR = r"c:\Users\mahesh\Desktop\VoxGuard"
    HUMAN_DIR = os.path.join(BASE_DIR, "training_data", "human_bonafide")
    AI_DIR = os.path.join(BASE_DIR, "training_data", "ai_online")

    print("=" * 75)
    print("VOXGUARD NATIVE TELEPHONY & CODEC SIMULATOR (PSTN/GSM/G.711)")
    print("=" * 75)
    # Augment some human files (Fleurs, Minds14) with telephony call conditions
    augment_dataset_with_telephony(HUMAN_DIR, HUMAN_DIR, tag="tel_human", max_files=200)
    # Augment some AI files (ElevenLabs, OpenAI, Google) with telephony call conditions
    augment_dataset_with_telephony(AI_DIR, AI_DIR, tag="tel_ai", max_files=200)
