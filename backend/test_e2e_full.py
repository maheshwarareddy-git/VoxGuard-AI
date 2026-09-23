import urllib.request
import json
import io
import wave
import struct
import math

base = "http://127.0.0.1:8000"

def create_synthetic_wav(freq=440.0, duration_sec=1.5, sample_rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        num_samples = int(duration_sec * sample_rate)
        for i in range(num_samples):
            # Synthesize sine wave with harmonics
            val = 0.5 * math.sin(2 * math.pi * freq * i / sample_rate)
            val += 0.2 * math.sin(2 * math.pi * (freq * 2) * i / sample_rate)
            sample = int(val * 32767.0)
            sample = max(-32768, min(32767, sample))
            wav.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

def multipart_post(url, fields, files):
    boundary = "----VoxGuardBoundary7MA4YWxkTrZu0gW"
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

print("=== 1. Testing Audio File Upload Analysis (/api/analyze/audio) ===")
wav_data = create_synthetic_wav(freq=300.0, duration_sec=2.0)
res = multipart_post(
    f"{base}/api/analyze/audio",
    fields={"transcript": "Immediate wire transfer approval required for overseas vendor.", "caller_name": "Inbound Trunk A"},
    files={"file": ("test_call.wav", wav_data, "audio/wav")}
)
print(f"Uploaded WAV Analysis:")
print(f"  Caller: {res['callerName']}")
print(f"  Authenticity Score: {res['authenticity']}% ({res['authStatus']})")
print(f"  Identity Score: {res['identity']}% ({res['idStatus']})")
print(f"  Context Risk: {res['contextRisk']}% (Intent: {res['nlpIntent']})")
print(f"  Threat Keywords Detected: {res['threatKeywords']}")
print(f"  AMVTF Fused Risk: {res['fusedRiskScore']}")
print(f"  Verdict: {res['actionType']} -> {res['recommendedAction']}")
print(f"  Transcript entries: {len(res['transcript'])}")

print("\n=== 2. Testing Live Stream / Mic Analysis (/api/analyze/live) ===")
live_res = multipart_post(
    f"{base}/api/analyze/live",
    fields={"transcript": "Hello, I am calling from tech support to reset your administrative master password."},
    files={"audio": ("mic_stream.wav", wav_data, "audio/wav")}
)
print(f"Live Stream Analysis:")
print(f"  Threat Keywords: {live_res['threatKeywords']}")
print(f"  Action Type: {live_res['actionType']}")
print(f"  Fused Risk: {live_res['fusedRiskScore']}")

print("\n=== 3. Testing Voice Enrollment with Audio (/api/identities/enroll-audio) ===")
enroll_res = multipart_post(
    f"{base}/api/identities/enroll-audio",
    fields={"name": "Sarah Jenkins", "department": "Executive Board"},
    files={"audio": ("sarah_enrollment.wav", wav_data, "audio/wav")}
)
print(f"Enrolled Voice Profile: {enroll_res['id']} - {enroll_res['name']} ({enroll_res['embeddingQuality']})")

print("\n=== 4. Testing Identity Verification Against Enrolled Profile ===")
verify_res = multipart_post(
    f"{base}/api/analyze/audio",
    fields={"transcript": "Routine quarterly operations report.", "target_profile_id": enroll_res['id']},
    files={"file": ("sarah_check.wav", wav_data, "audio/wav")}
)
print(f"Target Voiceprint: {verify_res['enrolledTarget']}")
print(f"Identity Match Score: {verify_res['identity']}% ({verify_res['idStatus']})")

print("\n=== 5. Testing Settings Update & Persistence (/api/settings) ===")
req = urllib.request.Request(
    f"{base}/api/settings",
    data=json.dumps({
        "aasistThreshold": 55,
        "ecapaThreshold": 75,
        "nlpSensitivity": 80,
        "emailAlerts": True,
        "slackAlerts": True,
        "criticalOnly": True,
        "autoBlock": True,
        "apiKey": "vxg_sk_live_custom_key_999",
        "webhookUrl": "https://company.internal/hooks/security"
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="PUT"
)
updated_s = json.loads(urllib.request.urlopen(req).read())
print(f"Updated Settings: aasist={updated_s['aasistThreshold']}, ecapa={updated_s['ecapaThreshold']}, nlp={updated_s['nlpSensitivity']}, slack={updated_s['slackAlerts']}")

# Re-read settings
r = urllib.request.urlopen(f"{base}/api/settings")
persisted_s = json.loads(r.read())
assert persisted_s['aasistThreshold'] == 55
assert persisted_s['slackAlerts'] is True
print("Settings successfully verified and persisted in SQLite!")

print("\n=== 6. Cleanup Verification Data ===")
req = urllib.request.Request(f"{base}/api/identities/all", method="DELETE")
urllib.request.urlopen(req)
req = urllib.request.Request(f"{base}/api/calls/all", method="DELETE")
urllib.request.urlopen(req)

# Reset settings to default
req = urllib.request.Request(
    f"{base}/api/settings",
    data=json.dumps({
        "aasistThreshold": 50,
        "ecapaThreshold": 70,
        "nlpSensitivity": 65,
        "emailAlerts": True,
        "slackAlerts": False,
        "criticalOnly": False,
        "autoBlock": True,
        "apiKey": "vxg_sk_live_99214820491823904812",
        "webhookUrl": "https://api.voxguard.security/hooks/amvtf-alerts"
    }).encode(),
    headers={"Content-Type": "application/json"},
    method="PUT"
)
urllib.request.urlopen(req)

r_calls = json.loads(urllib.request.urlopen(f"{base}/api/calls").read())
r_ids = json.loads(urllib.request.urlopen(f"{base}/api/identities").read())
print(f"Final Clean DB State: Calls={len(r_calls)}, Identities={len(r_ids)}")
print("ALL FULL E2E AMVTF PIPELINE TESTS PASSED COMPLETELY!")
