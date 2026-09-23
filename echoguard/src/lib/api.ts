const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export interface AuthUser {
  id: string;
  username: string;
  email: string;
  full_name: string;
  role: string;
  created_at?: string;
}

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterCredentials {
  username: string;
  email: string;
  password: string;
  full_name: string;
  role?: string;
}

export interface AuthResponse {
  user: AuthUser;
  token: string;
  expires_at: string;
}

export interface CallRecord {
  id: string;
  caller: string;
  agent: string;
  date: string;
  time: string;
  duration: string;
  verdict: "SAFE" | "WARNING" | "CRITICAL";
  authenticity: number;
  identity: number;
  context: string;
  flaggedPhrases: string[];
}

export interface VoiceProfile {
  id: string;
  name: string;
  department: string;
  enrolledDate: string;
  lastVerified: string;
  samples: number;
  confidence: number;
  status: "ACTIVE" | "PENDING" | "REVOKED";
  embeddingQuality: "HIGH" | "MEDIUM" | "LOW";
}

export interface SystemSettings {
  aasistThreshold: number;
  ecapaThreshold: number;
  nlpSensitivity: number;
  emailAlerts: boolean;
  slackAlerts: boolean;
  criticalOnly: boolean;
  autoBlock: boolean;
  apiKey?: string;
  webhookUrl?: string;
}

export interface TranscriptMessage {
  speaker: string;
  text: string;
  time: string;
  alert?: boolean;
  threatKeywords?: string[];
}

export interface AudioAnalysisResponse {
  callerName: string;
  enrolledTarget: string;
  contextTitle: string;
  authenticity: number;
  identity: number;
  contextRisk: number;
  fusedRiskScore: number;
  authStatus: string;
  idStatus: string;
  nlpIntent: string;
  threatKeywords: string[];
  semanticFlags: string[];
  recommendedAction: string;
  actionType: "ALLOW" | "STEP_UP" | "TERMINATE";
  rationale: string;
  transcript: TranscriptMessage[];
  spectralEntropy?: number;
  zcr?: number;
  jitter?: number;
  kurtosis?: number;
  syntheticIndicators?: string[];
}

// ─── API CLIENT FUNCTIONS ───

export async function getCalls(verdict?: string, search?: string): Promise<CallRecord[]> {
  const params = new URLSearchParams();
  if (verdict && verdict !== "ALL") params.append("verdict", verdict);
  if (search) params.append("search", search);

  const res = await fetch(`${API_BASE}/api/calls?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch calls from database");
  return res.json();
}

export async function saveCall(call: Omit<CallRecord, "id" | "date" | "time">): Promise<CallRecord> {
  const res = await fetch(`${API_BASE}/api/calls`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      caller: call.caller,
      agent: call.agent,
      duration: call.duration,
      verdict: call.verdict,
      authenticity: call.authenticity,
      identity: call.identity,
      context: call.context,
      flagged_phrases: call.flaggedPhrases,
    }),
  });
  if (!res.ok) throw new Error("Failed to persist call record");
  return res.json();
}

export async function deleteCall(callId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/calls/${callId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete call record");
}

export async function clearAllCalls(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/calls/all`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to clear calls");
}

export async function getIdentities(status?: string, search?: string): Promise<VoiceProfile[]> {
  const params = new URLSearchParams();
  if (status && status !== "ALL") params.append("status", status);
  if (search) params.append("search", search);

  const res = await fetch(`${API_BASE}/api/identities?${params.toString()}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch identities from database");
  return res.json();
}

export async function enrollVoiceprint(name: string, department: string): Promise<VoiceProfile> {
  const res = await fetch(`${API_BASE}/api/identities`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, department }),
  });
  if (!res.ok) throw new Error("Failed to enroll voiceprint");
  return res.json();
}

export async function enrollVoiceWithAudio(name: string, department: string, audioFile: File | Blob): Promise<VoiceProfile> {
  const formData = new FormData();
  formData.append("name", name);
  formData.append("department", department);
  formData.append("audio", audioFile);

  const res = await fetch(`${API_BASE}/api/identities/enroll-audio`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to enroll voice with audio");
  return res.json();
}

export async function deleteIdentity(profileId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/identities/${profileId}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete identity");
}

export async function clearAllIdentities(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/identities/all`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to clear identities");
}

export async function getSettings(): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch settings from database");
  return res.json();
}

export async function updateSettings(settings: SystemSettings): Promise<SystemSettings> {
  const res = await fetch(`${API_BASE}/api/settings`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error("Failed to update settings");
  return res.json();
}

export async function analyzeAudioUpload(
  file: File | Blob,
  transcript?: string,
  targetProfileId?: string
): Promise<AudioAnalysisResponse> {
  const formData = new FormData();
  formData.append("file", file, file instanceof File ? file.name : "recording.wav");
  if (transcript) formData.append("transcript", transcript);
  if (targetProfileId) formData.append("target_profile_id", targetProfileId);

  const res = await fetch(`${API_BASE}/api/analyze/audio`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to process audio file with AMVTF engine");
  return res.json();
}

export async function analyzeLiveMic(
  transcript: string,
  targetProfileId?: string,
  audioBlob?: Blob
): Promise<AudioAnalysisResponse> {
  const formData = new FormData();
  formData.append("transcript", transcript);
  if (targetProfileId) formData.append("target_profile_id", targetProfileId);
  if (audioBlob) formData.append("audio", audioBlob, "mic_stream.wav");

  const res = await fetch(`${API_BASE}/api/analyze/live`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) throw new Error("Failed to analyze live stream with AMVTF engine");
  return res.json();
}

// ─── AUTHENTICATION API (LOCAL SQLITE DATABASE ONLY) ───

const AUTH_TOKEN_KEY = "voxguard_auth_token";

export function getStoredToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(AUTH_TOKEN_KEY, token);
}

export function clearStoredToken(): void {
  if (typeof window === "undefined") return;
  localStorage.removeItem(AUTH_TOKEN_KEY);
}

export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Authentication failed. Check your credentials.");
  }

  const data: AuthResponse = await res.json();
  setStoredToken(data.token);
  return data;
}

export async function register(credentials: RegisterCredentials): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(credentials),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Registration failed. Please check inputs.");
  }

  const data: AuthResponse = await res.json();
  setStoredToken(data.token);
  return data;
}

export async function getCurrentUser(tokenOverride?: string): Promise<AuthUser> {
  const token = tokenOverride || getStoredToken();
  if (!token) {
    throw new Error("No active session token found");
  }

  const res = await fetch(`${API_BASE}/api/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    clearStoredToken();
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Session invalid or expired");
  }

  return res.json();
}

export async function logout(): Promise<void> {
  const token = getStoredToken();
  if (token) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
    } catch {
      // Ignore network errors on logout
    }
  }
  clearStoredToken();
}

// ─── API KEYS & USAGE-BASED BILLING (INR) ───

export interface ApiKeyRecord {
  id: string;
  key: string;
  name: string;
  plan_tier: string;
  tokens_remaining: number;
  tokens_total: number;
  price_paid: number; // in INR (₹)
  balance_inr?: number; // wallet balance in INR (₹)
  minutes_remaining?: number; // audio minutes
  minutes_total?: number;
  rate_per_min_inr?: number; // ₹2.00 / min
  features_enabled?: string[];
  status: "ACTIVE" | "REVOKED";
  created_at: string;
  last_used_at?: string | null;
}

export interface PlanDetail {
  id: string;
  label: string;
  price_inr: number;
  billing_period: string;
  tokens_included: number;
  audio_minutes_included: number;
  rate_per_min_inr: number;
  voiceprints_limit: number;
  features: string[];
  locked_features: string[];
  badge?: string;
}

export interface PlansCatalog {
  currency: string;
  symbol: string;
  default_audio_rate_per_min_inr: number;
  plans: PlanDetail[];
  token_packs: { tokens: number; price_inr: number; label: string; unit_rate: string }[];
  minutes_packs: { minutes: number; price_inr: number; label: string; unit_rate: string }[];
}

export interface GenerateKeyPayload {
  plan_tier: string;
  name?: string;
  payment_method?: string;
  card_last4?: string;
  upi_id?: string;
}

export interface TopupKeyPayload {
  key_id: string;
  topup_type?: "tokens" | "minutes" | "wallet";
  tokens_to_add?: number;
  minutes_to_add?: number;
  price_paid: number;
  plan_tier?: string;
  payment_method?: string;
}

export async function getPlansCatalog(): Promise<PlansCatalog> {
  const res = await fetch(`${API_BASE}/api/keys/plans`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch plans catalog");
  return res.json();
}

export async function getActiveApiKey(): Promise<ApiKeyRecord | null> {
  const token = getStoredToken();
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  try {
    const res = await fetch(`${API_BASE}/api/keys/active`, {
      headers,
      cache: "no-store",
    });
    if (res.status === 404 || !res.ok) {
      return null;
    }
    return await res.json();
  } catch (err) {
    console.warn("Could not fetch active API key from backend:", err);
    return null;
  }
}

export async function generateApiKey(payload: GenerateKeyPayload): Promise<ApiKeyRecord> {
  const token = getStoredToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/keys/generate`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to generate API Key");
  }
  return res.json();
}

export async function topupApiKey(payload: TopupKeyPayload): Promise<ApiKeyRecord> {
  const token = getStoredToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/keys/topup`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to recharge API Key");
  }
  return res.json();
}

export async function revokeApiKey(keyId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/keys/${keyId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to revoke API Key");
}

// ─── REAL UPI PAYMENT ORDERS & VERIFICATION ───

export interface PaymentOrderRecord {
  order_id: string;
  plan_tier: string;
  amount_inr: number;
  payer_upi_id: string;
  merchant_vpa: string;
  merchant_name: string;
  upi_intent_uri: string;
  status: "PENDING" | "SUCCESS" | "FAILED" | "EXPIRED";
  expires_at: string;
  created_at: string;
}

export interface PaymentActivationResult {
  order_id: string;
  status: string;
  utr_reference: string;
  message: string;
  user_credentials?: {
    username: string;
    email: string;
    temp_password: string;
    note?: string;
  };
  api_key: ApiKeyRecord;
  free_minutes_granted: number;
  overage_rate_per_min_inr: number;
}

export async function createPaymentOrder(
  planTier: string,
  amountInr: number,
  payerUpiId: string,
  payerName?: string,
  payerEmail?: string,
  targetKeyId?: string,
  topupType?: "minutes" | "tokens",
  unitsToAdd?: number
): Promise<PaymentOrderRecord> {
  const token = getStoredToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/keys/payment/create-order`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      plan_tier: planTier,
      amount_inr: amountInr,
      payer_upi_id: payerUpiId,
      payer_name: payerName,
      payer_email: payerEmail,
      target_key_id: targetKeyId,
      topup_type: topupType,
      units_to_add: unitsToAdd,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to initiate UPI collect order");
  }
  return res.json();
}

export async function verifyPaymentOrder(
  orderId: string,
  utrReference: string
): Promise<PaymentActivationResult> {
  const token = getStoredToken();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}/api/keys/payment/verify`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      order_id: orderId,
      utr_reference: utrReference,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to verify UPI payment");
  }
  return res.json();
}

export async function getPaymentOrderStatus(orderId: string): Promise<PaymentOrderRecord> {
  const res = await fetch(`${API_BASE}/api/keys/payment/status/${orderId}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to query order status");
  return res.json();
}



