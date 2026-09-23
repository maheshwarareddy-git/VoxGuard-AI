import sqlite3
import json
import os
import re
import hashlib
import secrets
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from backend/.env or root .env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# SQLite fallback path
DB_PATH = os.path.join(os.path.dirname(__file__), "voxguard.db")

IS_POSTGRES = bool(DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")))

if IS_POSTGRES:
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        IS_POSTGRES = False
        print("Warning: psycopg2 not found. Falling back to local SQLite.")

class PostgresCursorWrapper:
    def __init__(self, raw_cursor):
        self.cursor = raw_cursor

    def _convert_query(self, query: str) -> str:
        # 1. Convert INSERT OR REPLACE INTO settings ...
        if "INSERT OR REPLACE INTO settings" in query:
            query = re.sub(
                r"INSERT\s+OR\s+REPLACE\s+INTO\s+settings\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
                r"INSERT INTO settings (\1) VALUES (\2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                query,
                flags=re.IGNORECASE
            )
        # 2. Convert standard SQLite '?' parameter placeholders to PostgreSQL '%s'
        converted = query.replace("?", "%s")
        return converted

    def execute(self, query: str, params=None):
        sql = self._convert_query(query)
        if params is not None:
            if isinstance(params, list):
                params = tuple(params)
            return self.cursor.execute(sql, params)
        return self.cursor.execute(sql)

    def executemany(self, query: str, param_list):
        sql = self._convert_query(query)
        return self.cursor.executemany(sql, param_list)

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchmany(self, size=None):
        return self.cursor.fetchmany(size)

    @property
    def rowcount(self):
        return self.cursor.rowcount

    @property
    def description(self):
        return self.cursor.description

    def close(self):
        self.cursor.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class PostgresConnectionWrapper:
    def __init__(self, raw_conn):
        self.conn = raw_conn

    def cursor(self):
        raw_cur = self.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(raw_cur)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        self.close()


def get_connection():
    """
    Returns an active database connection.
    If DATABASE_URL is configured (e.g. Neon, Supabase, Render Postgres), returns a Cloud PostgreSQL connection.
    Otherwise, returns a local SQLite connection (voxguard.db).
    """
    global IS_POSTGRES
    if IS_POSTGRES and DATABASE_URL:
        try:
            # Normalize postgres:// to postgresql:// if needed for psycopg2
            pg_url = DATABASE_URL
            if pg_url.startswith("postgres://"):
                pg_url = "postgresql://" + pg_url[len("postgres://"):]
            
            # Connect with sslmode require if not already specified in URL
            if "sslmode=" not in pg_url:
                conn = psycopg2.connect(pg_url, sslmode="require")
            else:
                conn = psycopg2.connect(pg_url)
            
            return PostgresConnectionWrapper(conn)
        except Exception as e:
            print(f"PostgreSQL connection error: {e}. Falling back to local SQLite.")
    
    # SQLite fallback
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str, salt: str = None):
    if not salt:
        salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return pw_hash, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    pw_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pw_hash, expected_hash)


def init_db(reset: bool = False):
    """
    Initializes database schema (either Cloud PostgreSQL or local SQLite) cleanly.
    Creates calls, voice_profiles, users, sessions, api_keys, payment_orders, and settings tables.
    """
    conn = get_connection()
    cursor = conn.cursor()

    if isinstance(conn, PostgresConnectionWrapper):
        # PostgreSQL Schema Initialization
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id TEXT PRIMARY KEY,
            caller TEXT NOT NULL,
            agent TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            duration TEXT NOT NULL,
            verdict TEXT NOT NULL,
            authenticity DOUBLE PRECISION NOT NULL,
            identity DOUBLE PRECISION NOT NULL,
            context TEXT NOT NULL,
            flagged_phrases TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS voice_profiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            enrolled_date TEXT NOT NULL,
            last_verified TEXT NOT NULL,
            samples INTEGER NOT NULL,
            confidence DOUBLE PRECISION NOT NULL,
            status TEXT NOT NULL,
            embedding_quality TEXT NOT NULL,
            embedding_vector TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT DEFAULT 'SOC Analyst',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            key TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            plan_tier TEXT NOT NULL,
            tokens_remaining INTEGER NOT NULL,
            tokens_total INTEGER NOT NULL,
            price_paid DOUBLE PRECISION DEFAULT 0.0,
            balance_inr DOUBLE PRECISION DEFAULT 0.0,
            minutes_remaining DOUBLE PRECISION DEFAULT 15.0,
            minutes_total DOUBLE PRECISION DEFAULT 15.0,
            rate_per_min_inr DOUBLE PRECISION DEFAULT 2.0,
            features_enabled TEXT,
            status TEXT DEFAULT 'ACTIVE',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # Postgres Column migrations if columns don't exist
        for col, col_type in [
            ("balance_inr", "DOUBLE PRECISION DEFAULT 0.0"),
            ("minutes_remaining", "DOUBLE PRECISION DEFAULT 15.0"),
            ("minutes_total", "DOUBLE PRECISION DEFAULT 15.0"),
            ("rate_per_min_inr", "DOUBLE PRECISION DEFAULT 2.0"),
            ("features_enabled", "TEXT")
        ]:
            try:
                cursor.execute(f"ALTER TABLE api_keys ADD COLUMN IF NOT EXISTS {col} {col_type};")
            except Exception:
                pass

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payment_orders (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            plan_tier TEXT NOT NULL,
            amount_inr DOUBLE PRECISION NOT NULL,
            payer_upi_id TEXT NOT NULL,
            payer_name TEXT,
            payer_email TEXT,
            merchant_vpa TEXT DEFAULT 'voxguard.business@icici',
            upi_intent_uri TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING',
            utr_reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            target_key_id TEXT,
            topup_type TEXT,
            units_to_add DOUBLE PRECISION DEFAULT 0.0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        );
        """)

        for col, col_type in [
            ("target_key_id", "TEXT"),
            ("topup_type", "TEXT"),
            ("units_to_add", "DOUBLE PRECISION DEFAULT 0.0")
        ]:
            try:
                cursor.execute(f"ALTER TABLE payment_orders ADD COLUMN IF NOT EXISTS {col} {col_type};")
            except Exception:
                pass

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """)

        cursor.execute("SELECT value FROM settings WHERE key = 'global'")
        if not cursor.fetchone():
            default_settings = {
                "aasistThreshold": 50,
                "ecapaThreshold": 70,
                "nlpSensitivity": 65,
                "emailAlerts": True,
                "slackAlerts": False,
                "criticalOnly": False,
                "autoBlock": True,
                "apiKey": "vxg_sk_live_99214820491823904812",
                "webhookUrl": "https://api.voxguard.security/hooks/amvtf-alerts"
            }
            cursor.execute(
                "INSERT INTO settings (key, value) VALUES ('global', %s) ON CONFLICT (key) DO NOTHING",
                (json.dumps(default_settings),)
            )

        cursor.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        count = row[0] if row else 0
        if count == 0:
            pw_hash, salt = hash_password("voxguard2026")
            cursor.execute("""
            INSERT INTO users (id, username, email, password_hash, salt, full_name, role)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                "usr_default_operator",
                "operator",
                "operator@voxguard.security",
                pw_hash,
                salt,
                "Security Operator",
                "Lead SOC Analyst"
            ))

        conn.commit()
        conn.close()
        return

    # SQLite Schema Initialization
    if reset and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    # Real Calls table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS calls (
        id TEXT PRIMARY KEY,
        caller TEXT NOT NULL,
        agent TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        duration TEXT NOT NULL,
        verdict TEXT NOT NULL,
        authenticity REAL NOT NULL,
        identity REAL NOT NULL,
        context TEXT NOT NULL,
        flagged_phrases TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Real Voice profiles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voice_profiles (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT NOT NULL,
        enrolled_date TEXT NOT NULL,
        last_verified TEXT NOT NULL,
        samples INTEGER NOT NULL,
        confidence REAL NOT NULL,
        status TEXT NOT NULL,
        embedding_quality TEXT NOT NULL,
        embedding_vector TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        role TEXT DEFAULT 'SOC Analyst',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # API Keys & Token Billing table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        key TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        plan_tier TEXT NOT NULL,
        tokens_remaining INTEGER NOT NULL,
        tokens_total INTEGER NOT NULL,
        price_paid REAL DEFAULT 0.0,
        balance_inr REAL DEFAULT 0.0,
        minutes_remaining REAL DEFAULT 15.0,
        minutes_total REAL DEFAULT 15.0,
        rate_per_min_inr REAL DEFAULT 2.0,
        features_enabled TEXT,
        status TEXT DEFAULT 'ACTIVE',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_used_at TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    """)

    # Safe migration for usage-based billing columns in existing api_keys tables
    cursor.execute("PRAGMA table_info(api_keys)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    billing_cols = [
        ("balance_inr", "REAL DEFAULT 0.0"),
        ("minutes_remaining", "REAL DEFAULT 15.0"),
        ("minutes_total", "REAL DEFAULT 15.0"),
        ("rate_per_min_inr", "REAL DEFAULT 2.0"),
        ("features_enabled", "TEXT")
    ]
    for col_name, col_def in billing_cols:
        if col_name not in existing_cols:
            try:
                cursor.execute(f"ALTER TABLE api_keys ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

    # Payment Orders table for real UPI Collect & verification
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payment_orders (
        id TEXT PRIMARY KEY,
        user_id TEXT,
        plan_tier TEXT NOT NULL,
        amount_inr REAL NOT NULL,
        payer_upi_id TEXT NOT NULL,
        payer_name TEXT,
        payer_email TEXT,
        merchant_vpa TEXT DEFAULT 'voxguard.business@icici',
        upi_intent_uri TEXT NOT NULL,
        status TEXT DEFAULT 'PENDING',
        utr_reference TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        completed_at TIMESTAMP,
        target_key_id TEXT,
        topup_type TEXT,
        units_to_add REAL DEFAULT 0.0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
    )
    """)

    cursor.execute("PRAGMA table_info(payment_orders)")
    po_cols = {row[1] for row in cursor.fetchall()}
    for col_name, col_def in [
        ("target_key_id", "TEXT"),
        ("topup_type", "TEXT"),
        ("units_to_add", "REAL DEFAULT 0.0")
    ]:
        if col_name not in po_cols:
            try:
                cursor.execute(f"ALTER TABLE payment_orders ADD COLUMN {col_name} {col_def}")
            except Exception:
                pass

    # System configuration settings table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Initialize default operational engine thresholds if not present
    cursor.execute("SELECT value FROM settings WHERE key = 'global'")
    if not cursor.fetchone():
        default_settings = {
            "aasistThreshold": 50,
            "ecapaThreshold": 70,
            "nlpSensitivity": 65,
            "emailAlerts": True,
            "slackAlerts": False,
            "criticalOnly": False,
            "autoBlock": True,
            "apiKey": "vxg_sk_live_99214820491823904812",
            "webhookUrl": "https://api.voxguard.security/hooks/amvtf-alerts"
        }
        cursor.execute("""
        INSERT INTO settings (key, value) VALUES ('global', ?)
        """, (json.dumps(default_settings),))

    # Pre-seed default operator account if no users exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        pw_hash, salt = hash_password("voxguard2026")
        cursor.execute("""
        INSERT INTO users (id, username, email, password_hash, salt, full_name, role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "usr_default_operator",
            "operator",
            "operator@voxguard.security",
            pw_hash,
            salt,
            "Security Operator",
            "Lead SOC Analyst"
        ))

    conn.commit()
    conn.close()


def clear_all_calls():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM calls")
    conn.commit()
    conn.close()


def clear_all_identities():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM voice_profiles")
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db(reset=False)
    print("Database verified and schema initialized successfully.")
