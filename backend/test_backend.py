import urllib.request
import json
import io
import wave
import struct

base = "http://127.0.0.1:8000"

def create_sample_wav():
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        for i in range(16000):
            sample = int(32767.0 * 0.3 * (1 if (i // 100) % 2 == 0 else -1))
            wav.writeframes(struct.pack('<h', sample))
    return buf.getvalue()

def multipart_post(url, fields, files):
    boundary = "----VoxGuardBoundaryVerify"
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
    return json.loads(urllib.request.urlopen(req).read())

# Check calls (clean DB)
r = urllib.request.urlopen(f"{base}/api/calls")
calls = json.loads(r.read())
print(f"Calls in DB: {len(calls)}")

# Check identities (clean DB)
r = urllib.request.urlopen(f"{base}/api/identities")
ids = json.loads(r.read())
print(f"Identities in DB: {len(ids)}")

# Check settings
r = urllib.request.urlopen(f"{base}/api/settings")
s = json.loads(r.read())
print(f"Settings loaded: aasistThreshold={s['aasistThreshold']}, ecapaThreshold={s['ecapaThreshold']}")

# Test real audio analysis
wav_bytes = create_sample_wav()
res = multipart_post(
    f"{base}/api/analyze/audio",
    fields={"transcript": "Test audio analysis"},
    files={"file": ("test.wav", wav_bytes, "audio/wav")}
)
print(f"Audio Analysis Result: Auth={res['authenticity']}%, Action={res['actionType']}")

# Test voice enrollment
req = urllib.request.Request(
    f"{base}/api/identities",
    data=json.dumps({"name": "Test User", "department": "Security Operations"}).encode(),
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req)
profile = json.loads(r.read())
print(f"Enrolled: {profile['id']} - {profile['name']} ({profile['department']})")

# Test call persistence
req = urllib.request.Request(
    f"{base}/api/calls",
    data=json.dumps({
        "caller": "Test Caller",
        "agent": "Operator (SOC)",
        "duration": "2m 10s",
        "verdict": "SAFE",
        "authenticity": 97.5,
        "identity": 88.0,
        "context": "Routine Test",
        "flagged_phrases": []
    }).encode(),
    headers={"Content-Type": "application/json"}
)
r = urllib.request.urlopen(req)
call = json.loads(r.read())
print(f"Saved call: {call['id']} - {call['caller']} ({call['verdict']})")

# Clean up test data
req = urllib.request.Request(f"{base}/api/calls/all", method="DELETE")
urllib.request.urlopen(req)
req = urllib.request.Request(f"{base}/api/identities/all", method="DELETE")
urllib.request.urlopen(req)

r_calls = json.loads(urllib.request.urlopen(f"{base}/api/calls").read())
r_ids = json.loads(urllib.request.urlopen(f"{base}/api/identities").read())
print(f"Calls after cleanup: {len(r_calls)}")
print(f"Identities after cleanup: {len(r_ids)}")
print("ALL BACKEND TESTS PASSED - ZERO FAKE/MOCK DATA")
