import urllib.request
import json
import sys

# Windows console encoding
sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:8000"

def test_plans_catalog():
    print("\n--- 1. Testing GET /api/keys/plans ---")
    req = urllib.request.Request(f"{BASE_URL}/api/keys/plans")
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print(f"Currency: {data['currency']} ({data['symbol']})")
        assert data['currency'] == 'INR', f"Expected INR, got {data['currency']}"
        assert data['default_audio_rate_per_min_inr'] == 2.0, f"Expected 2.0, got {data['default_audio_rate_per_min_inr']}"
        
        plans = data['plans']
        print(f"Plans count: {len(plans)}")
        for p in plans:
            print(f"  Plan: {p['label']} ({p['id']}) - ₹{p['price_inr']} | Tokens: {p['tokens_included']} | Mins: {p['audio_minutes_included']} | Rate: ₹{p['rate_per_min_inr']}/min | Profiles: {p['voiceprints_limit']}")
            print(f"    Features count: {len(p['features'])}")
        
        # Verify Free plan has 550 tokens
        free_plan = next(p for p in plans if p['id'] == 'FREE')
        assert free_plan['tokens_included'] == 550, f"Free plan tokens should be 550, got {free_plan['tokens_included']}"
        assert free_plan['rate_per_min_inr'] == 2.0
        
        # Verify Enterprise plan has all features
        ent_plan = next(p for p in plans if p['id'] == 'ENTERPRISE')
        assert ent_plan['price_inr'] == 2999
        assert len(ent_plan['features']) > len(free_plan['features'])
        
        # Verify token packs
        print("\nToken Packs (INR):")
        for tp in data['token_packs']:
            print(f"  {tp['label']}: {tp['tokens']} tokens for ₹{tp['price_inr']} ({tp['unit_rate']})")
            
        # Verify minute packs
        print("\nMinute Packs (INR @ ₹2/min):")
        for mp in data['minutes_packs']:
            print(f"  {mp['label']}: {mp['minutes']} mins for ₹{mp['price_inr']} ({mp['unit_rate']})")
            
    print(">>> SUCCESS: Plans catalog endpoint fully compliant!")

def test_api_key_lifecycle():
    print("\n--- 2. Testing API Key Creation, Validation & INR Minute Usage ---")
    
    # 1. Create Free key
    gen_payload = json.dumps({"name": "Test Pay-As-You-Go Key", "plan_tier": "FREE"}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/keys/generate", data=gen_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        key_data = json.loads(resp.read().decode())
        raw_key = key_data["key"]
        print(f"Generated Key: {key_data['key'][:12]}... (Plan: {key_data['plan_tier']})")
        print(f"  Tokens: {key_data['tokens_remaining']} / {key_data['tokens_total']}")
        print(f"  Minutes: {key_data['minutes_remaining']} / {key_data['minutes_total']}")
        print(f"  Rate: ₹{key_data['rate_per_min_inr']} / min")
        print(f"  Balance: ₹{key_data['balance_inr']}")
        
        assert key_data['tokens_remaining'] == 550, f"Expected 550 tokens, got {key_data['tokens_remaining']}"
        assert key_data['rate_per_min_inr'] == 2.0, f"Expected rate 2.0, got {key_data['rate_per_min_inr']}"
        assert key_data['minutes_remaining'] == 15.0
        
    # 2. Validate usage of 120 seconds (2.0 minutes) and 10 tokens
    print("\n--- 3. Testing POST /api/keys/validate with 120 sec audio (2 minutes) ---")
    val_url = f"{BASE_URL}/api/keys/validate?cost_tokens=10&duration_sec=120.0"
    req = urllib.request.Request(val_url, data=b"", headers={"x-api-key": raw_key})
    with urllib.request.urlopen(req) as resp:
        val_data = json.loads(resp.read().decode())
        print(f"Status: {val_data['status']}")
        print(f"Minutes Remaining: {val_data['minutes_remaining']} (deducted {val_data['minutes_deducted']} min from 15.0)")
        print(f"Tokens Remaining: {val_data['tokens_remaining']} (deducted {val_data['tokens_deducted']} from 550)")
        assert abs(val_data['minutes_remaining'] - 13.0) < 0.01, f"Expected 13.0, got {val_data['minutes_remaining']}"
        assert val_data['tokens_remaining'] == 540, f"Expected 540, got {val_data['tokens_remaining']}"

    # 3. Top-up 50 minutes (₹100 pack)
    print("\n--- 4. Testing POST /api/keys/topup for 50 Audio Minutes (₹100) ---")
    topup_payload = json.dumps({
        "key_id": key_data["id"],
        "topup_type": "minutes",
        "minutes_to_add": 50.0,
        "price_paid": 100.0,
        "payment_method": "upi_gpay"
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/keys/topup", data=topup_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        topup_res = json.loads(resp.read().decode())
        print(f"Topup Key: {topup_res['id']}")
        print(f"New Minutes: {topup_res['minutes_remaining']}")
        assert abs(topup_res['minutes_remaining'] - 63.0) < 0.01, f"Expected 63.0, got {topup_res['minutes_remaining']}"

    # 4. Top-up 5,000 tokens (₹49 pack)
    print("\n--- 5. Testing POST /api/keys/topup for 5,000 Tokens (₹49) ---")
    topup_payload = json.dumps({
        "key_id": key_data["id"],
        "topup_type": "tokens",
        "tokens_to_add": 5000,
        "price_paid": 49.0,
        "payment_method": "upi_phonepe"
    }).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/keys/topup", data=topup_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        topup_res = json.loads(resp.read().decode())
        print(f"Topup Key: {topup_res['id']}")
        print(f"New Tokens: {topup_res['tokens_remaining']}")
        assert topup_res['tokens_remaining'] == 5540, f"Expected 5540, got {topup_res['tokens_remaining']}"

    # 5. Switch to Enterprise Plan
    print("\n--- 6. Testing Plan Upgrade to ENTERPRISE ---")
    upgrade_payload = json.dumps({"name": "Enterprise Key", "plan_tier": "ENTERPRISE"}).encode()
    req = urllib.request.Request(f"{BASE_URL}/api/keys/generate", data=upgrade_payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        ent_key = json.loads(resp.read().decode())
        print(f"Enterprise Key Generated: {ent_key['key'][:12]}...")
        print(f"  Plan: {ent_key['plan_tier']}")
        print(f"  Tokens: {ent_key['tokens_remaining']}")
        print(f"  Included Minutes: {ent_key['minutes_remaining']}")
        print(f"  Volume Rate: ₹{ent_key['rate_per_min_inr']}/min")
        assert ent_key['plan_tier'] == 'ENTERPRISE'
        assert ent_key['tokens_remaining'] == 50000
        assert ent_key['minutes_remaining'] == 1000.0
        assert ent_key['rate_per_min_inr'] == 1.5

    print("\n>>> ALL BACKEND TESTS PASSED WITH 100% COMPLIANCE! <<<")

if __name__ == "__main__":
    try:
        test_plans_catalog()
        test_api_key_lifecycle()
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
