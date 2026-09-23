import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio
from database import init_db
from routers import calls, identities, settings, analyze, auth, keys

# Initialize database
init_db()

app = FastAPI(
    title="VoxGuard / EchoGuard AI — SOC Backend Engine",
    description="Real-Time Multi-Modal Voice Trust & Threat Response System",
    version="2.4.0"
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(keys.router)
app.include_router(calls.router)
app.include_router(identities.router)
app.include_router(settings.router)
app.include_router(analyze.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "system": "EchoGuard AI",
        "engine": "AMVTF v2.4",
        "models": {
            "authenticity": "AASIST GNN (Audio Anti-Spoofing)",
            "identity": "ECAPA-TDNN 192-dim Speaker Verification",
            "nlp": "DistilBERT Contextual Threat Classifier"
        }
    }

@app.websocket("/ws/audio-stream")
async def websocket_audio_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            # Parse incoming audio metadata/chunk
            try:
                payload = json.loads(data)
                # Echo simulated live frame processing
                await websocket.send_json({
                    "type": "FRAME_PROCESSED",
                    "vadActive": True,
                    "frameRms": 0.42,
                    "authenticityEstimate": 96.5,
                    "latencyMs": 18
                })
            except Exception:
                await websocket.send_text("PONG")
    except WebSocketDisconnect:
        pass

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)
