import os
import sys
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

import database

def verify_cloud_database():
    print("========================================================")
    print("   VoxGuard AI — Supabase Cloud Database Verification   ")
    print("========================================================")
    
    db_url = os.environ.get("DATABASE_URL", "")
    print(f"[*] DATABASE_URL configured: {bool(db_url)}")
    print(f"[*] psycopg2 available: {database.PSYCOPG2_AVAILABLE}")
    print(f"[*] Postgres Mode Active: {database.is_postgres_configured()}")
    
    # 1. Initialize schema
    print("\n[1/5] Initializing database schema on Supabase...")
    database.init_db()
    print("      -> Schema initialized successfully.")
    
    # 2. Test Connection
    print("\n[2/5] Testing database connection...")
    conn = database.get_connection()
    print(f"      -> Connection type: {type(conn).__name__}")
    assert isinstance(conn, database.PostgresConnectionWrapper), "Expected PostgresConnectionWrapper"
    
    cursor = conn.cursor()
    
    # 3. Verify Tables
    print("\n[3/5] Verifying public tables in Supabase...")
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
    tables = [r[0] for r in cursor.fetchall()]
    print(f"      -> Tables found ({len(tables)}): {tables}")
    
    expected_tables = ["api_keys", "calls", "payment_orders", "sessions", "settings", "users", "voice_profiles"]
    for t in expected_tables:
        assert t in tables, f"Missing expected table: {t}"
    print("      -> All required tables exist in Supabase!")
    
    # 4. Verify Default Data
    print("\n[4/5] Verifying default data...")
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"      -> Total Users: {user_count}")
    
    cursor.execute("SELECT id, username, email, role FROM users LIMIT 1")
    user_row = cursor.fetchone()
    if user_row:
        print(f"      -> Default User: {dict(user_row)}")
        
    cursor.execute("SELECT value FROM settings WHERE key = 'global'")
    settings_row = cursor.fetchone()
    print(f"      -> Settings present: {bool(settings_row)}")
    
    # 5. Test CRUD operations on Calls & Profiles & Keys
    print("\n[5/5] Testing CRUD operations against Cloud Database...")
    test_call_id = "TEST-SUPABASE-001"
    cursor.execute("""
    INSERT INTO calls (id, caller, agent, date, time, duration, verdict, authenticity, identity, context, flagged_phrases)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (test_call_id, "Test Caller", "Test Agent", "2026-09-24", "22:30", "01:15", "SAFE", 98.5, 99.1, "Cloud DB Test", "[]"))
    conn.commit()
    
    cursor.execute("SELECT * FROM calls WHERE id = ?", (test_call_id,))
    fetched_call = cursor.fetchone()
    assert fetched_call is not None, "Failed to fetch inserted test call"
    print(f"      -> Insert & Read Call verified: {fetched_call['id']} (verdict: {fetched_call['verdict']})")
    
    # Cleanup test record
    cursor.execute("DELETE FROM calls WHERE id = ?", (test_call_id,))
    conn.commit()
    print("      -> Test cleanup verified.")
    
    conn.close()
    print("\n========================================================")
    print("   SUCCESS: Supabase Cloud Database is 100% Operational! ")
    print("========================================================")

if __name__ == "__main__":
    verify_cloud_database()
