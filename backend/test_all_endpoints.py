import os
import sys
import json
from dotenv import load_dotenv

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from starlette.testclient import TestClient
from main import app
import database

def test_all_cloud_routes():
    print("========================================================")
    print("   VoxGuard AI — Comprehensive Cloud DB Route Testing   ")
    print("========================================================")
    
    # Verify we are on Postgres
    assert database.is_postgres_configured(), "Must be running in Cloud PostgreSQL mode"
    print("[*] Cloud Postgres Mode Active: True")
    
    client = TestClient(app)
    
    # 1. Health
    print("\n[1] Testing /api/health...")
    r = client.get("/api/health")
    assert r.status_code == 200, f"Health check failed: {r.status_code}"
    print("    -> Health:", r.json())
    
    # 2. Auth Login with default operator
    print("\n[2] Testing /api/auth/login...")
    login_payload = {"username": "operator", "password": "voxguard2026"}
    r = client.post("/api/auth/login", json=login_payload)
    assert r.status_code == 200, f"Login failed: {r.text}"
    auth_data = r.json()
    token = auth_data["token"]
    print(f"    -> Logged in as: {auth_data['user']['username']} (Role: {auth_data['user']['role']})")
    print(f"    -> Token: {token[:16]}...")
    
    # 3. Auth Me
    print("\n[3] Testing /api/auth/me...")
    headers = {"Authorization": f"Bearer {token}"}
    r = client.get("/api/auth/me", headers=headers)
    assert r.status_code == 200, f"/me failed: {r.text}"
    print("    -> Current User:", r.json()["email"])
    
    # 4. Settings
    print("\n[4] Testing /api/settings...")
    r = client.get("/api/settings")
    assert r.status_code == 200, f"Settings GET failed: {r.text}"
    settings = r.json()
    print(f"    -> Current AASIST Threshold: {settings['aasistThreshold']}%")
    
    # 5. Calls CRUD
    print("\n[5] Testing /api/calls CRUD...")
    call_payload = {
        "caller": "+1 (555) 302-8841",
        "agent": "Agent Smith",
        "duration": "02:45",
        "verdict": "CRITICAL",
        "authenticity": 12.4,
        "identity": 45.0,
        "context": "Cloud Supabase Verification Call",
        "flagged_phrases": ["digital arrest", "otp code"]
    }
    r = client.post("/api/calls", json=call_payload)
    assert r.status_code == 200, f"Call creation failed: {r.text}"
    created_call = r.json()
    created_id = created_call["id"]
    print(f"    -> Created Call: {created_id} (Verdict: {created_call['verdict']})")
    
    # List calls
    r = client.get("/api/calls")
    assert r.status_code == 200
    calls_list = r.json()
    print(f"    -> Total calls in Supabase: {len(calls_list)}")
    
    # Delete test call
    r = client.delete(f"/api/calls/{created_id}")
    assert r.status_code == 200
    print(f"    -> Cleaned up call: {created_id}")
    
    # 6. Identities
    print("\n[6] Testing /api/identities...")
    id_payload = {
        "name": "Maheshwara Reddy",
        "department": "Security Architecture"
    }
    r = client.post("/api/identities", json=id_payload)
    assert r.status_code == 200, f"Identity enrollment failed: {r.text}"
    enrolled_id = r.json()
    print(f"    -> Enrolled Identity: {enrolled_id['name']} ({enrolled_id['id']})")
    
    # List identities
    r = client.get("/api/identities")
    assert r.status_code == 200
    id_list = r.json()
    print(f"    -> Total voice profiles in Supabase: {len(id_list)}")
    
    # 7. Plans & API Keys
    print("\n[7] Testing /api/keys/plans and /api/keys/generate...")
    r = client.get("/api/keys/plans")
    assert r.status_code == 200
    plans = r.json()
    print(f"    -> Catalog currency: {plans['currency']} ({len(plans['plans'])} plans)")
    
    key_payload = {
        "name": "Cloud Supabase API Key",
        "plan_tier": "FREE"
    }
    r = client.post("/api/keys/generate", json=key_payload, headers=headers)
    assert r.status_code == 200, f"Key generation failed: {r.text}"
    api_key_data = r.json()
    print(f"    -> Generated Key: {api_key_data['key'][:16]}... (Tier: {api_key_data['plan_tier']}, Tokens: {api_key_data['tokens_remaining']})")
    
    print("\n========================================================")
    print("   ALL TESTS PASSED! Supabase Cloud Database is READY!  ")
    print("========================================================")

if __name__ == "__main__":
    test_all_cloud_routes()
