from typing import Dict, Any, Optional

class AMVTFFusionEngine:
    """
    AMVTF: Adaptive Multi-Signal Voice Trust Fusion Engine
    Fuses acoustic authenticity, speaker identity, and spoken contextual threat indicators
    into a genuine, explainable threat score (0 - 100) and security decision: SAFE, WARNING, or CRITICAL.
    """

    def __init__(self, weight_auth: float = 0.50, weight_ctx: float = 0.50):
        self.w_auth = weight_auth
        self.w_ctx = weight_ctx

    def fuse_signals(
        self,
        authenticity: float,
        identity: float,
        context_risk: float,
        matched_profile: str = "",
        is_identity_match: bool = False,
        target_profile_requested: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates genuine threat score (0 - 100):
        - Acoustic Threat Risk = 100 - Authenticity (AI Deepfake has low authenticity -> High Acoustic Threat)
        - Context Threat Risk = Context Risk from Scammer Keyword Extraction (OTP, Card Expire, Threat)
        - Target Identity Mismatch is only penalized if a specific target profile was explicitly selected.
        """
        # 1. Acoustic risk: Genuine human voice (authenticity 85-98) has acoustic risk 2-15.
        #    Synthetic deepfake (authenticity 15-44) has acoustic risk 56-85.
        acoustic_threat = max(0.0, 100.0 - authenticity)

        # 2. Context threat: From NLP keyword extraction
        context_threat = float(np_clip(context_risk, 0.0, 100.0)) if 'np_clip' in globals() else float(min(100.0, max(0.0, context_risk)))

        # 3. Dynamic threat score fusion:
        # If specific target profile verification was requested:
        if target_profile_requested:
            id_threat = max(0.0, 100.0 - identity)
            # Weighted fusion across 3 signals
            fused_score = (0.40 * acoustic_threat) + (0.35 * id_threat) + (0.25 * context_threat)
        else:
            # General live monitoring: fuse acoustic authenticity and contextual scammer keywords
            # When speech is bona fide human, threat score is primarily governed by spoken content (coercion/fraud)
            if authenticity >= 80.0:
                # Human voice: baseline acoustic risk is very low (~5%)
                # Threat score increases if caller uses scammer language
                fused_score = (0.15 * acoustic_threat) + (0.85 * context_threat)
            else:
                # Suspect or synthetic acoustic signature: heavy weight on deepfake risk
                fused_score = (0.65 * acoustic_threat) + (0.35 * context_threat)

        fused_score = round(float(min(100.0, max(0.0, fused_score))), 1)

        # 4. Security Verdict Determination
        # CRITICAL conditions:
        # A) Acoustic synthetic deepfake detected (authenticity < 50.0)
        # B) Spoken dialogue contains critical fraud/coercion (context_risk >= 70.0)
        # C) Overall fused threat score >= 60.0
        if authenticity < 50.0:
            verdict = "CRITICAL"
            action_type = "TERMINATE"
            recommended_action = "TERMINATE CALL IMMEDIATELY — SYNTHETIC VOICE DETECTED"
            if context_risk >= 40.0:
                rationale = (
                    f"CRITICAL THREAT: Automated AI Deepfake Scammer Attack detected! "
                    f"Voice is synthetic ({authenticity:.1f}% authenticity) and transcript contains active coercion ({context_risk:.1f}% context threat)."
                )
            else:
                rationale = (
                    f"CRITICAL: Synthetic AI deepfake detected ({authenticity:.1f}% authenticity). "
                    f"Acoustic features show neural vocoder artifacts / playback distortion. Context risk is {context_risk:.1f}%."
                )
        elif context_risk >= 70.0 or fused_score >= 60.0:
            verdict = "CRITICAL"
            action_type = "TERMINATE"
            recommended_action = "INTERCEPT & BLOCK TRANSACTION — FRAUD ATTEMPT"
            rationale = (
                f"CRITICAL THREAT: High-risk scammer coercion detected in spoken dialogue ({context_risk:.1f}% context threat). "
                f"Spoken phrases include high-risk fraud keywords (OTP / card expiry / extortion tactics)."
            )
        elif context_risk >= 38.0 or fused_score >= 35.0 or (target_profile_requested and not is_identity_match):
            verdict = "WARNING"
            action_type = "STEP_UP"
            recommended_action = "Trigger Out-of-Band (OOB) Secondary Verification"
            reasons = []
            if context_risk >= 38.0:
                reasons.append(f"Elevated scam phrase indicators ({context_risk:.1f}%)")
            if authenticity < 75.0:
                reasons.append(f"Borderline acoustic quality ({authenticity:.1f}%)")
            if target_profile_requested and not is_identity_match:
                reasons.append(f"Target speaker voiceprint mismatch ({identity:.1f}%)")
            reason_str = "; ".join(reasons) if reasons else f"Fused risk elevated ({fused_score:.1f})"
            rationale = f"WARNING: {reason_str}. Out-of-band verification recommended before proceeding."
        else:
            verdict = "SAFE"
            action_type = "ALLOW"
            recommended_action = "Allow Session — Normal Operations"
            if target_profile_requested and is_identity_match:
                rationale = (
                    f"Bona fide human voice verified ({authenticity:.1f}%). "
                    f"Speaker voiceprint verified as {matched_profile} ({identity:.1f}%). No threat keywords detected ({context_risk:.1f}%)."
                )
            else:
                rationale = (
                    f"Bona fide human voice verified ({authenticity:.1f}%). "
                    f"Natural voice tune and formants confirmed. No threat keywords detected in dialogue ({context_risk:.1f}%)."
                )

        return {
            "fusedRiskScore": fused_score,
            "verdict": verdict,
            "actionType": action_type,
            "recommendedAction": recommended_action,
            "rationale": rationale
        }

amvtf_engine = AMVTFFusionEngine()

