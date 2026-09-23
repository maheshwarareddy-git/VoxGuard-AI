"use client";

import React, { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import {
  Shield,
  Lock,
  User,
  Mail,
  UserCheck,
  Eye,
  EyeOff,
  AlertCircle,
  ArrowRight,
  Fingerprint,
} from "lucide-react";

export default function LoginPage() {
  const { login, register } = useAuth();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Login form state
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register form state
  const [regFullName, setRegFullName] = useState("");
  const [regUsername, setRegUsername] = useState("");
  const [regEmail, setRegEmail] = useState("");
  const [regPassword, setRegPassword] = useState("");
  const [regRole, setRegRole] = useState("Lead SOC Analyst");

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!loginUsername.trim() || !loginPassword) {
      setErrorMsg("Please provide both username/email and password.");
      return;
    }

    setSubmitting(true);
    try {
      await login({
        username: loginUsername.trim(),
        password: loginPassword,
      });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to authenticate with local database.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!regFullName.trim() || !regUsername.trim() || !regEmail.trim() || !regPassword) {
      setErrorMsg("Please fill in all required registration fields.");
      return;
    }

    if (regPassword.length < 6) {
      setErrorMsg("Password must be at least 6 characters long.");
      return;
    }

    setSubmitting(true);
    try {
      await register({
        full_name: regFullName.trim(),
        username: regUsername.trim(),
        email: regEmail.trim(),
        password: regPassword,
        role: regRole,
      });
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrorMsg(err.message);
      } else {
        setErrorMsg("Failed to register account in local database.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen w-full flex flex-col justify-between bg-[#080B13] text-gray-100 relative overflow-hidden selection:bg-[#F6821F]/30 selection:text-white">
      {/* Dynamic Background Effects */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden">
        {/* Glowing gradient orbs */}
        <div className="absolute -top-40 -left-40 w-[600px] h-[600px] bg-[#F6821F]/10 rounded-full blur-[140px] opacity-70" />
        <div className="absolute top-1/2 -right-40 w-[500px] h-[500px] bg-blue-600/10 rounded-full blur-[140px] opacity-60" />
        <div className="absolute -bottom-40 left-1/3 w-[550px] h-[550px] bg-amber-500/8 rounded-full blur-[160px] opacity-50" />

        {/* Subtle grid pattern */}
        <div
          className="absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #fff 1px, transparent 0)`,
            backgroundSize: "32px 32px",
          }}
        />
      </div>

      {/* Top Bar Header */}
      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-[#F6821F] to-[#E85D04] p-0.5 shadow-lg shadow-orange-500/20 flex items-center justify-center">
            <div className="w-full h-full bg-gray-950/80 rounded-[10px] flex items-center justify-center">
              <Shield className="w-5 h-5 text-[#F6821F]" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-black tracking-tight text-white font-sans">
                Vox<span className="text-[#F6821F]">Guard</span>
              </span>
              <span className="text-[10px] font-mono tracking-wider px-2 py-0.5 bg-orange-500/10 border border-orange-500/20 text-[#F6821F] rounded-full uppercase">
                SOC Core
              </span>
            </div>
            <p className="text-[11px] text-gray-400 font-mono">AMVTF Multi-Modal Threat Response Engine</p>
          </div>
        </div>
      </header>

      {/* Main Authentication Container */}
      <main className="relative z-10 flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-md">
          {/* Card Container */}
          <div className="bg-[#0F1422]/90 border border-gray-800/80 rounded-2xl shadow-2xl shadow-black/80 backdrop-blur-xl p-7 sm:p-8 relative overflow-hidden transition-all duration-300">
            {/* Top glowing edge line */}
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-transparent via-[#F6821F] to-transparent opacity-80" />

            {/* Mode Switcher Tabs */}
            <div className="grid grid-cols-2 p-1 bg-gray-900/90 rounded-xl border border-gray-800/80 mb-6">
              <button
                type="button"
                onClick={() => {
                  setMode("login");
                  setErrorMsg(null);
                }}
                className={`py-2 px-3 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                  mode === "login"
                    ? "bg-[#F6821F] text-white shadow-md shadow-orange-500/20 font-semibold"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                <Fingerprint className="w-3.5 h-3.5" />
                <span>Analyst Sign In</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode("register");
                  setErrorMsg(null);
                }}
                className={`py-2 px-3 text-xs font-medium rounded-lg transition-all flex items-center justify-center gap-1.5 ${
                  mode === "register"
                    ? "bg-[#F6821F] text-white shadow-md shadow-orange-500/20 font-semibold"
                    : "text-gray-400 hover:text-gray-200"
                }`}
              >
                <UserCheck className="w-3.5 h-3.5" />
                <span>Register Analyst</span>
              </button>
            </div>

            {/* Error Alert */}
            {errorMsg && (
              <div className="mb-5 p-3 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 text-xs flex items-start gap-2.5 animate-in fade-in duration-200">
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{errorMsg}</span>
              </div>
            )}

            {/* SIGN IN FORM */}
            {mode === "login" && (
              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1.5">
                    Analyst Identifier <span className="text-gray-500 font-mono">(Username or Email)</span>
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      type="text"
                      value={loginUsername}
                      onChange={(e) => setLoginUsername(e.target.value)}
                      placeholder="operator or email@voxguard.security"
                      required
                      className="w-full pl-9 pr-3 py-2.5 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    />
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="block text-xs font-medium text-gray-300">Security Password</label>
                    <span className="text-[11px] text-gray-500 font-mono">PBKDF2 SHA-256</span>
                  </div>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={loginPassword}
                      onChange={(e) => setLoginPassword(e.target.value)}
                      placeholder="••••••••••••"
                      required
                      className="w-full pl-9 pr-10 py-2.5 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-300"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-[#F6821F] to-[#E85D04] text-white font-medium text-sm flex items-center justify-center gap-2 hover:opacity-95 active:scale-[0.99] disabled:opacity-50 transition-all shadow-lg shadow-orange-500/25 cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Authenticating Locally...</span>
                    </>
                  ) : (
                    <>
                      <span>Authorize SOC Session</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            )}

            {/* REGISTER FORM */}
            {mode === "register" && (
              <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Full Name</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <User className="w-4 h-4" />
                    </div>
                    <input
                      type="text"
                      value={regFullName}
                      onChange={(e) => setRegFullName(e.target.value)}
                      placeholder="e.g. Sarah Connor"
                      required
                      className="w-full pl-9 pr-3 py-2 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-300 mb-1">Analyst ID / User</label>
                    <input
                      type="text"
                      value={regUsername}
                      onChange={(e) => setRegUsername(e.target.value)}
                      placeholder="sconnor"
                      required
                      className="w-full px-3 py-2 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-300 mb-1">Role</label>
                    <select
                      value={regRole}
                      onChange={(e) => setRegRole(e.target.value)}
                      className="w-full px-3 py-2 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    >
                      <option value="Lead SOC Analyst">Lead SOC Analyst</option>
                      <option value="Audio Forensics Specialist">Audio Forensics</option>
                      <option value="Threat Hunter">Threat Hunter</option>
                      <option value="AMVTF System Admin">AMVTF Admin</option>
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Corporate / Security Email</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <Mail className="w-4 h-4" />
                    </div>
                    <input
                      type="email"
                      value={regEmail}
                      onChange={(e) => setRegEmail(e.target.value)}
                      placeholder="sarah@voxguard.security"
                      required
                      className="w-full pl-9 pr-3 py-2 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-300 mb-1">Master Password</label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-gray-500">
                      <Lock className="w-4 h-4" />
                    </div>
                    <input
                      type={showPassword ? "text" : "password"}
                      value={regPassword}
                      onChange={(e) => setRegPassword(e.target.value)}
                      placeholder="Minimum 6 characters"
                      required
                      minLength={6}
                      className="w-full pl-9 pr-10 py-2 bg-gray-900/80 border border-gray-800 rounded-xl text-sm text-gray-100 placeholder-gray-500 focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F] transition-all"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-500 hover:text-gray-300"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={submitting}
                  className="w-full mt-2 py-3 px-4 rounded-xl bg-gradient-to-r from-[#F6821F] to-[#E85D04] text-white font-medium text-sm flex items-center justify-center gap-2 hover:opacity-95 active:scale-[0.99] disabled:opacity-50 transition-all shadow-lg shadow-orange-500/25 cursor-pointer"
                >
                  {submitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      <span>Writing to Local Database...</span>
                    </>
                  ) : (
                    <>
                      <span>Register & Launch SOC Access</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full text-center py-4 text-[11px] text-gray-500 font-mono border-t border-gray-800/40">
        VoxGuard EchoGuard AI &copy; 2026 &bull; AMVTF Security Engine
      </footer>
    </div>
  );
}
