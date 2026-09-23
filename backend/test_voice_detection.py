import urllib.request
import json
import io
import wave
import struct
import math
import numpy as np
import scipy.signal as signal

base = "http://127.0.0.1:8000"

def create_human_speech_wav(duration=2.5, sr=16000):
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples)
    
    # 1. Biological glottal pulse train with micro-tremor (~135 Hz, 0.8% natural jitter)
    t_impulse = np.zeros(n_samples)
    pitch_period = int(sr / 135)
    for p in range(0, n_samples, pitch_period):
        jitter_offset = np.random.randint(-2, 3)
        idx = max(0, min(n_samples - 1, p + jitter_offset))
        t_impulse[idx] = 1.0
        
    # Formant resonators
    b, a = signal.butter(4, [250/(sr/2), 3200/(sr/2)], btype='band')
    human_vocal = signal.lfilter(b, a, t_impulse)
    
    # Natural breathing pause and room ambiance
    env = 0.5 * (1 + np.sin(2 * np.pi * 1.0 * t))
    human_mic = human_vocal * env + np.random.normal(0, 0.004, n_samples)
    human_mic = human_mic / np.max(np.abs(human_mic))
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        for s in human_mic:
            sample = int(np.clip(s * 32767.0, -32768, 32767))
            wav.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

def create_ai_synthetic_wav(duration=2.5, sr=16000):
    n_samples = int(sr * duration)
    t = np.linspace(0, duration, n_samples)
    
    # 2. Neural Vocoder / TTS characteristics:
    # Rigid pitch (zero jitter) + pure digital silence in pauses + vocoder phase dispersion
    ai_phase = 2 * np.pi * 135 * t
    ai_speech = (
        1.0 * np.sin(ai_phase) +
        0.7 * np.sin(2 * ai_phase) +
        0.5 * np.sin(3 * ai_phase) +
        0.3 * np.sin(4 * ai_phase)
    )
    # Digital silence pauses (instant gating to zero, typical of downloaded TTS files)
    ai_env = np.where(np.sin(2 * np.pi * 1.0 * t) > 0, 1.0, 0.0)
    ai_mic = ai_speech * ai_env
    ai_mic = ai_mic / (np.max(np.abs(ai_mic)) + 1e-6)
    
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sr)
        for s in ai_mic:
            sample = int(np.clip(s * 32767.0, -32768, 32767))
            wav.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

def multipart_post(url, fields, files):
    boundary = "----VoxGuardBoundaryLiveTest"
    body = bytearray()
    
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.extend(f"{value}\r\n".encode())
        
    for name, (filename, content, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode())
        body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
        body.extend(content)
        body.extend(b"\r\n")
        
    body.extend(f"--{boundary}--\r\n".encode())
    
    req = urllib.request.Request(
        url,
        data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
    )
    r = urllib.request.urlopen(req)
    return json.loads(r.read())

print("=== TEST 1: UPLOADING NORMAL HUMAN VOICE ===")
human_bytes = create_human_speech_wav()
res_human = multipart_post(
    f"{base}/api/analyze/audio",
    fields={"caller_name": "Human Speaker Test"},
    files={"file": ("natural_human.wav", human_bytes, "audio/wav")}
)
print(f"Human Voice Result:")
print(f"  Authenticity: {res_human['authenticity']}%")
print(f"  Status: {res_human['authStatus']}")
print(f"  Action Verdict: {res_human['actionType']} -> {res_human['recommendedAction']}")
print(f"  Spectral Entropy: {res_human.get('spectralEntropy')}")
print(f"  Micro-tremor Jitter: {res_human.get('jitter')}%")
print(f"  Glottal Kurtosis: {res_human.get('kurtosis')}")
print(f"  Synthetic Indicators: {res_human.get('syntheticIndicators')}")

print("\n=== TEST 2: UPLOADING AI / SYNTHETIC VOICE ===")
ai_bytes = create_ai_synthetic_wav()
res_ai = multipart_post(
    f"{base}/api/analyze/audio",
    fields={"caller_name": "AI Deepfake / TTS Test"},
    files={"file": ("ai_voice_sample.wav", ai_bytes, "audio/wav")}
)
print(f"AI Voice Result:")
print(f"  Authenticity: {res_ai['authenticity']}%")
print(f"  Status: {res_ai['authStatus']}")
print(f"  Action Verdict: {res_ai['actionType']} -> {res_ai['recommendedAction']}")
print(f"  Spectral Entropy: {res_ai.get('spectralEntropy')}")
print(f"  Micro-tremor Jitter: {res_ai.get('jitter')}%")
print(f"  Glottal Kurtosis: {res_ai.get('kurtosis')}")
print(f"  Synthetic Indicators: {res_ai.get('syntheticIndicators')}")

assert res_human['authenticity'] >= 75.0, "Human voice should have high authenticity"
assert res_ai['authenticity'] <= 50.0, "AI voice should be detected as synthetic"
assert "SYNTHETIC" in res_ai['authStatus']
print("\n>>> DETECTION VERIFIED: AI VOICE AND NORMAL VOICE ARE ACCURATELY DIFFERENTIATED! <<<")
