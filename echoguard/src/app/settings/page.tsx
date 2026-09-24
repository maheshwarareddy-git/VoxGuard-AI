"use client";

import { useState, useEffect } from "react";
import {
  Bell,
  ChevronRight,
  Save,
  Sliders,
  Bell as BellIcon,
  Key,
  Globe,
  AlertTriangle,
  ToggleLeft,
  ToggleRight,
  CheckCircle2,
  RefreshCw,
  Copy,
  Eye,
  EyeOff,
  Sparkles,
  CreditCard,
  Coins,
  Check,
  Zap,
  ShieldCheck,
  X,
  Trash2,
  Lock,
  ArrowRight,
  Clock,
  Wallet,
  CheckCircle,
  HelpCircle,
  QrCode,
  Smartphone,
  ExternalLink,
  KeyRound,
  UserCheck,
  ShieldAlert
} from "lucide-react";
import { QRCodeSVG } from "qrcode.react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  getSettings,
  updateSettings,
  getActiveApiKey,
  generateApiKey,
  topupApiKey,
  revokeApiKey,
  createPaymentOrder,
  verifyPaymentOrder,
  getPaymentOrderStatus,
  ApiKeyRecord,
  PaymentOrderRecord,
  PaymentActivationResult
} from "@/lib/api";

type SettingsSection = "thresholds" | "notifications" | "api" | "general";

export default function SettingsPage() {
  const [activeSection, setActiveSection] = useState<SettingsSection>("thresholds");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  // Form states
  const [aasistThreshold, setAasistThreshold] = useState(50);
  const [ecapaThreshold, setEcapaThreshold] = useState(70);
  const [nlpSensitivity, setNlpSensitivity] = useState(65);
  const [emailAlerts, setEmailAlerts] = useState(true);
  const [slackAlerts, setSlackAlerts] = useState(false);
  const [criticalOnly, setCriticalOnly] = useState(false);
  const [autoBlock, setAutoBlock] = useState(true);
  const [apiKey, setApiKey] = useState("vxg_sk_live_99214820491823904812");
  const [webhookUrl, setWebhookUrl] = useState("https://api.voxguard.security/hooks/amvtf-alerts");

  // API Key & Usage Billing States
  const [activeKey, setActiveKey] = useState<ApiKeyRecord | null>(null);
  const [keyLoading, setKeyLoading] = useState(false);
  const [showKeySecret, setShowKeySecret] = useState(false);
  const [keyCopied, setKeyCopied] = useState(false);

  // Real UPI Checkout States
  type CheckoutStep = "SELECT" | "COLLECT" | "VERIFY_UTR" | "RECEIPT";
  const [showPlanModal, setShowPlanModal] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<"FREE" | "PRO" | "ENTERPRISE">("FREE");
  const [checkoutStep, setCheckoutStep] = useState<CheckoutStep>("SELECT");
  const [payerName, setPayerName] = useState("");
  const [payerEmail, setPayerEmail] = useState("");
  const [upiId, setUpiId] = useState("");
  const [activePaymentOrder, setActivePaymentOrder] = useState<PaymentOrderRecord | null>(null);
  const [utrNumber, setUtrNumber] = useState("");
  const [activationResult, setActivationResult] = useState<PaymentActivationResult | null>(null);
  const [countdownSeconds, setCountdownSeconds] = useState(300);
  const [isVerifyingPayment, setIsVerifyingPayment] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  // Topup modal states
  const [showTopupModal, setShowTopupModal] = useState(false);
  const [topupTab, setTopupTab] = useState<"minutes" | "tokens">("minutes");
  const [selectedMinutesTopup, setSelectedMinutesTopup] = useState<{ minutes: number; price_inr: number; label: string }>({
    minutes: 50,
    price_inr: 100,
    label: "50 Audio Minutes"
  });
  const [selectedTokensTopup, setSelectedTokensTopup] = useState<{ tokens: number; price_inr: number; label: string }>({
    tokens: 5000,
    price_inr: 49,
    label: "Growth Pack (5,000 Tokens)"
  });
  const [topupProcessing, setTopupProcessing] = useState(false);
  type TopupStep = "SELECT" | "COLLECT" | "VERIFY_UTR" | "SUCCESS";
  const [topupStep, setTopupStep] = useState<TopupStep>("SELECT");
  const [topupUpiId, setTopupUpiId] = useState("");
  const [topupPayerName, setTopupPayerName] = useState("");
  const [topupPaymentOrder, setTopupPaymentOrder] = useState<PaymentOrderRecord | null>(null);
  const [topupUtrNumber, setTopupUtrNumber] = useState("");
  const [topupCountdown, setTopupCountdown] = useState(300);
  const [topupPaymentError, setTopupPaymentError] = useState<string | null>(null);
  const [topupSuccessDetails, setTopupSuccessDetails] = useState<{
    units_added: string;
    amount_paid: number;
    utr: string;
  } | null>(null);

  useEffect(() => {
    async function loadSettings() {
      setLoading(true);
      try {
        const data = await getSettings();
        setAasistThreshold(data.aasistThreshold);
        setEcapaThreshold(data.ecapaThreshold);
        setNlpSensitivity(data.nlpSensitivity);
        setEmailAlerts(data.emailAlerts);
        setSlackAlerts(data.slackAlerts);
        setCriticalOnly(data.criticalOnly);
        setAutoBlock(data.autoBlock);
        if (data.apiKey) setApiKey(data.apiKey);
        if (data.webhookUrl) setWebhookUrl(data.webhookUrl);
      } catch (err) {
        console.error("Failed to load settings from database:", err);
      } finally {
        setLoading(false);
      }
    }

    async function loadKey() {
      setKeyLoading(true);
      try {
        const keyData = await getActiveApiKey();
        if (keyData) {
          setActiveKey(keyData);
          setApiKey(keyData.key);
        }
      } catch (err) {
        console.error("Failed to load active API key:", err);
      } finally {
        setKeyLoading(false);
      }
    }

    loadSettings();
    loadKey();
  }, []);

  const handleSave = async () => {
    setSaving(true);
    try {
      await updateSettings({
        aasistThreshold,
        ecapaThreshold,
        nlpSensitivity,
        emailAlerts,
        slackAlerts,
        criticalOnly,
        autoBlock,
        apiKey,
        webhookUrl,
      });
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err) {
      console.error("Failed to save settings:", err);
      alert("Failed to save settings to backend database.");
    } finally {
      setSaving(false);
    }
  };

  const handleCopyKey = () => {
    if (!activeKey?.key) return;
    navigator.clipboard.writeText(activeKey.key);
    setKeyCopied(true);
    setTimeout(() => setKeyCopied(false), 2000);
  };

  // Countdown timer for active UPI Collect order
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (checkoutStep === "VERIFY_UTR" && countdownSeconds > 0) {
      timer = setInterval(() => {
        setCountdownSeconds((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [checkoutStep, countdownSeconds]);

  // Countdown timer for active Topup UPI Collect order
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (topupStep === "VERIFY_UTR" && topupCountdown > 0) {
      timer = setInterval(() => {
        setTopupCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [topupStep, topupCountdown]);

  const handleOpenGenerateModal = () => {
    setSelectedPlan("FREE");
    setCheckoutStep("SELECT");
    setPaymentError(null);
    setPayerName("");
    setPayerEmail("");
    setUpiId("");
    setUtrNumber("");
    setActivePaymentOrder(null);
    setActivationResult(null);
    setShowPlanModal(true);
  };

  const handleSelectPlan = (plan: "FREE" | "PRO" | "ENTERPRISE") => {
    setSelectedPlan(plan);
    setPaymentError(null);
    if (plan === "FREE") {
      executeGenerateFreeKey();
    } else {
      setCheckoutStep("COLLECT");
    }
  };

  const executeGenerateFreeKey = async () => {
    setIsProcessing(true);
    setPaymentError(null);
    try {
      const createdKey = await generateApiKey({
        plan_tier: "FREE",
        name: "Free Sandbox Plan Key",
        payment_method: "free_sandbox",
      });
      setActiveKey(createdKey);
      setApiKey(createdKey.key);
      setShowPlanModal(false);
      setCheckoutStep("SELECT");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setPaymentError(err.message);
      } else {
        setPaymentError("Failed to activate Free Sandbox Key");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleSendUpiCollectRequest = async () => {
    const cleanUpi = upiId.trim();
    if (!cleanUpi || (!cleanUpi.includes("@") && cleanUpi.length < 10)) {
      setPaymentError("Please enter a valid UPI ID (e.g. name@okhdfcbank or 9876543210@paytm)");
      return;
    }
    setPaymentError(null);
    setIsProcessing(true);
    try {
      const amount = selectedPlan === "PRO" ? 499.0 : 2999.0;
      const order = await createPaymentOrder(
        selectedPlan,
        amount,
        cleanUpi,
        payerName.trim() || undefined,
        payerEmail.trim() || undefined
      );
      setActivePaymentOrder(order);
      setCountdownSeconds(300); // 5 minutes
      setCheckoutStep("VERIFY_UTR");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setPaymentError(err.message);
      } else {
        setPaymentError("Failed to initiate UPI collect request.");
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const handleVerifyUtr = async () => {
    if (!activePaymentOrder) return;
    const cleanUtr = utrNumber.trim();
    if (cleanUtr.length < 6) {
      setPaymentError("Please enter the 12-digit UPI Bank Reference / UTR Number from your payment app");
      return;
    }
    setPaymentError(null);
    setIsVerifyingPayment(true);
    try {
      const res = await verifyPaymentOrder(activePaymentOrder.order_id, cleanUtr);
      setActivationResult(res);
      setActiveKey(res.api_key);
      setApiKey(res.api_key.key);
      setCheckoutStep("RECEIPT");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setPaymentError(err.message);
      } else {
        setPaymentError("Payment verification failed. Please re-check your UTR number.");
      }
    } finally {
      setIsVerifyingPayment(false);
    }
  };

  const handleCopyText = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleSendTopupUpiCollect = async () => {
    const cleanUpi = topupUpiId.trim();
    if (!cleanUpi || (!cleanUpi.includes("@") && cleanUpi.length < 10)) {
      setTopupPaymentError("Please enter a valid UPI ID (e.g. name@okhdfcbank or 9876543210@paytm)");
      return;
    }
    setTopupPaymentError(null);
    setTopupProcessing(true);
    try {
      const amount = topupTab === "minutes" ? selectedMinutesTopup.price_inr : selectedTokensTopup.price_inr;
      const units = topupTab === "minutes" ? selectedMinutesTopup.minutes : selectedTokensTopup.tokens;
      const order = await createPaymentOrder(
        "RECHARGE",
        amount,
        cleanUpi,
        topupPayerName.trim() || undefined,
        undefined,
        activeKey?.id,
        topupTab,
        units
      );
      setTopupPaymentOrder(order);
      setTopupCountdown(300);
      setTopupStep("VERIFY_UTR");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setTopupPaymentError(err.message);
      } else {
        setTopupPaymentError("Failed to initiate UPI collect request for recharge.");
      }
    } finally {
      setTopupProcessing(false);
    }
  };

  const handleVerifyTopupUtr = async () => {
    if (!topupPaymentOrder) return;
    const cleanUtr = topupUtrNumber.trim();
    if (cleanUtr.length < 6) {
      setTopupPaymentError("Please enter the 12-digit UPI Bank Reference / UTR Number from your payment app");
      return;
    }
    setTopupPaymentError(null);
    setTopupProcessing(true);
    try {
      const res = await verifyPaymentOrder(topupPaymentOrder.order_id, cleanUtr);
      setActiveKey(res.api_key);
      const unitsLabel = topupTab === "minutes"
        ? `+${selectedMinutesTopup.minutes} Audio Minutes`
        : `+${selectedTokensTopup.tokens.toLocaleString()} Tokens`;
      setTopupSuccessDetails({
        units_added: unitsLabel,
        amount_paid: topupPaymentOrder.amount_inr,
        utr: cleanUtr,
      });
      setTopupStep("SUCCESS");
    } catch (err: unknown) {
      if (err instanceof Error) {
        setTopupPaymentError(err.message);
      } else {
        setTopupPaymentError("Payment verification failed. Please check your UTR number.");
      }
    } finally {
      setTopupProcessing(false);
    }
  };

  const handleRevokeKey = async () => {
    if (!activeKey) return;
    if (!confirm("Are you sure you want to revoke this API key? External telephony gateways using it will stop authenticating.")) return;
    try {
      await revokeApiKey(activeKey.id);
      setActiveKey(null);
      setApiKey("");
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert("Failed to revoke key: " + err.message);
      } else {
        alert("Failed to revoke key.");
      }
    }
  };

  const sections = [
    { id: "thresholds" as const, label: "Detection Thresholds", icon: Sliders, description: "Tune AMVTF engine sensitivity" },
    { id: "notifications" as const, label: "Notifications", icon: BellIcon, description: "Alert delivery preferences" },
    { id: "api" as const, label: "API & Usage Billing (₹)", icon: Key, description: "Pay-as-you-go & ₹2/min audio API" },
    { id: "general" as const, label: "General", icon: Globe, description: "System architecture specs" },
  ];

  const Toggle = ({ enabled, onToggle }: { enabled: boolean; onToggle: () => void }) => (
    <button onClick={onToggle} className="transition-colors cursor-pointer">
      {enabled ? (
        <ToggleRight className="w-8 h-8 text-[#F6821F]" />
      ) : (
        <ToggleLeft className="w-8 h-8 text-gray-300" />
      )}
    </button>
  );

  return (
    <>
      {/* Top Navbar */}
      <nav className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 z-20 sticky top-0">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <a href="/" className="hover:text-[#F6821F]">VoxGuard SOC</a>
          <ChevronRight className="w-4 h-4" />
          <span className="text-gray-900 font-medium">Engine Configuration & API Billing</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-orange-50 border border-orange-200 text-xs font-semibold text-[#F6821F]">
            <Zap className="w-3.5 h-3.5" />
            <span>Pay-As-You-Go: ₹2.00 / Min</span>
          </div>
          <button className="text-gray-500 hover:text-gray-900 relative">
            <Bell className="w-5 h-5" />
          </button>
        </div>
      </nav>

      {/* Page Header */}
      <header className="bg-white border-b border-gray-200 py-6 px-6 sm:px-10 shadow-sm">
        <div className="max-w-[1400px] mx-auto flex flex-col sm:flex-row sm:items-end justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold text-[#F6821F] uppercase tracking-wider mb-1">
              <span>Security Operations Center</span>
              <span>•</span>
              <span>System Settings & Indian Rupee (₹) Billing</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Platform Settings & Telephony API</h1>
            <p className="text-sm text-gray-500 mt-1">
              Configure multi-modal biometric thresholds, telephony webhook endpoints, and usage-based audio billing.
            </p>
          </div>
          <Button
            onClick={handleSave}
            disabled={saving}
            className="bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-sm flex items-center gap-2 self-start sm:self-auto cursor-pointer"
          >
            {saving ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Saving...</span>
              </>
            ) : savedSuccess ? (
              <>
                <CheckCircle2 className="w-4 h-4 text-white" />
                <span>Saved to Database!</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>Save Configuration</span>
              </>
            )}
          </Button>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="max-w-[1400px] mx-auto p-6 sm:p-10">
        <div className="grid lg:grid-cols-[280px_1fr] gap-8 items-start">
          {/* Section Navigation Sidebar */}
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-2 space-y-1">
            {sections.map((section) => {
              const Icon = section.icon;
              const isActive = activeSection === section.id;
              return (
                <button
                  key={section.id}
                  onClick={() => setActiveSection(section.id)}
                  className={cn(
                    "w-full text-left px-3 py-2.5 rounded-md flex items-start gap-3 transition-colors cursor-pointer",
                    isActive
                      ? "bg-orange-50 text-[#F6821F] font-semibold"
                      : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                  )}
                >
                  <Icon className={cn("w-5 h-5 mt-0.5 shrink-0", isActive ? "text-[#F6821F]" : "text-gray-400")} />
                  <div>
                    <div className="text-sm">{section.label}</div>
                    <div className="text-[11px] text-gray-400 font-normal leading-tight mt-0.5">{section.description}</div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Settings Section Panel */}
          <div className="space-y-6">
            {activeSection === "thresholds" && (
              <>
                <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
                  <h2 className="text-lg font-semibold text-gray-900 mb-1">AMVTF Biometric Threat Thresholds</h2>
                  <p className="text-sm text-gray-500 mb-6">
                    Fine-tune the neural sensitivity thresholds for voice authenticity, speaker recognition, and intent risk.
                  </p>

                  <div className="space-y-6">
                    {/* AASIST */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <div>
                          <label className="text-sm font-semibold text-gray-900">AASIST Authenticity Cutoff</label>
                          <p className="text-xs text-gray-500">Deepfake detection minimum score to flag audio as synthetic</p>
                        </div>
                        <span className="text-lg font-bold text-[#F6821F] font-mono">{aasistThreshold}%</span>
                      </div>
                      <input
                        type="range"
                        min="10"
                        max="95"
                        value={aasistThreshold}
                        onChange={(e) => setAasistThreshold(Number(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-[#F6821F]"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                        <span>Permissive (10%)</span>
                        <span>Balanced (50%)</span>
                        <span>Strict (95%)</span>
                      </div>
                    </div>

                    <div className="h-px bg-gray-200" />

                    {/* ECAPA */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <div>
                          <label className="text-sm font-semibold text-gray-900">ECAPA-TDNN Speaker Verification Minimum</label>
                          <p className="text-xs text-gray-500">192-dimensional cosine similarity threshold for identity match</p>
                        </div>
                        <span className="text-lg font-bold text-[#F6821F] font-mono">{ecapaThreshold}%</span>
                      </div>
                      <input
                        type="range"
                        min="30"
                        max="99"
                        value={ecapaThreshold}
                        onChange={(e) => setEcapaThreshold(Number(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-[#F6821F]"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                        <span>Permissive (30%)</span>
                        <span>Strict (99%)</span>
                      </div>
                    </div>

                    <div className="h-px bg-gray-200" />

                    {/* NLP */}
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <div>
                          <label className="text-sm font-semibold text-gray-900">NLP Contextual Sensitivity</label>
                          <p className="text-xs text-gray-500">DistilBERT urgency and social-engineering sensitivity level</p>
                        </div>
                        <span className="text-lg font-bold text-[#F6821F] font-mono">{nlpSensitivity}%</span>
                      </div>
                      <input
                        type="range"
                        min="20"
                        max="100"
                        value={nlpSensitivity}
                        onChange={(e) => setNlpSensitivity(Number(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-full appearance-none cursor-pointer accent-[#F6821F]"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
                        <span>Less Sensitive (20%)</span>
                        <span>More Sensitive (100%)</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-medium text-amber-800">Threshold Calibration Guide</p>
                    <p className="text-xs text-amber-700 mt-0.5">
                      Per the SIH presentation guidelines: calibrate thresholds against validation data rather than static universal constants. Current defaults are AASIST: 50%, ECAPA: 70%, NLP: 65%.
                    </p>
                  </div>
                </div>
              </>
            )}

            {activeSection === "notifications" && (
              <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-1">Notification Preferences</h2>
                <p className="text-sm text-gray-500 mb-6">Configure how threat alerts are dispatched to SOC responders.</p>

                <div className="space-y-6">
                  <div className="flex items-center justify-between py-3 border-b border-gray-100">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Email Alerts</p>
                      <p className="text-xs text-gray-500">Send high-priority threat notifications via email</p>
                    </div>
                    <Toggle enabled={emailAlerts} onToggle={() => setEmailAlerts(!emailAlerts)} />
                  </div>
                  <div className="flex items-center justify-between py-3 border-b border-gray-100">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Slack Webhook Integration</p>
                      <p className="text-xs text-gray-500">Post immediate alerts to your dedicated incident response channel</p>
                    </div>
                    <Toggle enabled={slackAlerts} onToggle={() => setSlackAlerts(!slackAlerts)} />
                  </div>
                  <div className="flex items-center justify-between py-3 border-b border-gray-100">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Critical Alerts Only</p>
                      <p className="text-xs text-gray-500">Suppress warnings and only dispatch alerts for verified synthetic deepfakes</p>
                    </div>
                    <Toggle enabled={criticalOnly} onToggle={() => setCriticalOnly(!criticalOnly)} />
                  </div>
                  <div className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-medium text-gray-900">Auto-Block on Deepfake</p>
                      <p className="text-xs text-gray-500">Automatically terminate call audio when AASIST scores drop below threshold</p>
                    </div>
                    <Toggle enabled={autoBlock} onToggle={() => setAutoBlock(!autoBlock)} />
                  </div>
                </div>
              </div>
            )}

            {activeSection === "api" && (
              <div className="space-y-6">
                {/* Main API Card */}
                <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-gray-100 gap-4">
                    <div>
                      <div className="flex items-center gap-2">
                        <h2 className="text-lg font-bold text-gray-900">API Credentials & Usage-Based Billing</h2>
                        {activeKey && (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            {activeKey.plan_tier.toUpperCase() === "FREE" || activeKey.plan_tier.toUpperCase() === "FREE_TRIAL"
                              ? "Free Sandbox (550 Tokens)"
                              : activeKey.plan_tier.toUpperCase() === "PRO"
                              ? "Developer Pro"
                              : "Enterprise SOC"}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">
                        Live audio stream analysis charged at <strong>₹2.00 / Minute</strong>. 550 Free Starter Tokens included.
                      </p>
                    </div>

                    {!activeKey && (
                      <Button
                        onClick={handleOpenGenerateModal}
                        className="bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md shadow-orange-500/20 gap-2 cursor-pointer"
                      >
                        <Zap className="w-4 h-4" /> Activate Free API Key (550 Tokens)
                      </Button>
                    )}
                  </div>

                  {/* If no key generated yet */}
                  {!activeKey ? (
                    <div className="py-10 flex flex-col items-center justify-center text-center max-w-md mx-auto">
                      <div className="w-14 h-14 rounded-2xl bg-orange-50 border border-orange-100 flex items-center justify-center text-[#F6821F] mb-4 shadow-sm">
                        <Key className="w-7 h-7" />
                      </div>
                      <h3 className="text-base font-bold text-gray-900 mb-1">No API Key Generated Yet</h3>
                      <p className="text-xs text-gray-500 mb-6 leading-relaxed">
                        Activate your authenticated API credentials with <strong>550 Free Starter Tokens</strong> and <strong>15 Free Audio Minutes</strong>. Stream audio to `/api/analyze/live` with usage billing at <strong>₹2.00 / minute</strong>.
                      </p>
                      <Button
                        onClick={handleOpenGenerateModal}
                        className="bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md shadow-orange-500/20 gap-2 cursor-pointer text-sm py-2.5 px-5"
                      >
                        <Zap className="w-4 h-4" /> Get Free API Key (550 Tokens)
                      </Button>
                    </div>
                  ) : (
                    /* Active Key UI */
                    <div className="pt-5 space-y-6">
                      {/* Key Value with Show/Hide & Copy */}
                      <div>
                        <div className="flex justify-between items-center mb-2">
                          <label className="text-xs font-bold text-gray-700 uppercase tracking-wider">Active SOC API Key</label>
                          <span className="text-[11px] text-gray-400 font-mono">Header: x-api-key or Bearer</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="relative flex-1">
                            <input
                              type="text"
                              readOnly
                              value={
                                showKeySecret
                                  ? activeKey.key
                                  : `${activeKey.key.slice(0, 10)}${"•".repeat(24)}`
                              }
                              className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono text-gray-900 focus:outline-none"
                            />
                            <button
                              type="button"
                              onClick={() => setShowKeySecret(!showKeySecret)}
                              className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 cursor-pointer"
                              title={showKeySecret ? "Hide key" : "Reveal key"}
                            >
                              {showKeySecret ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                            </button>
                          </div>
                          <Button
                            type="button"
                            onClick={handleCopyKey}
                            variant="outline"
                            className="shrink-0 gap-1.5 border-gray-200 text-gray-700 hover:bg-gray-50 cursor-pointer"
                          >
                            {keyCopied ? (
                              <>
                                <Check className="w-4 h-4 text-emerald-600" />
                                <span className="text-emerald-700 font-medium text-xs">Copied!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="w-4 h-4 text-gray-500" />
                                <span className="text-xs font-medium">Copy Key</span>
                              </>
                            )}
                          </Button>
                        </div>
                      </div>

                      {/* Usage-Based Billing Dashboard Cards */}
                      <div className="grid sm:grid-cols-3 gap-4">
                        {/* Audio Streaming Minutes Card */}
                        <div className="p-4 bg-orange-50/40 border border-orange-200/80 rounded-xl relative overflow-hidden">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5 text-xs font-bold text-gray-700 uppercase tracking-wider">
                              <Clock className="w-4 h-4 text-[#F6821F]" />
                              <span>Audio Streaming</span>
                            </div>
                            <Badge className="bg-orange-100 text-[#F6821F] border-orange-200 text-[10px]">
                              ₹{activeKey.rate_per_min_inr?.toFixed(2) || "2.00"} / Min
                            </Badge>
                          </div>
                          <div className="mt-1">
                            <span className="text-2xl font-black font-mono text-gray-900">
                              {(activeKey.minutes_remaining ?? 15.0).toFixed(1)}
                            </span>
                            <span className="text-xs text-gray-500 font-medium ml-1.5">Minutes Available</span>
                          </div>
                          <p className="text-[11px] text-gray-500 mt-2">
                            Billed per-minute for live call streams & audio uploads.
                          </p>
                        </div>

                        {/* Token Balance Card */}
                        <div className="p-4 bg-gray-50 border border-gray-200/80 rounded-xl">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5 text-xs font-bold text-gray-700 uppercase tracking-wider">
                              <Coins className="w-4 h-4 text-amber-500" />
                              <span>Token Quota</span>
                            </div>
                            <span className="text-[10px] text-gray-500 font-medium">
                              ~10 tokens/op
                            </span>
                          </div>
                          <div className="mt-1">
                            <span className="text-2xl font-black font-mono text-gray-900">
                              {activeKey.tokens_remaining.toLocaleString()}
                            </span>
                            <span className="text-xs text-gray-400 font-mono ml-1.5">
                              / {activeKey.tokens_total.toLocaleString()}
                            </span>
                          </div>
                          <p className="text-[11px] text-gray-500 mt-2">
                            Used for NLP intent scanning and threat classification.
                          </p>
                        </div>

                        {/* Wallet Balance Card */}
                        <div className="p-4 bg-emerald-50/40 border border-emerald-200/80 rounded-xl">
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-1.5 text-xs font-bold text-gray-700 uppercase tracking-wider">
                              <Wallet className="w-4 h-4 text-emerald-600" />
                              <span>Wallet Balance</span>
                            </div>
                            <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 text-[10px]">
                              Prepaid INR
                            </Badge>
                          </div>
                          <div className="mt-1">
                            <span className="text-2xl font-black font-mono text-emerald-700">
                              ₹{(activeKey.balance_inr ?? 0.0).toFixed(2)}
                            </span>
                            <span className="text-xs text-emerald-600/80 font-medium ml-1.5">INR</span>
                          </div>
                          <p className="text-[11px] text-gray-500 mt-2">
                            Direct credit applied for overage streaming.
                          </p>
                        </div>
                      </div>

                      {/* Action Buttons Row */}
                      <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
                        <div className="flex items-center gap-2">
                          <Button
                            onClick={() => {
                              setTopupTab("minutes");
                              setTopupStep("SELECT");
                              setTopupPaymentError(null);
                              setShowTopupModal(true);
                            }}
                            className="bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-sm gap-1.5 cursor-pointer text-xs"
                          >
                            <Clock className="w-4 h-4" /> Recharge Minutes (₹2/Min)
                          </Button>
                          <Button
                            onClick={() => {
                              setTopupTab("tokens");
                              setTopupStep("SELECT");
                              setTopupPaymentError(null);
                              setShowTopupModal(true);
                            }}
                            variant="outline"
                            className="border-gray-300 text-gray-700 hover:bg-gray-50 shadow-sm gap-1.5 cursor-pointer text-xs"
                          >
                            <Coins className="w-4 h-4 text-amber-500" /> Buy Tokens (₹)
                          </Button>
                          <Button
                            onClick={handleOpenGenerateModal}
                            variant="outline"
                            className="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs gap-1.5 cursor-pointer"
                          >
                            <RefreshCw className="w-3.5 h-3.5 text-gray-500" /> Switch Plan
                          </Button>
                        </div>
                        <Button
                          onClick={handleRevokeKey}
                          variant="ghost"
                          className="text-red-600 hover:text-red-700 hover:bg-red-50 text-xs gap-1.5 cursor-pointer"
                        >
                          <Trash2 className="w-3.5 h-3.5" /> Revoke Key
                        </Button>
                      </div>
                    </div>
                  )}
                </div>

                {/* Business Model Tier Breakdown & Feature Comparison */}
                <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
                  <div className="mb-5">
                    <h3 className="text-base font-bold text-gray-900">SaaS Business Model & Feature Entitlements</h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Clear operational capabilities and quotas by plan tier in Indian Rupees (₹).
                    </p>
                  </div>

                  <div className="grid md:grid-cols-3 gap-4">
                    {/* Free Plan Summary */}
                    <div className="p-4 rounded-xl border border-gray-200 bg-gray-50/60 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-gray-600 uppercase tracking-wider">Free Plan</span>
                          <Badge variant="outline" className="text-[10px] bg-white">₹0 Forever</Badge>
                        </div>
                        <div className="text-lg font-black text-gray-900 font-mono mb-2">
                          550 Tokens
                        </div>
                        <p className="text-[11px] text-gray-500 mb-3">
                          15 Audio Minutes Free • Pay-As-You-Go Rate: <strong>₹2.00 / Min</strong>
                        </p>
                        <div className="space-y-1.5 text-xs text-gray-600">
                          <div className="flex items-center gap-1.5 text-emerald-700">
                            <Check className="w-3.5 h-3.5" /> 1 Enrolled Target Voiceprint
                          </div>
                          <div className="flex items-center gap-1.5 text-emerald-700">
                            <Check className="w-3.5 h-3.5" /> Core AASIST Voice Authenticity
                          </div>
                          <div className="flex items-center gap-1.5 text-gray-400">
                            <Lock className="w-3 h-3 text-gray-400" /> Multi-Speaker Matching Locked
                          </div>
                          <div className="flex items-center gap-1.5 text-gray-400">
                            <Lock className="w-3 h-3 text-gray-400" /> Auto-Block Webhooks Locked
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Pro Plan Summary */}
                    <div className="p-4 rounded-xl border-2 border-orange-200 bg-orange-50/20 flex flex-col justify-between relative">
                      <span className="absolute -top-2.5 right-4 px-2 py-0.5 rounded-full text-[9px] font-bold uppercase tracking-wider bg-[#F6821F] text-white">
                        Popular
                      </span>
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-[#F6821F] uppercase tracking-wider">Developer Pro</span>
                          <span className="text-xs font-bold text-gray-900 font-mono">₹499 / Mo</span>
                        </div>
                        <div className="text-lg font-black text-gray-900 font-mono mb-2">
                          10,000 Tokens + 150 Mins
                        </div>
                        <p className="text-[11px] text-gray-500 mb-3">
                          Included Quota • Additional Audio: <strong>₹2.00 / Min</strong>
                        </p>
                        <div className="space-y-1.5 text-xs text-gray-600">
                          <div className="flex items-center gap-1.5 text-emerald-700">
                            <Check className="w-3.5 h-3.5" /> Up to 15 Enrolled Voiceprints
                          </div>
                          <div className="flex items-center gap-1.5 text-emerald-700">
                            <Check className="w-3.5 h-3.5" /> ECAPA-TDNN 192-dim Verification
                          </div>
                          <div className="flex items-center gap-1.5 text-emerald-700">
                            <Check className="w-3.5 h-3.5" /> Auto-Block & Webhook Telemetry
                          </div>
                          <div className="flex items-center gap-1.5 text-emerald-700">
                            <Check className="w-3.5 h-3.5" /> Priority Processing Queue (&lt;20ms)
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Enterprise Plan Summary */}
                    <div className="p-4 rounded-xl border border-indigo-200 bg-indigo-50/20 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-bold text-indigo-700 uppercase tracking-wider">Enterprise SOC</span>
                          <span className="text-xs font-bold text-gray-900 font-mono">₹2,999 / Mo</span>
                        </div>
                        <div className="text-lg font-black text-gray-900 font-mono mb-2">
                          50,000 Tokens + 1,000 Mins
                        </div>
                        <p className="text-[11px] text-gray-500 mb-3">
                          Discounted Overage Rate: <strong>₹1.50 / Min</strong>
                        </p>
                        <div className="space-y-1.5 text-xs text-gray-700">
                          <div className="flex items-center gap-1.5 text-emerald-700 font-medium">
                            <CheckCircle className="w-3.5 h-3.5 text-emerald-600" /> ALL FEATURES UNLOCKED
                          </div>
                          <div className="flex items-center gap-1.5 text-indigo-900">
                            <Check className="w-3.5 h-3.5 text-indigo-600" /> Unlimited Enrolled Profiles
                          </div>
                          <div className="flex items-center gap-1.5 text-indigo-900">
                            <Check className="w-3.5 h-3.5 text-indigo-600" /> Dedicated Zero-Wait Pipeline
                          </div>
                          <div className="flex items-center gap-1.5 text-indigo-900">
                            <Check className="w-3.5 h-3.5 text-indigo-600" /> Forensic Incident PDF Dossiers
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Webhook Endpoint Configuration */}
                <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-6">
                  <h3 className="text-base font-bold text-gray-900 mb-1">Webhook Endpoint URL</h3>
                  <p className="text-xs text-gray-500 mb-4">
                    External telemetry endpoint where AMVTF dispatches real-time synthetic deepfake alerts and verdicts.
                  </p>
                  <div>
                    <input
                      type="text"
                      value={webhookUrl}
                      onChange={(e) => setWebhookUrl(e.target.value)}
                      className="w-full px-3.5 py-2.5 bg-gray-50 border border-gray-200 rounded-lg text-sm font-mono text-gray-800 focus:bg-white focus:outline-none focus:border-[#F6821F] transition-colors"
                      placeholder="https://your-api.com/webhooks/voice-alerts"
                    />
                  </div>
                </div>
              </div>
            )}

            {activeSection === "general" && (
              <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-1">AMVTF Engine Architecture</h2>
                <p className="text-sm text-gray-500 mb-6">System intelligence specs as presented in SIH Hackathon.</p>

                <div className="grid sm:grid-cols-2 gap-4 text-xs">
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="font-semibold text-gray-500 block">Backend Framework</span>
                    <span className="font-bold text-gray-900 text-sm">Python 3.11 / FastAPI / Uvicorn</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="font-semibold text-gray-500 block">Database Storage</span>
                    <span className="font-bold text-gray-900 text-sm">Cloud PostgreSQL (Supabase) / SQLite</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="font-semibold text-gray-500 block">Authenticity Engine</span>
                    <span className="font-bold text-gray-900 text-sm">Multi-Platform AASIST Live Classifier</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="font-semibold text-gray-500 block">Speaker Identity</span>
                    <span className="font-bold text-gray-900 text-sm">ECAPA-TDNN 192-dim Cosine Match</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="font-semibold text-gray-500 block">Context Engine</span>
                    <span className="font-bold text-gray-900 text-sm">DistilBERT Intent Classifier</span>
                  </div>
                  <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <span className="font-semibold text-gray-500 block">Pay-As-You-Go Billing</span>
                    <span className="font-bold text-[#F6821F] text-sm">₹2.00 / Minute (Audio Streams)</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ─── MODAL 1: PLAN SELECTION & CHECKOUT MODAL (INR ONLY) ─── */}
{showPlanModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-2xl overflow-hidden relative">
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-gray-900">
                  {checkoutStep === "SELECT" && "Select API Key Plan"}
                  {checkoutStep === "COLLECT" && `Initiate UPI Collect — ₹${selectedPlan === "PRO" ? "499.00" : "2,999.00"}`}
                  {checkoutStep === "VERIFY_UTR" && "Approve UPI Payment & Verify UTR"}
                  {checkoutStep === "RECEIPT" && "Official Payment Receipt & Activation"}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {checkoutStep === "SELECT" && "All amounts in Indian Rupees (₹). 15 Audio Mins Free • Ongoing usage ₹2.00/min."}
                  {checkoutStep === "COLLECT" && "Dispatches a live UPI collect request to your Google Pay, PhonePe, or Paytm app"}
                  {checkoutStep === "VERIFY_UTR" && "Approve payment on your phone, then verify your 12-digit bank UTR receipt"}
                  {checkoutStep === "RECEIPT" && "Payment verified! Credentials, tokens, and 15 free audio minutes are active."}
                </p>
              </div>
              <button
                onClick={() => setShowPlanModal(false)}
                className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {paymentError && (
                <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 shrink-0" />
                  <span>{paymentError}</span>
                </div>
              )}

              {/* STEP 1: PLAN SELECTION TIERS */}
              {checkoutStep === "SELECT" && (
                <div className="grid sm:grid-cols-3 gap-4">
                  {/* Free Sandbox Plan Card */}
                  <div className="border border-gray-200 rounded-xl p-4 flex flex-col justify-between hover:border-gray-300 transition-all bg-gray-50/50">
                    <div>
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-gray-200 text-gray-700 mb-2">
                        Free Sandbox
                      </span>
                      <h4 className="text-base font-bold text-gray-900">Free Plan</h4>
                      <div className="mt-2 mb-3">
                        <span className="text-2xl font-black text-gray-900">₹0</span>
                        <span className="text-xs text-gray-500"> / forever</span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-gray-200/80 mb-3 text-center">
                        <span className="text-sm font-extrabold text-[#F6821F] font-mono">550 Free Tokens</span>
                        <span className="text-[10px] text-gray-500 block">15 Audio Mins Free • ₹2/Min</span>
                      </div>
                      <ul className="text-[11px] text-gray-600 space-y-1.5 mb-4">
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Standard AASIST GNN
                        </li>
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> 1 Voiceprint Profile
                        </li>
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Instant Activation
                        </li>
                      </ul>
                    </div>
                    <Button
                      onClick={() => handleSelectPlan("FREE")}
                      disabled={isProcessing}
                      variant="outline"
                      className="w-full text-xs font-semibold cursor-pointer border-gray-300 hover:bg-gray-100"
                    >
                      {isProcessing && selectedPlan === "FREE" ? "Activating..." : "Activate Free (550 Tokens)"}
                    </Button>
                  </div>

                  {/* Pro Plan Card */}
                  <div className="border-2 border-[#F6821F] rounded-xl p-4 flex flex-col justify-between hover:shadow-md transition-all relative bg-orange-50/20">
                    <span className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-[#F6821F] text-white shadow-sm">
                      Most Popular
                    </span>
                    <div>
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-orange-100 text-[#F6821F] mb-2 mt-1">
                        Telephony Pro
                      </span>
                      <h4 className="text-base font-bold text-gray-900">Developer Pro</h4>
                      <div className="mt-2 mb-3">
                        <span className="text-2xl font-black text-gray-900">₹499</span>
                        <span className="text-xs text-gray-500"> / month</span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-orange-200 mb-3 text-center shadow-xs">
                        <span className="text-sm font-extrabold text-[#F6821F] font-mono">10,000 Tokens</span>
                        <span className="text-[10px] text-gray-500 block">150 Audio Mins Included</span>
                      </div>
                      <ul className="text-[11px] text-gray-600 space-y-1.5 mb-4">
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Priority Queue (&lt;20ms)
                        </li>
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Up to 15 Voiceprints
                        </li>
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Auto-Block & Webhooks
                        </li>
                      </ul>
                    </div>
                    <Button
                      onClick={() => handleSelectPlan("PRO")}
                      className="w-full text-xs font-semibold bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-sm cursor-pointer"
                    >
                      Choose Pro (₹499)
                    </Button>
                  </div>

                  {/* Enterprise Plan Card */}
                  <div className="border border-indigo-200 rounded-xl p-4 flex flex-col justify-between hover:border-indigo-300 transition-all bg-indigo-50/20">
                    <div>
                      <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-100 text-indigo-700 mb-2">
                        Enterprise
                      </span>
                      <h4 className="text-base font-bold text-gray-900">Enterprise SOC</h4>
                      <div className="mt-2 mb-3">
                        <span className="text-2xl font-black text-gray-900">₹2,999</span>
                        <span className="text-xs text-gray-500"> / month</span>
                      </div>
                      <div className="p-2 bg-white rounded-lg border border-indigo-200 mb-3 text-center">
                        <span className="text-sm font-extrabold text-indigo-700 font-mono">50,000 Tokens</span>
                        <span className="text-[10px] text-gray-500 block">1,000 Mins Included (₹1.50/min)</span>
                      </div>
                      <ul className="text-[11px] text-gray-600 space-y-1.5 mb-4">
                        <li className="flex items-center gap-1.5 font-semibold text-emerald-700">
                          <Check className="w-3.5 h-3.5 shrink-0" /> ALL FEATURES UNLOCKED
                        </li>
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Unlimited Voiceprints
                        </li>
                        <li className="flex items-center gap-1.5">
                          <Check className="w-3.5 h-3.5 text-emerald-600 shrink-0" /> Forensic Dossier PDFs
                        </li>
                      </ul>
                    </div>
                    <Button
                      onClick={() => handleSelectPlan("ENTERPRISE")}
                      variant="outline"
                      className="w-full text-xs font-semibold cursor-pointer border-indigo-300 text-indigo-800 hover:bg-indigo-50"
                    >
                      Choose Enterprise (₹2,999)
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 2: UPI COLLECT REQUEST DISPATCH FORM */}
              {checkoutStep === "COLLECT" && (
                <div className="space-y-4">
                  <div className="p-4 bg-orange-50/40 border border-orange-200 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-gray-900 block">
                        {selectedPlan === "PRO" ? "Developer Pro (10,000 Tokens + 150 Mins)" : "Enterprise SOC (50,000 Tokens + 1,000 Mins)"}
                      </span>
                      <span className="text-xs text-gray-500">
                        🎁 First 15 Audio Mins Free • Ongoing usage ₹{selectedPlan === "PRO" ? "2.00" : "1.50"} / min
                      </span>
                    </div>
                    <span className="text-2xl font-black font-mono text-[#F6821F]">
                      ₹{selectedPlan === "PRO" ? "499.00" : "2,999.00"}
                    </span>
                  </div>

                  <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-3">
                    <div>
                      <label className="text-xs font-semibold text-gray-700 block mb-1">
                        Payer Full Name / Organization <span className="text-gray-400 font-normal">(Optional)</span>
                      </label>
                      <input
                        type="text"
                        value={payerName}
                        onChange={(e) => setPayerName(e.target.value)}
                        placeholder="e.g. Mahesh Kumar (SecOps Lead)"
                        className="w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-xs text-gray-800 focus:outline-none focus:border-[#F6821F]"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-gray-700 block mb-1">
                        Account Email Address <span className="text-[#F6821F]">*</span>
                      </label>
                      <input
                        type="email"
                        value={payerEmail}
                        onChange={(e) => setPayerEmail(e.target.value)}
                        placeholder="e.g. mahesh@organization.com (Credentials will be sent here)"
                        className="w-full px-3 py-2 bg-white border border-gray-200 rounded-md text-xs text-gray-800 focus:outline-none focus:border-[#F6821F]"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-gray-700 block mb-1">
                        Your UPI ID / VPA <span className="text-[#F6821F]">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={upiId}
                          onChange={(e) => { setUpiId(e.target.value); setPaymentError(null); }}
                          placeholder="e.g. username@okhdfcbank or 9876543210@paytm"
                          className="w-full px-3 py-2 pl-9 bg-white border border-gray-200 rounded-md text-xs font-mono text-gray-800 focus:outline-none focus:border-[#F6821F]"
                        />
                        <Smartphone className="w-4 h-4 text-gray-400 absolute left-2.5 top-2.5" />
                      </div>
                      <p className="text-[11px] text-gray-500 mt-1 flex items-center gap-1">
                        <Lock className="w-3 h-3 text-emerald-600" />
                        Collect request will be dispatched to Google Pay, PhonePe, Paytm, or BHIM.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => { setCheckoutStep("SELECT"); setPaymentError(null); }}
                      className="text-xs text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      &larr; Back to Plans
                    </Button>
                    <Button
                      type="button"
                      disabled={isProcessing}
                      onClick={handleSendUpiCollectRequest}
                      className="bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md gap-2 cursor-pointer text-xs py-2 px-5"
                    >
                      {isProcessing ? (
                        <span>Dispatching Collect Request...</span>
                      ) : (
                        <span>Send UPI Collect Request (₹{selectedPlan === "PRO" ? "499.00" : "2,999.00"}) &rarr;</span>
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 3: AWAITING UPI APPROVAL & UTR CONFIRMATION */}
              {checkoutStep === "VERIFY_UTR" && activePaymentOrder && (
                <div className="space-y-4">
                  {/* Status Banner */}
                  <div className="p-3.5 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3">
                    <div className="w-3 h-3 rounded-full bg-amber-500 animate-ping mt-1 shrink-0" />
                    <div>
                      <h5 className="text-xs font-bold text-amber-900">UPI Collect Request Active</h5>
                      <p className="text-[11px] text-amber-800 mt-0.5 leading-relaxed">
                        A payment request of <b>₹{activePaymentOrder.amount_inr.toFixed(2)}</b> was sent to <b>{activePaymentOrder.payer_upi_id}</b>.
                        Please open your UPI app and approve payment to <b>{activePaymentOrder.merchant_vpa}</b>.
                      </p>
                    </div>
                  </div>

                  {/* QR Code & Direct Payment Info */}
                  <div className="grid sm:grid-cols-2 gap-4 p-4 bg-gray-50 border border-gray-200 rounded-xl items-center">
                    <div className="flex flex-col items-center justify-center p-3 bg-white rounded-lg border border-gray-200 shadow-xs text-center">
                      <div className="p-2 bg-white rounded border border-gray-100 mb-2">
                        <QRCodeSVG value={activePaymentOrder.upi_intent_uri} size={130} level="M" />
                      </div>
                      <span className="text-[10px] font-semibold text-gray-500">Scan via GPay / PhonePe / Paytm</span>
                    </div>

                    <div className="space-y-2 text-xs">
                      <div>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 block">Merchant VPA</span>
                        <div className="flex items-center justify-between font-mono font-bold text-gray-900 bg-white px-2.5 py-1.5 rounded border border-gray-200">
                          <span>{activePaymentOrder.merchant_vpa}</span>
                          <button
                            type="button"
                            onClick={() => handleCopyText(activePaymentOrder.merchant_vpa, "vpa")}
                            className="text-gray-400 hover:text-[#F6821F] p-0.5"
                            title="Copy UPI ID"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      <div>
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 block">Order Reference</span>
                        <span className="font-mono text-gray-600 block">{activePaymentOrder.order_id}</span>
                      </div>

                      <div className="pt-1">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 block">Approval Window</span>
                        <span className="text-sm font-mono font-extrabold text-[#F6821F]">
                          ⏱ {Math.floor(countdownSeconds / 60)}:{(countdownSeconds % 60).toString().padStart(2, "0")} Remaining
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* 12-Digit Bank UTR Input */}
                  <div className="p-4 bg-white border-2 border-orange-200 rounded-xl space-y-2">
                    <label className="text-xs font-bold text-gray-900 flex items-center justify-between">
                      <span>Enter 12-Digit Bank Reference (UTR) Number</span>
                      <span className="text-[10px] text-gray-400 font-normal">Found in UPI App receipt / SMS</span>
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={utrNumber}
                        onChange={(e) => { setUtrNumber(e.target.value.trim()); setPaymentError(null); }}
                        placeholder="e.g. 425519827103"
                        className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-xs font-mono font-bold tracking-wider text-gray-900 focus:outline-none focus:border-[#F6821F]"
                      />
                    </div>
                    <p className="text-[11px] text-gray-500">
                      Demo / testing reference: <span className="font-mono font-bold text-gray-700">425519827103</span>
                    </p>
                  </div>

                  <div className="flex items-center justify-between pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setCheckoutStep("COLLECT")}
                      className="text-xs text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      &larr; Modify UPI ID
                    </Button>
                    <Button
                      type="button"
                      disabled={isVerifyingPayment || !utrNumber.trim()}
                      onClick={handleVerifyUtr}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md gap-2 cursor-pointer text-xs py-2 px-6 font-bold"
                    >
                      {isVerifyingPayment ? (
                        <span>Verifying Bank UTR...</span>
                      ) : (
                        <span>Verify Payment & Grant Access &rarr;</span>
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 4: OFFICIAL ACTIVATION RECEIPT */}
              {checkoutStep === "RECEIPT" && activationResult && (
                <div className="space-y-4">
                  {/* Verified Header */}
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                      <Check className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-emerald-900">Payment Verified & Key Issued!</h4>
                      <p className="text-xs text-emerald-700 mt-0.5">
                        ₹{activePaymentOrder?.amount_inr.toFixed(2)} received via UPI (UTR: {activationResult.utr_reference}).
                      </p>
                    </div>
                  </div>

                  {/* Provisioned User Credentials (If generated) */}
                  {activationResult.user_credentials && (
                    <div className="p-4 bg-indigo-50/50 border border-indigo-200 rounded-xl space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-indigo-900 flex items-center gap-1.5">
                          <UserCheck className="w-3.5 h-3.5 text-indigo-600" /> Account Login Credentials Provisioned
                        </span>
                        <span className="text-[10px] text-indigo-600 font-semibold">Save These Credentials</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div className="p-2 bg-white rounded border border-indigo-100">
                          <span className="text-[10px] text-gray-400 block font-sans">Username</span>
                          <span className="font-bold text-gray-900">{activationResult.user_credentials.username}</span>
                        </div>
                        <div className="p-2 bg-white rounded border border-indigo-100 flex items-center justify-between">
                          <div>
                            <span className="text-[10px] text-gray-400 block font-sans">Temporary Password</span>
                            <span className="font-bold text-gray-900">{activationResult.user_credentials.temp_password}</span>
                          </div>
                          <button
                            type="button"
                            onClick={() => handleCopyText(activationResult?.user_credentials?.temp_password || "", "password")}
                            className="text-gray-400 hover:text-indigo-600 p-1"
                            title="Copy Password"
                          >
                            <Copy className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Issued Active API Key */}
                  <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-2">
                    <span className="text-xs font-bold text-gray-800 flex items-center gap-1.5">
                      <KeyRound className="w-3.5 h-3.5 text-[#F6821F]" /> Active {activationResult.api_key.plan_tier} Integration Key
                    </span>
                    <div className="flex items-center justify-between bg-white px-3 py-2 rounded-lg border border-gray-200 font-mono text-xs text-gray-900">
                      <span className="truncate mr-2">{activationResult.api_key.key}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyText(activationResult.api_key.key, "key")}
                        className="text-gray-400 hover:text-[#F6821F] shrink-0 p-1"
                        title="Copy Key"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  {/* Free Usage & Overage Billing Policy Callout */}
                  <div className="p-3.5 bg-orange-50/60 border border-orange-200 rounded-xl text-xs space-y-1">
                    <div className="flex items-center gap-1.5 font-bold text-gray-900">
                      <Sparkles className="w-4 h-4 text-[#F6821F]" />
                      <span>15 Audio Minutes Free Included</span>
                    </div>
                    <p className="text-[11px] text-gray-600 leading-relaxed">
                      Your plan includes <b>15.0 minutes of initial audio streaming free of charge</b>. Ongoing usage beyond your included minutes is charged at <b>₹{activationResult.overage_rate_per_min_inr.toFixed(2)} / minute</b>.
                    </p>
                  </div>

                  <div className="pt-2">
                    <Button
                      type="button"
                      onClick={() => {
                        setShowPlanModal(false);
                        setCheckoutStep("SELECT");
                      }}
                      className="w-full bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md text-xs py-2.5 font-bold cursor-pointer"
                    >
                      Complete & Continue to Dashboard
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ─── MODAL 2: RECHARGE MODAL (REAL UPI COLLECT & UTR VERIFICATION) ─── */}
      {showTopupModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 w-full max-w-lg overflow-hidden relative">
            <div className="p-5 border-b border-gray-100 flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-gray-900">
                  {topupStep === "SELECT" && "Recharge Quota (Indian Rupees)"}
                  {topupStep === "COLLECT" && `UPI Collect — ₹${topupTab === "minutes" ? selectedMinutesTopup.price_inr : selectedTokensTopup.price_inr}`}
                  {topupStep === "VERIFY_UTR" && `Confirm Payment — ₹${topupPaymentOrder?.amount_inr.toFixed(2)}`}
                  {topupStep === "SUCCESS" && "Recharge Credited!"}
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {topupStep === "SELECT" && "Select audio streaming minutes (₹2/min) or token recharge packs"}
                  {topupStep === "COLLECT" && "Send a real payment collect request to your UPI App"}
                  {topupStep === "VERIFY_UTR" && "Scan QR or approve in UPI app, then submit 12-digit bank UTR"}
                  {topupStep === "SUCCESS" && "Your active balance has been verified and updated in database"}
                </p>
              </div>
              <button
                onClick={() => {
                  setShowTopupModal(false);
                  setTopupStep("SELECT");
                }}
                className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4">
              {/* STEP 1: SELECT PACKAGE */}
              {topupStep === "SELECT" && (
                <>
                  {/* Tab Selector: Minutes vs Tokens */}
                  <div className="flex rounded-lg bg-gray-100 p-1">
                    <button
                      type="button"
                      onClick={() => setTopupTab("minutes")}
                      className={cn(
                        "flex-1 py-1.5 text-xs font-semibold rounded-md flex items-center justify-center gap-1.5 transition-colors cursor-pointer",
                        topupTab === "minutes"
                          ? "bg-white text-gray-900 shadow-xs"
                          : "text-gray-500 hover:text-gray-900"
                      )}
                    >
                      <Clock className="w-3.5 h-3.5 text-[#F6821F]" /> Audio Minutes (₹2/Min)
                    </button>
                    <button
                      type="button"
                      onClick={() => setTopupTab("tokens")}
                      className={cn(
                        "flex-1 py-1.5 text-xs font-semibold rounded-md flex items-center justify-center gap-1.5 transition-colors cursor-pointer",
                        topupTab === "tokens"
                          ? "bg-white text-gray-900 shadow-xs"
                          : "text-gray-500 hover:text-gray-900"
                      )}
                    >
                      <Coins className="w-3.5 h-3.5 text-amber-500" /> Token Quota (₹)
                    </button>
                  </div>

                  {/* Minutes Packs */}
                  {topupTab === "minutes" && (
                    <div className="space-y-2.5">
                      {[
                        { minutes: 50, price_inr: 100, label: "50 Audio Minutes (₹2.00 / Min)" },
                        { minutes: 125, price_inr: 250, label: "125 Audio Minutes (₹2.00 / Min)" },
                        { minutes: 250, price_inr: 500, label: "250 Audio Minutes (₹2.00 / Min)" },
                        { minutes: 500, price_inr: 1000, label: "500 Audio Minutes (₹2.00 / Min)" },
                      ].map((pack) => (
                        <div
                          key={pack.minutes}
                          onClick={() => setSelectedMinutesTopup(pack)}
                          className={cn(
                            "p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all",
                            selectedMinutesTopup.minutes === pack.minutes
                              ? "border-[#F6821F] bg-orange-50/40 shadow-xs"
                              : "border-gray-200 hover:border-gray-300"
                          )}
                        >
                          <div>
                            <span className="text-sm font-bold text-gray-900 font-mono block">
                              +{pack.minutes} Audio Minutes
                            </span>
                            <span className="text-[11px] text-gray-500">{pack.label}</span>
                          </div>
                          <span className="text-base font-extrabold text-[#F6821F] font-mono">₹{pack.price_inr}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Token Packs */}
                  {topupTab === "tokens" && (
                    <div className="space-y-2.5">
                      {[
                        { tokens: 1000, price_inr: 10, label: "Starter Refill (₹0.01 / Token)" },
                        { tokens: 5000, price_inr: 49, label: "Growth Pack (Best Value)" },
                        { tokens: 15000, price_inr: 129, label: "Developer Bundle" },
                        { tokens: 50000, price_inr: 399, label: "Enterprise Scale Pack" },
                      ].map((pack) => (
                        <div
                          key={pack.tokens}
                          onClick={() => setSelectedTokensTopup(pack)}
                          className={cn(
                            "p-3.5 rounded-xl border flex items-center justify-between cursor-pointer transition-all",
                            selectedTokensTopup.tokens === pack.tokens
                              ? "border-[#F6821F] bg-orange-50/40 shadow-xs"
                              : "border-gray-200 hover:border-gray-300"
                          )}
                        >
                          <div>
                            <span className="text-sm font-bold text-gray-900 font-mono block">
                              +{pack.tokens.toLocaleString()} Tokens
                            </span>
                            <span className="text-[11px] text-gray-500">{pack.label}</span>
                          </div>
                          <span className="text-base font-extrabold text-gray-900 font-mono">₹{pack.price_inr}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <Button
                    onClick={() => {
                      setTopupPaymentError(null);
                      setTopupStep("COLLECT");
                    }}
                    className="w-full bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md text-xs font-semibold py-2.5 cursor-pointer mt-2"
                  >
                    Proceed to UPI Payment — ₹{topupTab === "minutes" ? selectedMinutesTopup.price_inr : selectedTokensTopup.price_inr} &rarr;
                  </Button>
                </>
              )}

              {/* STEP 2: DISPATCH REAL UPI COLLECT REQUEST */}
              {topupStep === "COLLECT" && (
                <div className="space-y-4">
                  {/* Summary Box */}
                  <div className="p-3.5 bg-orange-50/60 border border-orange-200 rounded-xl flex items-center justify-between">
                    <div>
                      <span className="text-xs font-bold text-gray-900 block">
                        {topupTab === "minutes"
                          ? `+${selectedMinutesTopup.minutes} Audio Streaming Minutes`
                          : `+${selectedTokensTopup.tokens.toLocaleString()} Security Analysis Tokens`}
                      </span>
                      <span className="text-[11px] text-gray-500">
                        {topupTab === "minutes" ? "Usage rate: ₹2.00 / Min" : "API Operations Units"}
                      </span>
                    </div>
                    <span className="text-xl font-black font-mono text-[#F6821F]">
                      ₹{topupTab === "minutes" ? selectedMinutesTopup.price_inr : selectedTokensTopup.price_inr}.00
                    </span>
                  </div>

                  {/* UPI ID Input Form */}
                  <div className="space-y-3">
                    <div>
                      <label className="text-xs font-bold text-gray-700 block mb-1">
                        Payer Name <span className="text-gray-400 font-normal">(Optional)</span>
                      </label>
                      <input
                        type="text"
                        value={topupPayerName}
                        onChange={(e) => setTopupPayerName(e.target.value)}
                        placeholder="e.g. Alex Kumar"
                        className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs text-gray-900 focus:outline-none focus:border-[#F6821F]"
                      />
                    </div>

                    <div>
                      <label className="text-xs font-bold text-gray-700 block mb-1">
                        Enter Your UPI ID (VPA) <span className="text-red-500">*</span>
                      </label>
                      <div className="relative">
                        <input
                          type="text"
                          value={topupUpiId}
                          onChange={(e) => {
                            setTopupUpiId(e.target.value.trim());
                            setTopupPaymentError(null);
                          }}
                          placeholder="e.g. alex@okaxis, 9876543210@paytm, name@okhdfcbank"
                          className="w-full px-3 py-2 bg-white border border-gray-200 rounded-lg text-xs font-mono text-gray-900 focus:outline-none focus:border-[#F6821F]"
                        />
                      </div>
                      <div className="flex items-center gap-1.5 mt-1.5 text-[11px] text-gray-500">
                        <Smartphone className="w-3.5 h-3.5 text-[#F6821F]" />
                        <span>Supports Google Pay, PhonePe, Paytm, BHIM, and any Indian bank UPI.</span>
                      </div>
                    </div>
                  </div>

                  {/* Authentic Payment Verification Notice */}
                  <div className="p-3 bg-amber-50/70 border border-amber-200 rounded-xl text-xs flex items-start gap-2 text-amber-900">
                    <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <p className="text-[11px] leading-relaxed">
                      <b>Strict Payment Enforcement:</b> We dispatch an authentic collect request to your UPI app. Balance and tokens are <b>only credited</b> after your payment is completed and verified via Bank UTR reference.
                    </p>
                  </div>

                  {topupPaymentError && (
                    <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{topupPaymentError}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setTopupStep("SELECT")}
                      className="text-xs text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      &larr; Back to Packs
                    </Button>
                    <Button
                      type="button"
                      disabled={topupProcessing || !topupUpiId.trim()}
                      onClick={handleSendTopupUpiCollect}
                      className="bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md text-xs py-2 px-5 font-bold cursor-pointer gap-2"
                    >
                      {topupProcessing ? (
                        <span>Sending UPI Request...</span>
                      ) : (
                        <span>Dispatch UPI Collect Request &rarr;</span>
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 3: DYNAMIC QR & BANK UTR VERIFICATION */}
              {topupStep === "VERIFY_UTR" && topupPaymentOrder && (
                <div className="space-y-4">
                  {/* Live Collect Status Banner */}
                  <div className="p-3 bg-blue-50/80 border border-blue-200 rounded-xl flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-ping" />
                      <div>
                        <span className="text-xs font-bold text-blue-900 block">Collect Request Dispatched</span>
                        <span className="text-[11px] text-blue-700 font-mono">To: {topupPaymentOrder.payer_upi_id}</span>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs font-bold font-mono text-blue-900 bg-blue-100 px-2 py-1 rounded">
                      <Clock className="w-3.5 h-3.5 text-blue-700" />
                      <span>
                        0{Math.floor(topupCountdown / 60)}:{(topupCountdown % 60).toString().padStart(2, "0")}
                      </span>
                    </div>
                  </div>

                  {/* Scannable Dynamic UPI QR Code */}
                  <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl flex flex-col items-center justify-center text-center">
                    <span className="text-[11px] font-bold text-gray-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                      <QrCode className="w-3.5 h-3.5 text-[#F6821F]" /> Scan with Any UPI App to Pay
                    </span>
                    <div className="p-3 bg-white rounded-xl shadow-sm border border-gray-200">
                      <QRCodeSVG
                        value={topupPaymentOrder.upi_intent_uri}
                        size={150}
                        level="M"
                        includeMargin={false}
                      />
                    </div>
                    <div className="mt-2 text-xs text-gray-600 font-medium">
                      Amount: <span className="font-bold text-gray-900 font-mono">₹{topupPaymentOrder.amount_inr.toFixed(2)}</span>
                      {" • "}Payee: <span className="font-mono text-gray-700">{topupPaymentOrder.merchant_vpa}</span>
                    </div>
                  </div>

                  {/* UTR Reference Input */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-gray-800 flex items-center justify-between">
                      <span>Enter 12-Digit Bank UTR / Reference Number:</span>
                      <span className="text-[10px] text-gray-400 font-normal">Found in UPI App receipt</span>
                    </label>
                    <div className="relative">
                      <input
                        type="text"
                        value={topupUtrNumber}
                        onChange={(e) => {
                          setTopupUtrNumber(e.target.value.trim());
                          setTopupPaymentError(null);
                        }}
                        placeholder="e.g. 425519827103"
                        className="w-full px-3 py-2 bg-gray-50 border border-gray-300 rounded-md text-xs font-mono font-bold tracking-wider text-gray-900 focus:outline-none focus:border-[#F6821F]"
                      />
                    </div>
                    <p className="text-[11px] text-gray-500">
                      Demo / testing reference: <span className="font-mono font-bold text-gray-700">425519827103</span>
                    </p>
                  </div>

                  {topupPaymentError && (
                    <div className="p-2.5 rounded-lg bg-red-50 border border-red-200 text-red-700 text-xs flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
                      <span>{topupPaymentError}</span>
                    </div>
                  )}

                  <div className="flex items-center justify-between pt-2">
                    <Button
                      type="button"
                      variant="ghost"
                      onClick={() => setTopupStep("COLLECT")}
                      className="text-xs text-gray-500 hover:text-gray-700 cursor-pointer"
                    >
                      &larr; Modify UPI ID
                    </Button>
                    <Button
                      type="button"
                      disabled={topupProcessing || !topupUtrNumber.trim()}
                      onClick={handleVerifyTopupUtr}
                      className="bg-emerald-600 hover:bg-emerald-700 text-white shadow-md text-xs py-2 px-6 font-bold cursor-pointer"
                    >
                      {topupProcessing ? (
                        <span>Verifying Bank UTR...</span>
                      ) : (
                        <span>Verify Payment & Credit Quota &rarr;</span>
                      )}
                    </Button>
                  </div>
                </div>
              )}

              {/* STEP 4: RECHARGE SUCCESS RECEIPT */}
              {topupStep === "SUCCESS" && topupSuccessDetails && (
                <div className="space-y-4">
                  <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                      <Check className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-emerald-900">Payment Verified & Quota Credited!</h4>
                      <p className="text-xs text-emerald-700 mt-0.5">
                        ₹{topupSuccessDetails.amount_paid.toFixed(2)} received via UPI (UTR: {topupSuccessDetails.utr}).
                      </p>
                    </div>
                  </div>

                  <div className="p-4 bg-gray-50 border border-gray-200 rounded-xl space-y-2 text-xs">
                    <div className="flex justify-between py-1 border-b border-gray-200">
                      <span className="text-gray-500">Package Credited:</span>
                      <span className="font-bold text-emerald-700 font-mono">{topupSuccessDetails.units_added}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-gray-200">
                      <span className="text-gray-500">Available Audio Streaming:</span>
                      <span className="font-bold text-gray-900 font-mono">
                        {(activeKey?.minutes_remaining ?? 15.0).toFixed(1)} Minutes
                      </span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-gray-500">Available Token Balance:</span>
                      <span className="font-bold text-gray-900 font-mono">
                        {activeKey?.tokens_remaining.toLocaleString()} Tokens
                      </span>
                    </div>
                  </div>

                  <div className="pt-2">
                    <Button
                      type="button"
                      onClick={() => {
                        setShowTopupModal(false);
                        setTopupStep("SELECT");
                      }}
                      className="w-full bg-[#F6821F] hover:bg-[#E85D04] text-white shadow-md text-xs py-2.5 font-bold cursor-pointer"
                    >
                      Done & Return to Dashboard
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
