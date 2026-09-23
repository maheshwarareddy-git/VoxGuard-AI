from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from typing import List, Optional
import json
from datetime import datetime
from database import get_connection, clear_all_identities
from models import VoiceProfileCreate, VoiceProfileResponse
from engines.ecapa import ecapa_engine

router = APIRouter(prefix="/api/identities", tags=["Identities"])

@router.get("", response_model=List[VoiceProfileResponse])
def get_identities(
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, PENDING, REVOKED"),
    search: Optional[str] = Query(None, description="Search by name, department, or ID")
):
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM voice_profiles WHERE 1=1"
    params = []

    if status and status != "ALL":
        query += " AND status = ?"
        params.append(status)

    if search:
        query += " AND (name LIKE ? OR department LIKE ? OR id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append(VoiceProfileResponse(
            id=r["id"],
            name=r["name"],
            department=r["department"],
            enrolledDate=r["enrolled_date"],
            lastVerified=r["last_verified"],
            samples=r["samples"],
            confidence=float(r["confidence"]),
            status=r["status"],
            embeddingQuality=r["embedding_quality"]
        ))
    return results

@router.post("", response_model=VoiceProfileResponse)
def enroll_identity(profile: VoiceProfileCreate):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM voice_profiles")
    count = cursor.fetchone()[0]
    vp_id = f"VP-{count + 1:03d}"
    now_str = datetime.now().strftime("%Y-%m-%d")

    # Extract 192-dim embedding
    embedding_vec = ecapa_engine.extract_embedding()

    cursor.execute("""
    INSERT INTO voice_profiles (id, name, department, enrolled_date, last_verified, samples, confidence, status, embedding_quality, embedding_vector)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        vp_id,
        profile.name,
        profile.department,
        now_str,
        "Today",
        3,
        96.0,
        "ACTIVE",
        "HIGH",
        json.dumps(embedding_vec)
    ))
    conn.commit()
    conn.close()

    return VoiceProfileResponse(
        id=vp_id,
        name=profile.name,
        department=profile.department,
        enrolledDate=now_str,
        lastVerified="Today",
        samples=3,
        confidence=96.0,
        status="ACTIVE",
        embeddingQuality="HIGH"
    )

@router.post("/enroll-audio", response_model=VoiceProfileResponse)
async def enroll_with_audio(
    name: str = Form(...),
    department: str = Form(...),
    audio: UploadFile = File(...)
):
    """
    Enrolls a new identity by extracting a 192-dimensional acoustic embedding vector
    directly from an uploaded or recorded voice sample (.wav / .mp3 / audio blob).
    """
    audio_bytes = await audio.read()
    if not audio_bytes or len(audio_bytes) < 44:
        raise HTTPException(status_code=400, detail="Invalid audio sample provided.")

    embedding_vec = ecapa_engine.extract_embedding(audio_bytes)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM voice_profiles")
    count = cursor.fetchone()[0]
    vp_id = f"VP-{count + 1:03d}"
    now_str = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
    INSERT INTO voice_profiles (id, name, department, enrolled_date, last_verified, samples, confidence, status, embedding_quality, embedding_vector)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        vp_id,
        name,
        department,
        now_str,
        "Today",
        5,
        98.0,
        "ACTIVE",
        "HIGH",
        json.dumps(embedding_vec)
    ))
    conn.commit()
    conn.close()

    return VoiceProfileResponse(
        id=vp_id,
        name=name,
        department=department,
        enrolledDate=now_str,
        lastVerified="Today",
        samples=5,
        confidence=98.0,
        status="ACTIVE",
        embeddingQuality="HIGH"
    )

@router.delete("/all")
def clear_all():
    clear_all_identities()
    return {"status": "success", "message": "All voice profiles cleared"}

@router.delete("/{profile_id}")
def delete_identity(profile_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM voice_profiles WHERE id = ?", (profile_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted": profile_id}
