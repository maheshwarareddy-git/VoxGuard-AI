import os
import sys
import requests
import numpy as np

sys_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(sys_path, "backend"))
from engines.aasist import aasist_engine

samples = [
    ('OpenAI ChatGPT Voice', os.path.join(sys_path, r'training_data\ai_online\openai_audio31585.wav'), True),
    ('Google / Gemini Voice', os.path.join(sys_path, r'training_data\ai_online\google_voice_sample.mp3'), True),
    ('Azure / Claude / Copilot', os.path.join(sys_path, r'training_data\ai_online\neural_en-US-JennyNeural_0.mp3'), True),
    ('ElevenLabs Cloned Voice', os.path.join(sys_path, r'training_data\ai_online\ElevenLabs_2026-09-07T17_16_09_Bella - Professional, Bright, Warm_pre_sp100_s50_sb75_se0_b_m2.mp3'), True),
    ('ASVspoof Challenge Attack', os.path.join(sys_path, r'training_data\asvspoof\asvspoof2015_spoof_0.wav'), True),
    ('Bona Fide Human 1', os.path.join(sys_path, r'training_data\human_bonafide\human1.mp4'), False),
    ('Bona Fide Human 3', os.path.join(sys_path, r'training_data\human_bonafide\human3.mp4'), False),
    ('Bona Fide Human (LibriSpeech)', os.path.join(sys_path, r'training_data\human_bonafide\librispeech_human_0.wav'), False),
    ('Bona Fide Human (LibriSpeech 2)', os.path.join(sys_path, r'training_data\human_bonafide\librispeech_human_12.wav'), False)
]

print(f"{'PLATFORM / VOICE':<32} | {'EXPECTED':<8} | {'AUTHENTICITY':<12} | {'PREDICTED':<9} | {'STATUS'}")
print("-" * 80)

total_passed = 0
for name, full_p, exp_ai in samples:
    data, sr = aasist_engine._decode_audio(open(full_p, 'rb').read())
    chunk = (np.clip(data[:int(sr*1.8)], -1.0, 1.0) * 32767).astype(np.int16).tobytes()
    
    res = requests.post(
        'http://127.0.0.1:8000/api/analyze/live',
        data={'transcript': 'Voice verification analysis live session.'},
        files={'audio': ('chunk.raw', chunk, 'application/octet-stream')},
        timeout=5
    )
    d = res.json()
    auth = d.get('authenticity', 0.0)
    is_ai = auth < 55.0 or bool(d.get('syntheticIndicators'))
    pred = 'AI' if is_ai else 'HUMAN'
    exp = 'AI' if exp_ai else 'HUMAN'
    passed = (pred == exp)
    if passed:
        total_passed += 1
    status_str = '[PASS] OK' if passed else '[FAIL]'
    print(f"{name:<32} | {exp:<8} | {auth:>10.1f}% | {pred:<9} | {status_str}")

print("=" * 80)
print(f"LIVE SERVER ENDPOINT ACCURACY: {total_passed}/{len(samples)} ({total_passed/len(samples)*100:.1f}%)")
print("=" * 80)
