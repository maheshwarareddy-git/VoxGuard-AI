"use client";

import { useState, useEffect, useRef } from "react";
import {
  Search,
  Bell,
  ChevronRight,
  Plus,
  UserCheck,
  UserX,
  Mic,
  Fingerprint,
  Trash2,
  TrendingUp,
  Shield,
  X,
  Sparkles,
  CheckCircle2,
  Cpu,
  RefreshCw,
  Upload,
  Square,
  AlertCircle,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  getIdentities,
  enrollVoiceprint,
  enrollVoiceWithAudio,
  deleteIdentity,
  clearAllIdentities,
  VoiceProfile,
} from "@/lib/api";

const statusConfig = {
  ACTIVE: { label: "Active", color: "text-emerald-700", bg: "bg-emerald-50", border: "border-emerald-200" },
  PENDING: { label: "Pending", color: "text-amber-700", bg: "bg-amber-50", border: "border-amber-200" },
  REVOKED: { label: "Revoked", color: "text-red-700", bg: "bg-red-50", border: "border-red-200" },
};

const qualityConfig = {
  HIGH: { label: "High Precision", color: "text-emerald-700", bg: "bg-emerald-50" },
  MEDIUM: { label: "Standard", color: "text-amber-700", bg: "bg-amber-50" },
  LOW: { label: "Low Precision", color: "text-red-700", bg: "bg-red-50" },
};

export default function IdentitiesPage() {
  const [profiles, setProfiles] = useState<VoiceProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState<"ALL" | "ACTIVE" | "PENDING" | "REVOKED">("ALL");
  const [searchQuery, setSearchQuery] = useState("");

  // Modal state for enrolling new identity
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDept, setNewDept] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordedBlob, setRecordedBlob] = useState<Blob | null>(null);
  const [enrollStep, setEnrollStep] = useState<"IDLE" | "EXTRACTING" | "DONE">("IDLE");

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  const fetchRealIdentities = async () => {
    setLoading(true);
    try {
      const data = await getIdentities(filterStatus, searchQuery);
      setProfiles(data);
    } catch (err) {
      console.error("Failed to load identities from database:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRealIdentities();
  }, [filterStatus, searchQuery]);

  const stats = {
    total: profiles.length,
    active: profiles.filter((p) => p.status === "ACTIVE").length,
    pending: profiles.filter((p) => p.status === "PENDING").length,
    avgConfidence: profiles.length
      ? Math.round(profiles.reduce((sum, p) => sum + p.confidence, 0) / profiles.length)
      : 0,
  };

  // Start real microphone recording for voice enrollment
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        setRecordedBlob(blob);
        setSelectedFile(null);
        stream.getTracks().forEach((t) => t.stop());
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      alert("Microphone access unavailable. You can upload an audio file instead.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleStartEnrollment = async () => {
    if (!newName.trim() || !newDept.trim()) {
      alert("Please provide both name and department for voiceprint registration.");
      return;
    }

    setEnrollStep("EXTRACTING");
    try {
      let created: VoiceProfile;
      const audioToUpload = selectedFile || recordedBlob;

      if (audioToUpload) {
        created = await enrollVoiceWithAudio(newName.trim(), newDept.trim(), audioToUpload);
      } else {
        created = await enrollVoiceprint(newName.trim(), newDept.trim());
      }

      setEnrollStep("DONE");
      setProfiles((prev) => [created, ...prev]);
    } catch (err) {
      console.error("Enrollment failed:", err);
      alert("Failed to enroll voiceprint to backend database.");
      setEnrollStep("IDLE");
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Delete voiceprint ${id}? This action removes it from biometric matching.`)) return;
    try {
      await deleteIdentity(id);
      setProfiles((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      console.error("Failed to delete identity:", err);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Are you sure you want to clear all enrolled voice profiles?")) return;
    try {
      await clearAllIdentities();
      setProfiles([]);
    } catch (err) {
      console.error("Failed to clear identities:", err);
    }
  };

  const resetModal = () => {
    setIsModalOpen(false);
    setNewName("");
    setNewDept("");
    setSelectedFile(null);
    setRecordedBlob(null);
    setIsRecording(false);
    setEnrollStep("IDLE");
  };

  return (
    <>
      {/* Top Navbar */}
      <nav className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 z-20 sticky top-0">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <a href="/" className="hover:text-[#F6821F]">VoxGuard SOC</a>
          <ChevronRight className="w-4 h-4" />
          <span className="text-gray-900 font-medium">Speaker Voiceprint Registry</span>
        </div>
        <div className="flex items-center gap-4">
          <button
            onClick={fetchRealIdentities}
            className="text-gray-500 hover:text-gray-900 p-1.5 rounded-md hover:bg-gray-100"
            title="Refresh database"
          >
            <RefreshCw className={cn("w-4 h-4", loading ? "animate-spin text-[#F6821F]" : "")} />
          </button>
          <button className="text-gray-500 hover:text-gray-900 relative">
            <Bell className="w-5 h-5" />
          </button>
        </div>
      </nav>

      {/* Page Header */}
      <header className="bg-white border-b border-gray-200 py-6 px-6 sm:px-10 shadow-sm">
        <div className="max-w-[1400px] mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Speaker Voiceprint Registry</h1>
              <p className="text-sm text-gray-500 mt-1">
                Real ECAPA-TDNN 192-dimensional embeddings stored in SQLite for biometric matching
              </p>
            </div>
            <div className="flex items-center gap-3">
              {profiles.length > 0 && (
                <Button
                  onClick={handleClearAll}
                  variant="outline"
                  size="sm"
                  className="text-xs text-red-600 hover:bg-red-50 hover:border-red-300"
                >
                  <Trash2 className="w-3.5 h-3.5 mr-1" /> Clear Registry
                </Button>
              )}
              <Button
                onClick={() => setIsModalOpen(true)}
                className="bg-[#F6821F] hover:bg-[#E85D04] text-white gap-2 text-sm font-medium shadow-sm cursor-pointer"
              >
                <Plus className="w-4 h-4" /> Enroll Voiceprint
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="flex-1 w-full max-w-[1400px] mx-auto p-6 sm:p-10 space-y-6">
        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-gray-100 rounded-lg"><Fingerprint className="w-5 h-5 text-gray-600" /></div>
              <div>
                <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
                <p className="text-xs text-gray-500">Database Profiles</p>
              </div>
            </div>
          </div>
          <div className="bg-white border border-emerald-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-emerald-50 rounded-lg"><UserCheck className="w-5 h-5 text-emerald-600" /></div>
              <div>
                <p className="text-2xl font-bold text-emerald-700">{stats.active}</p>
                <p className="text-xs text-gray-500">Active High-Trust Profiles</p>
              </div>
            </div>
          </div>
          <div className="bg-white border border-amber-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-amber-50 rounded-lg"><UserX className="w-5 h-5 text-amber-600" /></div>
              <div>
                <p className="text-2xl font-bold text-amber-700">{stats.pending}</p>
                <p className="text-xs text-gray-500">Pending Audio Samples</p>
              </div>
            </div>
          </div>
          <div className="bg-white border border-blue-200 rounded-lg p-4 shadow-sm">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-50 rounded-lg"><TrendingUp className="w-5 h-5 text-blue-600" /></div>
              <div>
                <p className="text-2xl font-bold text-blue-700">{stats.avgConfidence}%</p>
                <p className="text-xs text-gray-500">Mean Match Confidence</p>
              </div>
            </div>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px]">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search by name, department, or VP ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9 pr-4 py-1.5 w-full bg-gray-50 border border-gray-200 focus:bg-white focus:border-[#F6821F] rounded-md text-sm text-gray-900 focus:outline-none focus:ring-1 focus:ring-[#F6821F] transition-all"
            />
          </div>
          <div className="flex items-center gap-2">
            {(["ALL", "ACTIVE", "PENDING", "REVOKED"] as const).map((s) => (
              <Button
                key={s}
                variant="outline"
                size="sm"
                onClick={() => setFilterStatus(s)}
                className={cn(
                  "text-xs font-medium rounded-md transition-all cursor-pointer",
                  filterStatus === s
                    ? s === "ALL"
                      ? "bg-gray-900 text-white border-gray-900"
                      : s === "ACTIVE"
                      ? "bg-emerald-50 text-emerald-700 border-emerald-500"
                      : s === "PENDING"
                      ? "bg-amber-50 text-amber-700 border-amber-500"
                      : "bg-red-50 text-red-700 border-red-500"
                    : ""
                )}
              >
                {s === "ALL" ? "All Profiles" : statusConfig[s].label}
              </Button>
            ))}
          </div>
        </div>

        {/* Profile Cards Grid */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {loading ? (
            <div className="col-span-full py-16 text-center text-gray-400">
              <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-2 text-[#F6821F]" />
              Querying voice embeddings from SQLite...
            </div>
          ) : profiles.length === 0 ? (
            <div className="col-span-full py-16 text-center bg-white border border-gray-200 rounded-xl p-8 shadow-sm">
              <Fingerprint className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <h3 className="text-base font-semibold text-gray-800">No Enrolled Voiceprints</h3>
              <p className="text-xs text-gray-500 max-w-md mx-auto mt-1 mb-4">
                No authorized voice profiles are registered in SQLite yet. Enroll authorized personnel with audio samples so the ECAPA-TDNN engine can perform biometric speaker verification.
              </p>
              <Button
                onClick={() => setIsModalOpen(true)}
                className="bg-[#F6821F] hover:bg-[#E85D04] text-white text-xs gap-1.5"
              >
                <Plus className="w-3.5 h-3.5" /> Enroll First Voiceprint
              </Button>
            </div>
          ) : (
            profiles.map((profile) => {
              const s = statusConfig[profile.status];
              const q = qualityConfig[profile.embeddingQuality];
              return (
                <div
                  key={profile.id}
                  className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md hover:border-[#F6821F]/40 transition-all duration-200 overflow-hidden group flex flex-col justify-between"
                >
                  <div className="p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#F6821F] to-[#E85D04] flex items-center justify-center text-white text-sm font-bold shrink-0 shadow-sm">
                        {profile.name.split(" ").map((n) => n[0]).join("")}
                      </div>
                      <div className="flex items-center gap-1">
                        <span className="text-[10px] font-mono text-gray-400">{profile.id}</span>
                        <button
                          onClick={() => handleDelete(profile.id)}
                          className="text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity p-1"
                          title="Delete voiceprint"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                    <h3 className="font-semibold text-gray-900 text-sm">{profile.name}</h3>
                    <p className="text-xs text-gray-500 mb-3">{profile.department}</p>

                    <div className="flex items-center gap-2 mb-4">
                      <Badge className={cn("text-[10px] font-medium", s.bg, s.color, s.border)}>{s.label}</Badge>
                      <Badge className={cn("text-[10px] font-medium", q.bg, q.color)}>
                        <Shield className="w-2.5 h-2.5 mr-0.5" /> {q.label}
                      </Badge>
                    </div>

                    <div className="space-y-1.5 text-xs text-gray-600 pt-3 border-t border-gray-100">
                      <div className="flex justify-between">
                        <span className="text-gray-400">Enrolled:</span>
                        <span>{profile.enrolledDate}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Last Verified:</span>
                        <span>{profile.lastVerified}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-400">Samples:</span>
                        <span>{profile.samples} sessions</span>
                      </div>
                    </div>
                  </div>

                  <div className="px-5 py-3 bg-gray-50 border-t border-gray-100 flex items-center justify-between">
                    <span className="text-xs text-gray-500">Cosine Confidence</span>
                    <span className="text-xs font-bold text-emerald-700">{profile.confidence}%</span>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </main>

      {/* Voice Enrollment Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in duration-200">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-orange-50 rounded-lg">
                  <Fingerprint className="w-5 h-5 text-[#F6821F]" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">Enroll Speaker Voiceprint</h3>
                  <p className="text-xs text-gray-500">Compute 192-dim acoustic vector for database matching</p>
                </div>
              </div>
              <button onClick={resetModal} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            {enrollStep === "IDLE" && (
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    placeholder="e.g. Dr. Jane Smith"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-gray-700 mb-1">Department / Organization Role</label>
                  <input
                    type="text"
                    value={newDept}
                    onChange={(e) => setNewDept(e.target.value)}
                    placeholder="e.g. Treasury Operations / Executive Office"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:border-[#F6821F] focus:ring-1 focus:ring-[#F6821F]"
                  />
                </div>

                <div className="pt-2 border-t border-gray-100 space-y-3">
                  <label className="block text-xs font-semibold text-gray-700">Voice Sample Intake</label>
                  
                  {/* Voice recording or audio upload */}
                  <div className="grid grid-cols-2 gap-3">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={isRecording ? stopRecording : startRecording}
                      className={cn(
                        "text-xs font-medium gap-1.5 h-16 flex flex-col items-center justify-center cursor-pointer",
                        isRecording ? "bg-red-50 text-red-700 border-red-400 animate-pulse" : "hover:border-[#F6821F]"
                      )}
                    >
                      {isRecording ? <Square className="w-4 h-4 text-red-600" /> : <Mic className="w-4 h-4 text-[#F6821F]" />}
                      <span>{isRecording ? "Stop Recording" : "Record Mic"}</span>
                    </Button>

                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-xs font-medium gap-1.5 h-16 flex flex-col items-center justify-center hover:border-[#F6821F] cursor-pointer"
                    >
                      <Upload className="w-4 h-4 text-[#F6821F]" />
                      <span>{selectedFile ? selectedFile.name.slice(0, 15) : "Upload Audio (.wav)"}</span>
                    </Button>
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={(e) => {
                        if (e.target.files?.[0]) {
                          setSelectedFile(e.target.files[0]);
                          setRecordedBlob(null);
                        }
                      }}
                      accept="audio/*"
                      className="hidden"
                    />
                  </div>

                  {(recordedBlob || selectedFile) && (
                    <div className="flex items-center gap-2 p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800">
                      <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>Audio sample ready: {selectedFile ? selectedFile.name : "Microphone recording captured (WAV)"}</span>
                    </div>
                  )}
                </div>

                <div className="flex justify-end gap-3 pt-3">
                  <Button variant="ghost" size="sm" onClick={resetModal}>Cancel</Button>
                  <Button
                    onClick={handleStartEnrollment}
                    disabled={!newName.trim() || !newDept.trim()}
                    className="bg-[#F6821F] hover:bg-[#E85D04] text-white text-xs gap-1.5 cursor-pointer"
                  >
                    <Cpu className="w-3.5 h-3.5" /> Extract Embedding & Save
                  </Button>
                </div>
              </div>
            )}

            {enrollStep === "EXTRACTING" && (
              <div className="py-8 text-center space-y-3">
                <RefreshCw className="w-8 h-8 animate-spin mx-auto text-[#F6821F]" />
                <p className="text-sm font-semibold text-gray-800">Extracting 192-Dim Acoustic Embedding...</p>
                <p className="text-xs text-gray-500">Computing FFT spectrogram filters and saving vector to SQLite...</p>
              </div>
            )}

            {enrollStep === "DONE" && (
              <div className="py-6 text-center space-y-4">
                <CheckCircle2 className="w-12 h-12 text-emerald-600 mx-auto" />
                <div>
                  <h4 className="text-base font-bold text-gray-900">Voiceprint Successfully Enrolled!</h4>
                  <p className="text-xs text-gray-500 mt-1">Profile saved to SQLite and active for real-time verification.</p>
                </div>
                <Button onClick={resetModal} className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs w-full">
                  Close
                </Button>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}
