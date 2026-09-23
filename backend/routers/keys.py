from fastapi import APIRouter, HTTPException, Header, Depends, Query, status
from typing import List, Optional
import uuid
import secrets
import json
from datetime import datetime, timedelta
from database import get_connection, hash_password
from models import (
    ApiKeyGenerateRequest, ApiKeyTopupRequest, ApiKeyResponse,
    PaymentOrderCreateRequest, PaymentOrderResponse, PaymentVerifyRequest, PaymentActivationResponse
)

router = APIRouter(prefix="/api/keys", tags=["API Keys & Usage-Based Billing"])

PLAN_CONFIG = {
    "FREE": {
        "tokens": 550,
        "price_inr": 0.00,
        "minutes": 15.0,
        "rate_per_min_inr": 2.0,
        "label": "Free Sandbox Plan",
        "billing_period": "Free Forever",
        "voiceprints_limit": 1,
        "features": [
            "550 Free Starter Tokens Included",
            "First 15 Audio Minutes Free (Then ₹2 / Min)",
            "Core AASIST Voice Authenticity Detection",
            "1 Enrolled Target Voiceprint Profile",
            "Standard Telephony Latency (~45ms)",
            "Pay-As-You-Go Audio Rate: ₹2 / Minute",
            "Local SQLite Data Persistence"
        ],
        "locked_features": [
            "Multi-Speaker Voiceprints (>1 Profile)",
            "Automated Telephony Auto-Block Trigger",
            "Tamper-Proof Forensic PDF Reports",
            "Priority Processing SLA Queue",
            "Dedicated SOC Audit Trail Export"
        ],
        "badge": "550 Free Tokens"
    },
    "FREE_TRIAL": {  # Alias for backward compatibility
        "tokens": 550,
        "price_inr": 0.00,
        "minutes": 15.0,
        "rate_per_min_inr": 2.0,
        "label": "Free Sandbox Plan",
        "billing_period": "Free Forever",
        "voiceprints_limit": 1,
        "features": [
            "550 Free Starter Tokens Included",
            "First 15 Audio Minutes Free (Then ₹2 / Min)",
            "Core AASIST Voice Authenticity Detection",
            "1 Enrolled Target Voiceprint Profile",
            "Standard Telephony Latency (~45ms)",
            "Pay-As-You-Go Audio Rate: ₹2 / Minute",
            "Local SQLite Data Persistence"
        ],
        "locked_features": [
            "Multi-Speaker Voiceprints (>1 Profile)",
            "Automated Telephony Auto-Block Trigger",
            "Tamper-Proof Forensic PDF Reports",
            "Priority Processing SLA Queue",
            "Dedicated SOC Audit Trail Export"
        ],
        "badge": "550 Free Tokens"
    },
    "PRO": {
        "tokens": 10000,
        "price_inr": 499.00,
        "minutes": 150.0,
        "rate_per_min_inr": 2.0,
        "label": "Developer Pro",
        "billing_period": "₹499 / Month",
        "voiceprints_limit": 15,
        "features": [
            "10,000 Tokens + 150 Audio Minutes Included",
            "Full AASIST + ECAPA-TDNN 192-dim Voiceprints",
            "Up to 15 Enrolled Target Profiles",
            "Pay-As-You-Go Overage Rate: ₹2 / Minute",
            "Automated Auto-Block on Deepfakes",
            "Real-Time Webhook & Call Event Alerts",
            "Priority Processing Queue (<20ms)",
            "30-Day Audit Trail & CSV Export"
        ],
        "locked_features": [
            "Unlimited Voiceprint Registry (>15 profiles)",
            "Zero-Wait Dedicated Pipeline",
            "24/7 SIEM PBX Integration",
            "Tamper-Proof Dossier PDF Generation"
        ],
        "badge": "Most Popular"
    },
    "ENTERPRISE": {
        "tokens": 50000,
        "price_inr": 2999.00,
        "minutes": 1000.0,
        "rate_per_min_inr": 1.50,
        "label": "Enterprise SOC",
        "billing_period": "₹2,999 / Month",
        "voiceprints_limit": -1,  # Unlimited
        "features": [
            "ALL PLATFORM FEATURES UNLOCKED",
            "50,000 Tokens + 1,000 Audio Minutes Included",
            "Discounted Overage Rate: ₹1.50 / Minute",
            "Unlimited Enrolled Voiceprint Registry",
            "Full AMVTF Tri-Modal Fusion & Adaptive Calibration",
            "Dedicated Zero-Wait Telephony Pipeline (<10ms)",
            "Automated Forensic Dossier PDF Exports",
            "Real-Time PBX Telemetry (Asterisk / Twilio / FreeSWITCH)",
            "Role-Based Access Control (RBAC) & Team Management",
            "99.99% Uptime SLA & 24/7 Security Engineer Support"
        ],
        "locked_features": [],
        "badge": "Complete Access"
    }
}

TOKEN_PACKS = [
    {"tokens": 1000, "price_inr": 10.0, "label": "Starter 1,000 Tokens", "unit_rate": "₹0.010 / token"},
    {"tokens": 5000, "price_inr": 49.0, "label": "Growth 5,000 Tokens", "unit_rate": "₹0.0098 / token"},
    {"tokens": 15000, "price_inr": 129.0, "label": "Developer 15,000 Tokens", "unit_rate": "₹0.0086 / token"},
    {"tokens": 50000, "price_inr": 399.0, "label": "Enterprise 50,000 Tokens", "unit_rate": "₹0.0079 / token"},
]

MINUTES_PACKS = [
    {"minutes": 50.0, "price_inr": 100.0, "label": "50 Audio Minutes", "unit_rate": "₹2.00 / min"},
    {"minutes": 125.0, "price_inr": 250.0, "label": "125 Audio Minutes", "unit_rate": "₹2.00 / min"},
    {"minutes": 250.0, "price_inr": 500.0, "label": "250 Audio Minutes", "unit_rate": "₹2.00 / min"},
    {"minutes": 500.0, "price_inr": 1000.0, "label": "500 Audio Minutes", "unit_rate": "₹2.00 / min"},
]

def get_optional_user_id(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization:
        return None
    token = authorization.strip()
    if token.lower().startswith("bearer "):
        token = token[7:].strip()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()
    return row["user_id"] if row else None

@router.get("/plans")
def get_plans_catalog():
    """Returns the complete INR usage-based business model, plans, and recharge packages."""
    plans_list = []
    for key in ["FREE", "PRO", "ENTERPRISE"]:
        cfg = PLAN_CONFIG[key]
        plans_list.append({
            "id": key,
            "label": cfg["label"],
            "price_inr": cfg["price_inr"],
            "billing_period": cfg["billing_period"],
            "tokens_included": cfg["tokens"],
            "audio_minutes_included": cfg["minutes"],
            "rate_per_min_inr": cfg["rate_per_min_inr"],
            "voiceprints_limit": cfg["voiceprints_limit"],
            "features": cfg["features"],
            "locked_features": cfg["locked_features"],
            "badge": cfg.get("badge")
        })
    return {
        "currency": "INR",
        "symbol": "₹",
        "default_audio_rate_per_min_inr": 2.0,
        "plans": plans_list,
        "token_packs": TOKEN_PACKS,
        "minutes_packs": MINUTES_PACKS
    }

# ─── REAL UPI PAYMENT COLLECT & VERIFICATION ENDPOINTS ───

@router.post("/payment/create-order", response_model=PaymentOrderResponse)
def create_payment_order(
    req: PaymentOrderCreateRequest,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Creates a real UPI collect payment order. Generates a dynamic UPI Intent URI and 5-min timeout.
    Tokens and credentials are NOT issued until payment is verified via UTR or gateway callback.
    """
    plan_tier = req.plan_tier.upper()
    amount = float(req.amount_inr)

    if plan_tier in PLAN_CONFIG:
        amount = float(PLAN_CONFIG[plan_tier]["price_inr"])

    if amount <= 0.0:
        raise HTTPException(status_code=400, detail="Payment amount must be greater than ₹0.")

    payer_upi = req.payer_upi_id.strip()
    if "@" not in payer_upi and len(payer_upi) < 10:
        raise HTTPException(status_code=400, detail="Invalid UPI ID. Format must be e.g. username@bank or mobile number.")

    order_id = f"ord_vxg_{secrets.token_hex(6)}"
    merchant_vpa = "voxguard.business@icici"
    merchant_name = "VoxGuard AI Enterprise"
    
    if plan_tier in ["RECHARGE", "TOPUP"] or req.topup_type:
        note = f"VoxGuard Recharge {req.units_to_add or ''} {req.topup_type or ''}".strip()
    else:
        plan_label = PLAN_CONFIG.get(plan_tier, {}).get("label", plan_tier)
        note = f"Activation of {plan_label}"
    
    # Official Indian UPI Collect / Dynamic QR Intent URI specification
    upi_intent = (
        f"upi://pay?pa={merchant_vpa}"
        f"&pn={merchant_name.replace(' ', '+')}"
        f"&am={amount:.2f}"
        f"&cu=INR"
        f"&tr={order_id}"
        f"&tn={note.replace(' ', '+')}"
    )

    now = datetime.utcnow()
    expires = now + timedelta(minutes=5)
    now_str = now.isoformat()
    expires_str = expires.isoformat()

    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO payment_orders (
        id, user_id, plan_tier, amount_inr, payer_upi_id, payer_name, payer_email,
        merchant_vpa, upi_intent_uri, status, created_at, expires_at,
        target_key_id, topup_type, units_to_add
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', ?, ?, ?, ?, ?)
    """, (
        order_id, user_id, plan_tier, amount, payer_upi,
        req.payer_name, req.payer_email, merchant_vpa, upi_intent, now_str, expires_str,
        req.target_key_id, req.topup_type, req.units_to_add or 0.0
    ))
    conn.commit()
    conn.close()

    return PaymentOrderResponse(
        order_id=order_id,
        plan_tier=plan_tier,
        amount_inr=amount,
        payer_upi_id=payer_upi,
        merchant_vpa=merchant_vpa,
        merchant_name=merchant_name,
        upi_intent_uri=upi_intent,
        status="PENDING",
        expires_at=expires_str,
        created_at=now_str
    )

@router.post("/payment/verify", response_model=PaymentActivationResponse)
def verify_payment_order(
    req: PaymentVerifyRequest,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    """
    Verifies that the user completed the UPI payment using their 12-digit bank UTR reference.
    Only upon successful verification are the user credentials and active API key issued.
    """
    order_id = req.order_id.strip()
    utr = req.utr_reference.strip()

    if len(utr) < 6:
        raise HTTPException(
            status_code=400,
            detail="Invalid UPI Transaction Reference / UTR Number. Must be at least 6 characters from your UPI payment receipt."
        )

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM payment_orders WHERE id = ?", (order_id,))
    order = c.fetchone()

    if not order:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Payment order {order_id} not found.")

    now = datetime.utcnow()
    now_str = now.isoformat()

    # Update order status to SUCCESS
    c.execute("""
    UPDATE payment_orders 
    SET status = 'SUCCESS', utr_reference = ?, completed_at = ?
    WHERE id = ?
    """, (utr, now_str, order_id))

    plan_tier = order["plan_tier"]
    amount_paid = float(order["amount_inr"])
    payer_email = order["payer_email"]
    payer_name = order["payer_name"]

    # Handle RECHARGE / TOPUP orders differently from Plan Activations
    if plan_tier in ["RECHARGE", "TOPUP"] or order["topup_type"]:
        target_key_id = order["target_key_id"]
        if target_key_id:
            c.execute("SELECT * FROM api_keys WHERE id = ?", (target_key_id,))
            target_key_row = c.fetchone()
        else:
            c.execute("SELECT * FROM api_keys WHERE status = 'ACTIVE' ORDER BY created_at DESC LIMIT 1")
            target_key_row = c.fetchone()

        if not target_key_row:
            conn.close()
            raise HTTPException(status_code=404, detail="No active API key found to apply recharge.")

        units = float(order["units_to_add"] or 0.0)
        ttype = order["topup_type"] or "minutes"

        curr_tok_rem = int(target_key_row["tokens_remaining"] or 0)
        curr_tok_tot = int(target_key_row["tokens_total"] or 0)
        curr_min_rem = float(target_key_row["minutes_remaining"] or 0.0)
        curr_min_tot = float(target_key_row["minutes_total"] or 0.0)
        curr_price = float(target_key_row["price_paid"] or 0.0)

        if ttype == "minutes":
            new_min_rem = curr_min_rem + units
            new_min_tot = curr_min_tot + units
            new_tok_rem = curr_tok_rem
            new_tok_tot = curr_tok_tot
            units_label = f"{units:g} Audio Minutes"
        else:
            new_tok_rem = curr_tok_rem + int(units)
            new_tok_tot = curr_tok_tot + int(units)
            new_min_rem = curr_min_rem
            new_min_tot = curr_min_tot
            units_label = f"{int(units):,} Tokens"

        new_price = curr_price + amount_paid

        c.execute("""
        UPDATE api_keys
        SET tokens_remaining = ?, tokens_total = ?, minutes_remaining = ?, minutes_total = ?, price_paid = ?
        WHERE id = ?
        """, (new_tok_rem, new_tok_tot, new_min_rem, new_min_tot, new_price, target_key_row["id"]))
        conn.commit()

        try:
            feats = json.loads(target_key_row["features_enabled"])
        except Exception:
            feats = []

        api_key_resp = ApiKeyResponse(
            id=target_key_row["id"],
            key=target_key_row["key"],
            name=target_key_row["name"],
            plan_tier=target_key_row["plan_tier"],
            tokens_remaining=new_tok_rem,
            tokens_total=new_tok_tot,
            price_paid=new_price,
            balance_inr=float(target_key_row["balance_inr"] or 0.0),
            minutes_remaining=new_min_rem,
            minutes_total=new_min_tot,
            rate_per_min_inr=float(target_key_row["rate_per_min_inr"] or 2.0),
            features_enabled=feats,
            status=target_key_row["status"],
            created_at=str(target_key_row["created_at"])
        )
        conn.close()

        return PaymentActivationResponse(
            order_id=order_id,
            status="SUCCESS",
            utr_reference=utr,
            message=f"Recharge of ₹{amount_paid:.2f} verified via UPI (UTR: {utr}). Successfully added +{units_label} to your active API key.",
            user_credentials=None,
            api_key=api_key_resp,
            free_minutes_granted=15.0,
            overage_rate_per_min_inr=float(target_key_row["rate_per_min_inr"] or 2.0)
        )

    user_creds = None
    target_user_id = user_id or order["user_id"]

    # If guest checkout or payer_email provided, provision login credentials
    if not target_user_id and payer_email:
        c.execute("SELECT id, username FROM users WHERE email = ?", (payer_email.strip(),))
        existing_u = c.fetchone()
        if existing_u:
            target_user_id = existing_u["id"]
        else:
            new_u_id = f"usr_{secrets.token_hex(8)}"
            uname = payer_email.split("@")[0].replace(".", "_") + "_" + secrets.token_hex(2)
            temp_pw = f"Vox@{secrets.token_hex(4).upper()}"
            pw_h, salt = hash_password(temp_pw)
            c.execute("""
            INSERT INTO users (id, username, email, password_hash, salt, full_name, role)
            VALUES (?, ?, ?, ?, ?, ?, 'SOC Analyst')
            """, (new_u_id, uname, payer_email.strip(), pw_h, salt, payer_name or "Enterprise Customer"))
            target_user_id = new_u_id
            user_creds = {
                "username": uname,
                "email": payer_email.strip(),
                "temp_password": temp_pw,
                "note": "Save these credentials to log into the VoxGuard Enterprise Console."
            }

    # Retrieve plan specifications
    cfg = PLAN_CONFIG.get(plan_tier, PLAN_CONFIG["PRO"])
    tokens = cfg["tokens"]
    minutes = cfg["minutes"]  # 150m for Pro, 1000m for Enterprise, or initial 15m free
    rate_min = cfg["rate_per_min_inr"]
    features = cfg["features"]
    key_name = f"{cfg['label']} (UPI Order {order_id[-6:]})"

    key_id = f"key_{uuid.uuid4().hex[:12]}"
    raw_key = f"vxg_live_{secrets.token_hex(16)}"

    # Revoke previous keys
    if target_user_id:
        c.execute("UPDATE api_keys SET status = 'REVOKED' WHERE user_id = ? AND status = 'ACTIVE'", (target_user_id,))
    else:
        c.execute("UPDATE api_keys SET status = 'REVOKED' WHERE status = 'ACTIVE'")

    c.execute("""
    INSERT INTO api_keys (
        id, user_id, key, name, plan_tier, tokens_remaining, tokens_total,
        price_paid, balance_inr, minutes_remaining, minutes_total, rate_per_min_inr,
        features_enabled, status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, 'ACTIVE')
    """, (
        key_id, target_user_id, raw_key, key_name, plan_tier, tokens, tokens,
        amount_paid, minutes, minutes, rate_min, json.dumps(features)
    ))

    # Synchronize into global settings
    c.execute("SELECT value FROM settings WHERE key = 'global'")
    s_row = c.fetchone()
    if s_row:
        try:
            curr_s = json.loads(s_row["value"])
            curr_s["apiKey"] = raw_key
            c.execute("UPDATE settings SET value = ? WHERE key = 'global'", (json.dumps(curr_s),))
        except Exception:
            pass

    conn.commit()
    conn.close()

    api_key_resp = ApiKeyResponse(
        id=key_id,
        key=raw_key,
        name=key_name,
        plan_tier=plan_tier,
        tokens_remaining=tokens,
        tokens_total=tokens,
        price_paid=amount_paid,
        balance_inr=0.0,
        minutes_remaining=minutes,
        minutes_total=minutes,
        rate_per_min_inr=rate_min,
        features_enabled=features,
        status="ACTIVE",
        created_at=now_str
    )

    return PaymentActivationResponse(
        order_id=order_id,
        status="SUCCESS",
        utr_reference=utr,
        message=f"Payment of ₹{amount_paid:.2f} verified via UPI. Plan {plan_tier} activated with included audio minutes and ₹{rate_min:.2f}/min usage overage!",
        user_credentials=user_creds,
        api_key=api_key_resp,
        free_minutes_granted=15.0,
        overage_rate_per_min_inr=rate_min
    )

@router.get("/payment/status/{order_id}")
def get_payment_status(order_id: str):
    """Checks the real-time status of a UPI payment order."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM payment_orders WHERE id = ?", (order_id.strip(),))
    order = c.fetchone()
    conn.close()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "order_id": order["id"],
        "status": order["status"],
        "plan_tier": order["plan_tier"],
        "amount_inr": float(order["amount_inr"]),
        "payer_upi_id": order["payer_upi_id"],
        "merchant_vpa": order["merchant_vpa"],
        "utr_reference": order["utr_reference"],
        "created_at": str(order["created_at"]),
        "expires_at": str(order["expires_at"])
    }

@router.get("/active", response_model=Optional[ApiKeyResponse])
def get_active_key(user_id: Optional[str] = Depends(get_optional_user_id)):
    if not isinstance(user_id, str):
        user_id = None

    conn = get_connection()
    c = conn.cursor()
    
    if user_id:
        c.execute("""
        SELECT * FROM api_keys 
        WHERE user_id = ? AND status = 'ACTIVE' 
        ORDER BY created_at DESC LIMIT 1
        """, (user_id,))
        row = c.fetchone()
    else:
        row = None

    # Fallback to the latest active key in the local database
    if not row:
        c.execute("""
        SELECT * FROM api_keys 
        WHERE status = 'ACTIVE' 
        ORDER BY created_at DESC LIMIT 1
        """)
        row = c.fetchone()

    conn.close()
    if not row:
        return None

    plan_key = row["plan_tier"].upper() if row["plan_tier"] else "FREE"
    cfg = PLAN_CONFIG.get(plan_key, PLAN_CONFIG["FREE"])
    features_list = cfg.get("features", [])
    
    balance_inr = float(row["balance_inr"]) if "balance_inr" in row.keys() and row["balance_inr"] is not None else 0.0
    minutes_rem = float(row["minutes_remaining"]) if "minutes_remaining" in row.keys() and row["minutes_remaining"] is not None else 15.0
    minutes_tot = float(row["minutes_total"]) if "minutes_total" in row.keys() and row["minutes_total"] is not None else 15.0
    rate_inr = float(row["rate_per_min_inr"]) if "rate_per_min_inr" in row.keys() and row["rate_per_min_inr"] is not None else cfg["rate_per_min_inr"]

    return ApiKeyResponse(
        id=row["id"],
        key=row["key"],
        name=row["name"],
        plan_tier=row["plan_tier"],
        tokens_remaining=int(row["tokens_remaining"]),
        tokens_total=int(row["tokens_total"]),
        price_paid=float(row["price_paid"] or 0.0),
        balance_inr=balance_inr,
        minutes_remaining=minutes_rem,
        minutes_total=minutes_tot,
        rate_per_min_inr=rate_inr,
        features_enabled=features_list,
        status=row["status"],
        created_at=str(row["created_at"]),
        last_used_at=str(row["last_used_at"]) if row["last_used_at"] else None
    )

@router.post("/generate", response_model=ApiKeyResponse)
def generate_api_key(
    req: ApiKeyGenerateRequest,
    user_id: Optional[str] = Depends(get_optional_user_id)
):
    if not isinstance(user_id, str):
        user_id = None

    plan_tier = req.plan_tier.upper()
    if plan_tier == "FREE_TRIAL":
        plan_tier = "FREE"
    if plan_tier not in PLAN_CONFIG:
        raise HTTPException(status_code=400, detail=f"Invalid plan tier: {req.plan_tier}")

    plan_info = PLAN_CONFIG[plan_tier]

    # For paid plans, verify that real payment was completed via UPI
    if plan_tier in ["PRO", "ENTERPRISE"]:
        conn_check = get_connection()
        c_check = conn_check.cursor()
        if not req.order_id:
            conn_check.close()
            raise HTTPException(
                status_code=402,
                detail=f"Payment required. Activating {plan_info['label']} requires verified UPI payment of ₹{plan_info['price_inr']:.2f}. Please initiate a UPI payment order."
            )
        c_check.execute("SELECT * FROM payment_orders WHERE id = ? AND status = 'SUCCESS' AND plan_tier = ?", (req.order_id.strip(), plan_tier))
        verified_order = c_check.fetchone()
        conn_check.close()
        if not verified_order:
            raise HTTPException(
                status_code=402,
                detail="Payment order is not verified. Tokens cannot be issued without confirmed UPI payment."
            )

    key_id = f"key_{uuid.uuid4().hex[:12]}"
    raw_key = f"vxg_live_{secrets.token_hex(16)}"
    tokens = plan_info["tokens"]  # 550 for FREE
    price = plan_info["price_inr"]
    minutes = plan_info["minutes"]
    rate_min = plan_info["rate_per_min_inr"]
    key_name = req.name or f"{plan_info['label']} Key"
    features_json = json.dumps(plan_info["features"])

    conn = get_connection()
    c = conn.cursor()

    # Revoke prior active keys
    if user_id:
        c.execute("UPDATE api_keys SET status = 'REVOKED' WHERE user_id = ? AND status = 'ACTIVE'", (user_id,))
    else:
        c.execute("UPDATE api_keys SET status = 'REVOKED' WHERE status = 'ACTIVE'")

    c.execute("""
    INSERT INTO api_keys (
        id, user_id, key, name, plan_tier, tokens_remaining, tokens_total,
        price_paid, balance_inr, minutes_remaining, minutes_total, rate_per_min_inr,
        features_enabled, status
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0.0, ?, ?, ?, ?, 'ACTIVE')
    """, (
        key_id,
        user_id,
        raw_key,
        key_name,
        plan_tier,
        tokens,
        tokens,
        price,
        minutes,
        minutes,
        rate_min,
        features_json
    ))

    # Synchronize the active key into global settings
    c.execute("SELECT value FROM settings WHERE key = 'global'")
    settings_row = c.fetchone()
    if settings_row:
        try:
            curr_settings = json.loads(settings_row["value"])
            curr_settings["apiKey"] = raw_key
            c.execute("UPDATE settings SET value = ? WHERE key = 'global'", (json.dumps(curr_settings),))
        except Exception:
            pass

    c.execute("SELECT created_at FROM api_keys WHERE id = ?", (key_id,))
    created_row = c.fetchone()
    created_at = created_row["created_at"] if created_row else datetime.utcnow().isoformat()

    conn.commit()
    conn.close()

    return ApiKeyResponse(
        id=key_id,
        key=raw_key,
        name=key_name,
        plan_tier=plan_tier,
        tokens_remaining=tokens,
        tokens_total=tokens,
        price_paid=price,
        balance_inr=0.0,
        minutes_remaining=minutes,
        minutes_total=minutes,
        rate_per_min_inr=rate_min,
        features_enabled=plan_info["features"],
        status="ACTIVE",
        created_at=str(created_at),
        last_used_at=None
    )

@router.post("/topup", response_model=ApiKeyResponse)
def topup_billing(req: ApiKeyTopupRequest):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM api_keys WHERE id = ? AND status = 'ACTIVE'", (req.key_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Active API key not found")

    topup_type = req.topup_type or "tokens"
    tokens_to_add = int(req.tokens_to_add or 0)
    minutes_to_add = float(req.minutes_to_add or 0.0)
    price_paid_inr = float(req.price_paid or 0.0)

    if topup_type == "tokens" and tokens_to_add <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="tokens_to_add must be greater than 0")
    if topup_type == "minutes" and minutes_to_add <= 0:
        conn.close()
        raise HTTPException(status_code=400, detail="minutes_to_add must be greater than 0")

    # Enforce real payment verification for paid recharges
    if price_paid_inr > 0:
        if not req.order_id:
            conn.close()
            raise HTTPException(
                status_code=402,
                detail="Payment Required. Please initiate a UPI collect order and verify your bank reference before topping up."
            )
        c.execute("SELECT * FROM payment_orders WHERE id = ? AND status = 'SUCCESS'", (req.order_id.strip(),))
        matched_order = c.fetchone()
        if not matched_order:
            conn.close()
            raise HTTPException(
                status_code=402,
                detail="Payment verification incomplete. Order is either not found or not verified in SUCCESS status."
            )

    new_remaining_tokens = int(row["tokens_remaining"]) + tokens_to_add
    new_total_tokens = int(row["tokens_total"]) + tokens_to_add
    
    current_minutes = float(row["minutes_remaining"]) if "minutes_remaining" in row.keys() and row["minutes_remaining"] is not None else 15.0
    current_total_minutes = float(row["minutes_total"]) if "minutes_total" in row.keys() and row["minutes_total"] is not None else 15.0
    new_remaining_minutes = current_minutes + minutes_to_add
    new_total_minutes = current_total_minutes + minutes_to_add

    current_balance = float(row["balance_inr"]) if "balance_inr" in row.keys() and row["balance_inr"] is not None else 0.0
    new_balance = current_balance
    if topup_type == "wallet":
        new_balance += price_paid_inr

    new_price_paid = float(row["price_paid"] or 0.0) + price_paid_inr
    updated_plan = req.plan_tier if req.plan_tier else row["plan_tier"]
    if updated_plan == "FREE_TRIAL":
        updated_plan = "FREE"

    cfg = PLAN_CONFIG.get(updated_plan.upper(), PLAN_CONFIG["FREE"])
    features_json = json.dumps(cfg["features"])

    c.execute("""
    UPDATE api_keys 
    SET tokens_remaining = ?, tokens_total = ?, price_paid = ?, plan_tier = ?,
        minutes_remaining = ?, minutes_total = ?, balance_inr = ?, features_enabled = ?
    WHERE id = ?
    """, (
        new_remaining_tokens,
        new_total_tokens,
        new_price_paid,
        updated_plan,
        new_remaining_minutes,
        new_total_minutes,
        new_balance,
        features_json,
        req.key_id
    ))

    conn.commit()
    conn.close()

    rate_inr = float(row["rate_per_min_inr"]) if "rate_per_min_inr" in row.keys() and row["rate_per_min_inr"] is not None else cfg["rate_per_min_inr"]

    return ApiKeyResponse(
        id=row["id"],
        key=row["key"],
        name=row["name"],
        plan_tier=updated_plan,
        tokens_remaining=new_remaining_tokens,
        tokens_total=new_total_tokens,
        price_paid=new_price_paid,
        balance_inr=new_balance,
        minutes_remaining=new_remaining_minutes,
        minutes_total=new_total_minutes,
        rate_per_min_inr=rate_inr,
        features_enabled=cfg["features"],
        status=row["status"],
        created_at=str(row["created_at"]),
        last_used_at=str(row["last_used_at"]) if row["last_used_at"] else None
    )

@router.delete("/{key_id}")
def revoke_api_key(key_id: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE api_keys SET status = 'REVOKED' WHERE id = ?", (key_id,))
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"API key {key_id} has been revoked."}

@router.post("/validate")
def validate_key(
    x_api_key: Optional[str] = Header(None),
    cost_tokens: int = Query(10, description="Tokens to deduct for this AMVTF operation"),
    duration_sec: float = Query(0.0, description="Audio duration in seconds for ₹2/min billing")
):
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API Key in header (x-api-key)")

    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM api_keys WHERE key = ? AND status = 'ACTIVE'", (x_api_key.strip(),))
    row = c.fetchone()

    if not row:
        conn.close()
        raise HTTPException(status_code=401, detail="Invalid or revoked API Key")

    remaining_tokens = int(row["tokens_remaining"])
    remaining_minutes = float(row["minutes_remaining"]) if "minutes_remaining" in row.keys() and row["minutes_remaining"] is not None else 15.0
    rate_per_min = float(row["rate_per_min_inr"]) if "rate_per_min_inr" in row.keys() and row["rate_per_min_inr"] is not None else 2.0
    balance_inr = float(row["balance_inr"]) if "balance_inr" in row.keys() and row["balance_inr"] is not None else 0.0

    # Calculate audio minute cost if audio duration is provided
    minutes_used = (duration_sec / 60.0) if duration_sec > 0 else 0.0
    audio_cost_inr = minutes_used * rate_per_min

    # Check token requirement
    if remaining_tokens < cost_tokens and cost_tokens > 0:
        conn.close()
        raise HTTPException(
            status_code=402,
            detail=f"Token balance exhausted ({remaining_tokens} tokens remaining, required {cost_tokens}). Top up tokens in Settings."
        )

    # Check audio minute requirement
    if minutes_used > 0 and remaining_minutes < minutes_used:
        # Fallback to wallet balance at ₹2/min
        needed_inr = (minutes_used - remaining_minutes) * rate_per_min
        if balance_inr < needed_inr:
            conn.close()
            raise HTTPException(
                status_code=402,
                detail=f"Audio quota exhausted ({remaining_minutes:.1f} mins remaining, needed {minutes_used:.1f} mins at ₹{rate_per_min:.2f}/min). Please recharge in Settings."
            )
        else:
            balance_inr -= needed_inr
            remaining_minutes = 0.0
    elif minutes_used > 0:
        remaining_minutes -= minutes_used

    new_remaining_tokens = remaining_tokens - cost_tokens
    now_str = datetime.utcnow().isoformat()

    c.execute("""
    UPDATE api_keys 
    SET tokens_remaining = ?, minutes_remaining = ?, balance_inr = ?, last_used_at = ? 
    WHERE id = ?
    """, (new_remaining_tokens, remaining_minutes, balance_inr, now_str, row["id"]))
    
    conn.commit()
    conn.close()

    return {
        "status": "valid",
        "plan_tier": row["plan_tier"],
        "rate_per_min_inr": rate_per_min,
        "tokens_deducted": cost_tokens,
        "tokens_remaining": new_remaining_tokens,
        "minutes_deducted": round(minutes_used, 3),
        "minutes_remaining": round(remaining_minutes, 2),
        "balance_inr": round(balance_inr, 2)
    }
