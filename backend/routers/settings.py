from fastapi import APIRouter, HTTPException
import json
from database import get_connection
from models import SystemSettingsSchema

router = APIRouter(prefix="/api/settings", tags=["Settings"])

@router.get("", response_model=SystemSettingsSchema)
def get_settings():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = 'global'")
    row = cursor.fetchone()
    conn.close()

    if not row:
        return SystemSettingsSchema()
    
    data = json.loads(row["value"])
    return SystemSettingsSchema(**data)

@router.put("", response_model=SystemSettingsSchema)
def update_settings(settings: SystemSettingsSchema):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM settings WHERE key = 'global'")
    if cursor.fetchone():
        cursor.execute("UPDATE settings SET value = ? WHERE key = 'global'", (settings.model_dump_json(),))
    else:
        cursor.execute("INSERT INTO settings (key, value) VALUES ('global', ?)", (settings.model_dump_json(),))
    conn.commit()
    conn.close()
    return settings
