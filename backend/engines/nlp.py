import io
import re
from typing import List, Dict, Any, Optional
import av
import numpy as np
import soundfile as sf
import speech_recognition as sr

# ──────────────────────────────────────────────────────────────────────────────
# THREAT_DICTIONARY — Comprehensive Scammer & Social-Engineering Phrase Bank
# Contains real-world phrases used in phone scams, digital arrest intimidation,
# bank fraud, OTP theft, and remote access extortion.
# ──────────────────────────────────────────────────────────────────────────────
THREAT_DICTIONARY = {
    # ── Digital Arrest & Law Enforcement Impersonation ──
    "digital_arrest": [
        "digital arrest", "digital custody", "cbi officer", "cbi investigation",
        "cbi", "central bureau of investigation", "police officer", "delhi police",
        "mumbai police", "cyber cell", "cyber crime", "enforcement directorate",
        "ed officer", "money laundering", "hawala", "illegal parcel",
        "customs department", "contraband", "narcotics bureau", "drugs in parcel",
        "passport seized", "sim card fraud", "trai notice", "telecom department",
        "supreme court order", "high court warrant", "non-bailable warrant",
        "police inspector", "customs clearance", "parcel detained", "drugs found"
    ],

    # ── OTP & Verification-Code Theft ──
    "otp_fraud": [
        "tell me the otp", "share the otp", "give me the otp", "read the otp",
        "what is the otp", "otp number", "otp code", "verification code",
        "send me the code", "tell me the code", "share the code",
        "read the code", "give me the code", "one time password",
        "confirm the otp", "enter the otp", "type the otp",
        "i need your otp", "otp for verification", "otp has been sent",
        "6 digit code", "4 digit code", "sms code", "mobile code",
        "otp", "6 digit otp", "4 digit otp", "read otp", "tell otp", "share otp"
    ],

    # ── Card & Account Expiry Pressure ──
    "card_expiry": [
        "card will expire", "card is expiring", "card has expired",
        "account will be blocked", "account is blocked", "account suspended",
        "account frozen", "card is blocked", "card blocked", "debit card expire",
        "credit card expire", "card deactivated", "account deactivated",
        "renew your card", "reactivate your card", "update card details",
        "card will be suspended", "account will expire", "kyc expired",
        "kyc update", "kyc verification", "re-kyc", "update your kyc",
        "pan card link", "link your pan", "aadhaar link", "link aadhaar",
        "account will be closed", "account closure", "electricity bill unpaid",
        "power disconnect", "electricity disconnected", "power cut tonight",
        "gas connection disconnected", "subsidy stop"
    ],

    # ── Financial Manipulation & Fraudulent Transfers ──
    "financial_manipulation": [
        "send money", "transfer money", "pay now", "make payment",
        "upi pin", "enter upi pin", "share upi pin", "upi id",
        "google pay", "phonepe", "paytm", "refund process",
        "refund will be credited", "cashback", "lottery", "prize money",
        "you have won", "claim your prize", "insurance claim",
        "loan approved", "pre-approved loan", "credit limit increase",
        "investment opportunity", "guaranteed returns", "double your money",
        "bitcoin", "crypto investment", "trading profit", "collect request",
        "payment request", "scan this qr", "scan qr", "qr code",
        "transfer to safe account", "government safe account", "verification account",
        "security deposit", "lucky draw", "gpay"
    ],

    # ── Credential Theft & Remote Access Tools ──
    "credential_theft": [
        "cvv number", "cvv", "3 digit cvv", "card number", "expiry date",
        "mother maiden name", "date of birth", "social security",
        "aadhaar number", "pan number", "passport number",
        "bank account number", "ifsc code", "pin number",
        "atm pin", "internet banking password", "login password",
        "security question", "secret answer", "confirm your identity",
        "verify your account", "click the link", "download this app",
        "install this app", "remote access", "anydesk", "teamviewer",
        "quicksupport", "rustdesk", "ultraviewer", "screen share", "share your screen"
    ],

    # ── Fear, Intimidation & Coercion ──
    "fear_pressure": [
        "legal action", "arrest warrant", "police complaint",
        "case filed against you", "fir registered", "court notice",
        "jail", "imprisonment", "penalty", "fine will be imposed",
        "your account is hacked", "suspicious activity",
        "unauthorized transaction", "someone accessed your account",
        "money will be lost", "you will lose everything",
        "don't tell anyone", "keep this confidential",
        "don't inform family", "this is confidential",
        "do not disconnect", "stay on the line", "don't hang up",
        "secret investigation", "police will arrive at your home"
    ],

    # ── Urgency & Time Pressure ──
    "urgency": [
        "immediately", "urgent", "crisis", "right now", "hurry", "asap",
        "emergency", "within 5 minutes", "within 10 minutes", "deadline",
        "last chance", "act now", "don't delay", "time is running out",
        "expires today", "only few minutes left", "do it now", "quickly", "fast"
    ],

    # ── Impersonation ──
    "impersonation": [
        "calling from bank", "this is bank", "reserve bank",
        "rbi calling", "income tax department", "tax department",
        "police department", "cyber crime", "customs department",
        "calling from sbi", "calling from hdfc", "calling from icici",
        "calling from axis", "calling from pnb", "microsoft support",
        "apple support", "google support", "tech support", "customer care",
        "fraud department", "security department", "insurance company",
        "telecom company", "electricity department", "gas agency"
    ],

    # ── Bypass / Security Circumvention ──
    "bypass": [
        "bypass protocol", "skip dual-auth", "without triggering escalation",
        "override", "bypass security", "skip verification", "ignore procedure",
        "disable mfa", "bypass 2fa", "turn off security", "remove protection"
    ],

    # ── Executive Authority Pressure ──
    "authority": [
        "ceo requested", "board meeting", "executive order", "director approved",
        "cfo authorized", "vp instructed", "confidential project",
        "manager told me", "supervisor said", "higher authority"
    ],

    # ── High-Risk Asset / Wire Transfer ──
    "sensitive": [
        "wire transfer", "personal email", "personal gmail", "send recovery link",
        "lost 2fa device", "bypass link", "confidential data", "routing number",
        "swift code", "transfer funds", "bank details", "account details"
    ]
}


def convert_to_wav(audio_bytes: bytes) -> bytes:
    """
    Decodes audio bytes from any format (WAV, MP3, WebM, OGG, FLAC, MP4/AAC)
    into standard 16kHz mono 16-bit PCM WAV in memory.
    """
    if not audio_bytes or len(audio_bytes) < 100:
        return b""

    # 1. Try direct soundfile read (fastest for standard wav/ogg/flac)
    try:
        data, sr_in = sf.read(io.BytesIO(audio_bytes))
        out = io.BytesIO()
        sf.write(out, data, sr_in, format='WAV', subtype='PCM_16')
        return out.getvalue()
    except Exception:
        pass

    # 2. PyAV decoder for MP3, WebM, MP4, AAC, etc.
    try:
        inp = io.BytesIO(audio_bytes)
        container = av.open(inp)
        resampler = av.AudioResampler(format='s16', layout='mono', rate=16000)
        frames = []
        for frame in container.decode(audio=0):
            res_frames = resampler.resample(frame)
            if isinstance(res_frames, list):
                for rf in res_frames:
                    frames.append(rf.to_ndarray())
            elif res_frames:
                frames.append(res_frames.to_ndarray())
        if not frames:
            return b""
        audio_arr = np.concatenate(frames, axis=1)
        out = io.BytesIO()
        sf.write(out, audio_arr.squeeze(), 16000, format='WAV', subtype='PCM_16')
        return out.getvalue()
    except Exception as e:
        print(f"[ASR] Error decoding audio bytes: {e}")
        return b""


class ContextualThreatEngine:
    """
    Contextual Threat & Social Engineering Classification Engine.
    Transcribes spoken audio streams and evaluates conversational text against
    scammer phrase dictionaries to extract threat keywords and compute Layer 3 Context Risk.
    """

    # Per-category base score and per-additional-match increment
    CATEGORY_WEIGHTS = {
        "digital_arrest":           (45.0, 15.0, "Digital arrest & law enforcement impersonation"),
        "otp_fraud":                (45.0, 15.0, "OTP / verification-code theft attempt"),
        "card_expiry":              (40.0, 12.0, "Card / account expiry pressure tactic"),
        "impersonation":            (35.0, 10.0, "Authority impersonation detected"),
        "financial_manipulation":   (38.0, 12.0, "Financial manipulation / payment fraud"),
        "credential_theft":         (42.0, 14.0, "Credential / personal-info phishing"),
        "fear_pressure":            (40.0, 12.0, "Fear / threat-based coercion"),
        "urgency":                  (25.0,  8.0, "High urgency coercion detected"),
        "bypass":                   (35.0, 12.0, "Security protocol circumvention request"),
        "authority":                (20.0,  8.0, "Executive authority pressure indicator"),
        "sensitive":                (30.0, 10.0, "High-value asset / credential target"),
    }

    def __init__(self, sensitivity: float = 65.0):
        self.sensitivity = sensitivity

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """
        Extracts spoken words directly from raw audio bytes in any format.
        Tries Indian English (en-IN), Standard English (en-US), and Hindi (hi-IN).
        """
        wav_data = convert_to_wav(audio_bytes)
        if not wav_data:
            return ""

        r = sr.Recognizer()
        r.energy_threshold = 200
        r.dynamic_energy_threshold = True

        try:
            with sr.AudioFile(io.BytesIO(wav_data)) as source:
                audio = r.record(source)

            # Try primary recognition languages
            for lang in ["en-IN", "en-US", "hi-IN"]:
                try:
                    text = r.recognize_google(audio, language=lang)
                    if text and text.strip():
                        print(f"[ASR] Successfully transcribed ({lang}): {text}")
                        return text.strip()
                except Exception:
                    continue
        except Exception as e:
            print(f"[ASR] Speech recognition error: {e}")

        return ""

    def analyze_text(self, text: str = "") -> Dict[str, Any]:
        """
        Dynamically evaluates text/transcript for security threat indicators.
        Returns risk score (0 - 100), detected keywords, semantic flags,
        and intent classification.
        """
        if not text or not text.strip():
            return {
                "contextRisk": 5.0,
                "nlpIntent": "Routine Inquiry / Inactive Conversation",
                "threatKeywords": [],
                "semanticFlags": ["Standard operational baseline"],
                "contextTitle": "Operational Communications Baseline",
            }

        text_lower = text.lower()
        flagged_keywords: List[str] = []
        flags: List[str] = []
        score = 0.0

        # ── Heuristic scoring based on category weights ──
        for category, keywords in THREAT_DICTIONARY.items():
            cat_matches = []
            for kw in keywords:
                # Substring check with word boundary consideration
                if kw in text_lower:
                    cat_matches.append(kw)
                    if kw not in flagged_keywords:
                        flagged_keywords.append(kw)

            if cat_matches:
                base, incr, flag_text = self.CATEGORY_WEIGHTS.get(category, (30.0, 10.0, "Security flag detected"))
                score += base + (len(cat_matches) - 1) * incr
                flags.append(flag_text)

        # ── Multi-category escalation bonus ──
        active_categories = sum(
            1 for cat, kws in THREAT_DICTIONARY.items()
            if any(kw in text_lower for kw in kws)
        )
        if active_categories >= 3:
            score += 15.0
            flags.append(f"Multi-vector attack pattern ({active_categories} categories)")

        # ── Determine intent classification ──
        if not flagged_keywords:
            score = 8.0
            flags = ["Standard operational tone", "Procedural compliance"]
            intent = "Benign Business Communication"
            context_title = "Routine Operational Conversation"
        else:
            score = float(min(100.0, score + 10.0))
            if score >= 70.0:
                intent = "CRITICAL — Active Fraud / Social Engineering Attack"
                context_title = "High-Risk Fraud & Coercion Detected"
            elif score >= 38.0:
                intent = "WARNING — Suspicious Scam / Procedural Deviation"
                context_title = "Elevated Fraud Indicators Detected"
            else:
                intent = "Low-Level Procedural Friction"
                context_title = "Monitored Dialogue with Minor Indicators"

        return {
            "contextRisk": round(score, 1),
            "nlpIntent": intent,
            "threatKeywords": flagged_keywords,
            "semanticFlags": flags,
            "contextTitle": context_title,
        }


nlp_engine = ContextualThreatEngine()
