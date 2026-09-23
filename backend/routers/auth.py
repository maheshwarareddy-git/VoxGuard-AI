from fastapi import APIRouter, HTTPException, Header, Depends, status
from typing import List, Optional
import uuid
import secrets
from datetime import datetime, timedelta
from database import get_connection, hash_password, verify_password
from models import UserRegisterRequest, UserLoginRequest, UserResponse, AuthResponse

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

def extract_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    parts = authorization.strip().split(" ")
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization.strip()

@router.post("/register", response_model=AuthResponse)
def register_user(req: UserRegisterRequest):
    username_clean = req.username.strip()
    email_clean = req.email.strip().lower()
    full_name_clean = req.full_name.strip()
    role_clean = (req.role or "SOC Analyst").strip()

    if len(username_clean) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if "@" not in email_clean:
        raise HTTPException(status_code=400, detail="Valid email address is required")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long")

    conn = get_connection()
    cursor = conn.cursor()

    # Check for existing username or email
    cursor.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?)", (username_clean,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Username is already taken")

    cursor.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email_clean,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email is already registered")

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    pw_hash, salt = hash_password(req.password)

    cursor.execute("""
    INSERT INTO users (id, username, email, password_hash, salt, full_name, role)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        username_clean,
        email_clean,
        pw_hash,
        salt,
        full_name_clean,
        role_clean
    ))

    # Generate session token valid for 7 days
    token = secrets.token_hex(32)
    expires_dt = datetime.utcnow() + timedelta(days=7)
    expires_str = expires_dt.isoformat() + "Z"

    cursor.execute("""
    INSERT INTO sessions (token, user_id, expires_at)
    VALUES (?, ?, ?)
    """, (token, user_id, expires_str))

    cursor.execute("SELECT created_at FROM users WHERE id = ?", (user_id,))
    created_row = cursor.fetchone()
    created_at = created_row["created_at"] if created_row else datetime.utcnow().isoformat()

    conn.commit()
    conn.close()

    user_resp = UserResponse(
        id=user_id,
        username=username_clean,
        email=email_clean,
        full_name=full_name_clean,
        role=role_clean,
        created_at=str(created_at)
    )

    return AuthResponse(
        user=user_resp,
        token=token,
        expires_at=expires_str
    )

@router.post("/login", response_model=AuthResponse)
def login_user(req: UserLoginRequest):
    identifier = req.username.strip().lower()
    if not identifier or not req.password:
        raise HTTPException(status_code=400, detail="Username and password are required")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, username, email, password_hash, salt, full_name, role, created_at
    FROM users
    WHERE LOWER(username) = ? OR LOWER(email) = ?
    """, (identifier, identifier))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(req.password, row["salt"], row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid username or password")

    user_id = row["id"]

    # Generate new session token
    token = secrets.token_hex(32)
    expires_dt = datetime.utcnow() + timedelta(days=7)
    expires_str = expires_dt.isoformat() + "Z"

    cursor.execute("""
    INSERT INTO sessions (token, user_id, expires_at)
    VALUES (?, ?, ?)
    """, (token, user_id, expires_str))

    conn.commit()
    conn.close()

    user_resp = UserResponse(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        created_at=str(row["created_at"])
    )

    return AuthResponse(
        user=user_resp,
        token=token,
        expires_at=expires_str
    )

@router.get("/me", response_model=UserResponse)
def get_current_user(token: str = Depends(extract_token_from_header)):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.token, s.expires_at, u.id, u.username, u.email, u.full_name, u.role, u.created_at
    FROM sessions s
    JOIN users u ON s.user_id = u.id
    WHERE s.token = ?
    """, (token,))

    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid or expired session token")

    # Check expiration
    expires_str = row["expires_at"]
    try:
        # Support both ISO format with Z and without
        exp_clean = expires_str.replace("Z", "")
        expires_dt = datetime.fromisoformat(exp_clean)
        if datetime.utcnow() > expires_dt:
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
            conn.close()
            raise HTTPException(status_code=401, detail="Session has expired. Please log in again.")
    except ValueError:
        pass

    conn.close()

    return UserResponse(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        full_name=row["full_name"],
        role=row["role"],
        created_at=str(row["created_at"])
    )

@router.post("/logout")
def logout_user(token: str = Depends(extract_token_from_header)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": "Logged out successfully"}

@router.get("/users", response_model=List[UserResponse])
def list_local_users():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, email, full_name, role, created_at FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [
        UserResponse(
            id=r["id"],
            username=r["username"],
            email=r["email"],
            full_name=r["full_name"],
            role=r["role"],
            created_at=str(r["created_at"])
        )
        for r in rows
    ]
