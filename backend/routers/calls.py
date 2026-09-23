from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
from datetime import datetime
from database import get_connection, clear_all_calls
from models import CallRecordCreate, CallRecordResponse

router = APIRouter(prefix="/api/calls", tags=["Calls"])

@router.get("", response_model=List[CallRecordResponse])
def get_calls(
    verdict: Optional[str] = Query(None, description="Filter by verdict: SAFE, WARNING, CRITICAL"),
    search: Optional[str] = Query(None, description="Search by caller, agent, or context")
):
    conn = get_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM calls WHERE 1=1"
    params = []

    if verdict and verdict != "ALL":
        query += " AND verdict = ?"
        params.append(verdict)

    if search:
        query += " AND (caller LIKE ? OR agent LIKE ? OR context LIKE ? OR id LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term, term])

    query += " ORDER BY created_at DESC"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        results.append(CallRecordResponse(
            id=r["id"],
            caller=r["caller"],
            agent=r["agent"],
            date=r["date"],
            time=r["time"],
            duration=r["duration"],
            verdict=r["verdict"],
            authenticity=float(r["authenticity"]),
            identity=float(r["identity"]),
            context=r["context"],
            flaggedPhrases=json.loads(r["flagged_phrases"]) if r["flagged_phrases"] else []
        ))
    return results

@router.post("", response_model=CallRecordResponse)
def create_call(call: CallRecordCreate):
    conn = get_connection()
    cursor = conn.cursor()

    # Generate next ID
    cursor.execute("SELECT COUNT(*) FROM calls")
    count = cursor.fetchone()[0]
    call_id = f"VX-{8900 + count + 1}"
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    cursor.execute("""
    INSERT INTO calls (id, caller, agent, date, time, duration, verdict, authenticity, identity, context, flagged_phrases)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        call_id,
        call.caller,
        call.agent,
        date_str,
        time_str,
        call.duration,
        call.verdict,
        call.authenticity,
        call.identity,
        call.context,
        json.dumps(call.flagged_phrases)
    ))
    conn.commit()
    conn.close()

    return CallRecordResponse(
        id=call_id,
        caller=call.caller,
        agent=call.agent,
        date=date_str,
        time=time_str,
        duration=call.duration,
        verdict=call.verdict,
        authenticity=call.authenticity,
        identity=call.identity,
        context=call.context,
        flaggedPhrases=call.flagged_phrases
    )

@router.delete("/all")
def clear_all():
    clear_all_calls()
    return {"status": "success", "message": "All call records cleared"}

@router.delete("/{call_id}")
def delete_call(call_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calls WHERE id = ?", (call_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "deleted": call_id}
