"use client";

import { useState, useEffect, useRef, ChangeEvent } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ShieldAlert,
  ShieldCheck,
  Activity,
  MessageSquareWarning,
  PhoneOff,
  Search,
  Bell,
  ChevronRight,
  Radio,
  Mic,
  MicOff,
  AlertTriangle,
  Flame,
  CheckCircle2,
  XCircle,
  Sliders,
  Sparkles,
  Lock,
  UserCheck,
  Zap,
  Upload,
  RefreshCw,
  FileAudio,
  Fingerprint,
  PhoneCall,
  Send,
  AlertCircle,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  analyzeAudioUpload,
  analyzeLiveMic,
  saveCall,
  getIdentities,
  VoiceProfile,
  AudioAnalysisResponse,
} from "@/lib/api";

type RiskState = "IDLE" | "SAFE" | "WARNING" | "CRITICAL";

function downsampleBuffer(buffer: Float32Array, inputSampleRate: number, outputSampleRate = 16000): Float32Array {
  if (inputSampleRate === outputSampleRate) return buffer;
  const sampleRateRatio = inputSampleRate / outputSampleRate;
  const newLength = Math.round(buffer.length / sampleRateRatio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    const start = Math.floor(i * sampleRateRatio);
    const end = Math.min(buffer.length, Math.floor((i + 1) * sampleRateRatio));
    let sum = 0;
    for (let j = start; j < end; j++) {
      sum += buffer[j];
    }
    result[i] = sum / Math.max(1, end - start);
  }
  return result;
}

function encodeWavPcm16(samples: Float32Array, sampleRate = 16000): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  const writeString = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) {
      view.setUint8(offset + i, str.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // Mono
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true);
    offset += 2;
  }

  return new Blob([view], { type: "audio/wav" });
}

export default function HybridDashboard() {
  const [riskState, setRiskState] = useState<RiskState>("IDLE");
  const [isSimulating, setIsSimulating] = useState(false);
  const [isMicActive, setIsMicActive] = useState(false);
  const [micVolume, setMicVolume] = useState<number[]>(new Array(12).fill(10));
  const [callDuration, setCallDuration] = useState(0);
  const [actionExecuted, setActionExecuted] = useState(false);
  const [isPersisted, setIsPersisted] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // Registered database profiles
  const [enrolledProfiles, setEnrolledProfiles] = useState<VoiceProfile[]>([]);
  const [selectedTargetId, setSelectedTargetId] = useState<string>("");

  // Custom text input for threat testing
  const [customTranscript, setCustomTranscript] = useState("");
  const [liveSpeechText, setLiveSpeechText] = useState("");
  const liveSpeechTextRef = useRef<string>("");

  // Active analysis data from backend
  const [currentScenario, setCurrentScenario] = useState<AudioAnalysisResponse | null>(null);

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const micStreamRef = useRef<MediaStream | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const recognitionRef = useRef<any>(null);
  const liveIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const pcmBufferRef = useRef<Float32Array[]>([]);
  const scriptProcessorRef = useRef<ScriptProcessorNode | null>(null);

  // Load real registered voiceprints from SQLite
  useEffect(() => {
    async function loadProfiles() {
      try {
        const data = await getIdentities();
        setEnrolledProfiles(data);
      } catch (err) {
        console.error("Failed to load registered identities:", err);
      }
    }
    loadProfiles();
  }, []);

  // Call duration timer
  useEffect(() => {
    let timer: NodeJS.Timeout;
    if (isSimulating || isMicActive) {
      timer = setInterval(() => {
        setCallDuration((prev) => prev + 1);
      }, 1000);
    } else {
      setCallDuration(0);
    }
    return () => clearInterval(timer);
  }, [isSimulating, isMicActive]);

  // Real Microphone Audio + Real Web Speech API transcription + Real-time Streaming
  const toggleMicrophone = async () => {
    if (isMicActive) {
      // Stop mic streaming
      if (liveIntervalRef.current) {
        clearInterval(liveIntervalRef.current);
        liveIntervalRef.current = null;
      }
      if (scriptProcessorRef.current) {
        try {
          scriptProcessorRef.current.disconnect();
        } catch {}
        scriptProcessorRef.current = null;
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {}
      }
      if (micStreamRef.current) {
        micStreamRef.current.getTracks().forEach((track) => track.stop());
      }
      const currentSr = audioContextRef.current?.sampleRate || 16000;
      if (audioContextRef.current) {
        try {
          audioContextRef.current.close();
        } catch {}
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      setIsMicActive(false);

      // Final full-session audio analysis and persist to audit trail
      if (pcmBufferRef.current.length > 0) {
        let totalLen = 0;
        for (const chunk of pcmBufferRef.current) totalLen += chunk.length;
        const merged = new Float32Array(totalLen);
        let offset = 0;
        for (const chunk of pcmBufferRef.current) {
          merged.set(chunk, offset);
          offset += chunk.length;
        }
        const pcm16k = downsampleBuffer(merged, currentSr, 16000);
        const fullWavBlob = encodeWavPcm16(pcm16k, 16000);
        const finalTranscript = liveSpeechTextRef.current || liveSpeechText.trim() || customTranscript.trim();
        await processLiveAnalysis(finalTranscript, fullWavBlob, true);
      }
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: false,
          autoGainControl: false,
        },
      }).catch(() => navigator.mediaDevices.getUserMedia({ audio: true }));
      micStreamRef.current = stream;
      pcmBufferRef.current = [];
      liveSpeechTextRef.current = "";
      setLiveSpeechText("");

      // Setup Web Audio Analyser
      const AudioCtx = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      let ctx: AudioContext;
      try {
        ctx = new AudioCtx({ sampleRate: 16000 } as any);
      } catch {
        ctx = new AudioCtx();
      }
      audioContextRef.current = ctx;

      const analyser = ctx.createAnalyser();
      analyser.fftSize = 64;
      analyserRef.current = analyser;

      const source = ctx.createMediaStreamSource(stream);
      source.connect(analyser);

      // Capture genuine PCM audio samples directly from sound card
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      scriptProcessorRef.current = processor;
      processor.onaudioprocess = (e) => {
        const channel = e.inputBuffer.getChannelData(0);
        pcmBufferRef.current.push(new Float32Array(channel));
        // Keep sliding window of ~3.5 seconds
        const maxChunks = Math.ceil((ctx.sampleRate * 3.5) / 4096);
        if (pcmBufferRef.current.length > maxChunks) {
          pcmBufferRef.current.splice(0, pcmBufferRef.current.length - maxChunks);
        }
      };
      source.connect(processor);

      // Connect through a zero-gain node to prevent speaker audio feedback/echo loop while keeping processor active
      const muteNode = ctx.createGain();
      muteNode.gain.value = 0;
      processor.connect(muteNode);
      muteNode.connect(ctx.destination);

      // Setup Web Speech API for live speech-to-text
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        const recognition = new SpeechRecognition();
        recognitionRef.current = recognition;
        recognition.continuous = true;
        recognition.interimResults = true;
        recognition.lang = "en-US";

        recognition.onresult = (event: any) => {
          let transcript = "";
          for (let i = 0; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript + " ";
          }
          const clean = transcript.trim();
          liveSpeechTextRef.current = clean;
          setLiveSpeechText(clean);
        };

        recognition.onerror = () => {};
        try {
          recognition.start();
        } catch {}
      }

      setIsMicActive(true);
      setIsSimulating(false);
      setRiskState("SAFE");

      const updateBars = () => {
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(dataArray);
        const bars: number[] = [];
        for (let i = 0; i < 12; i++) {
          const val = dataArray[i * 2] || 0;
          bars.push(Math.max(12, Math.min(95, (val / 255) * 100)));
        }
        setMicVolume(bars);
        animFrameRef.current = requestAnimationFrame(updateBars);
      };
      updateBars();

      // Real-time live mic streaming analysis every 1.8 seconds:
      liveIntervalRef.current = setInterval(async () => {
        if (pcmBufferRef.current.length < 8) return;
        let totalLen = 0;
        for (const chunk of pcmBufferRef.current) totalLen += chunk.length;
        const merged = new Float32Array(totalLen);
        let offset = 0;
        for (const chunk of pcmBufferRef.current) {
          merged.set(chunk, offset);
          offset += chunk.length;
        }
        const pcm16k = downsampleBuffer(merged, ctx.sampleRate, 16000);
        const wavBlob = encodeWavPcm16(pcm16k, 16000);
        const currentSpokenText = liveSpeechTextRef.current || "";
        await processLiveAnalysis(currentSpokenText, wavBlob, false);
      }, 1800);
    } catch {
      alert("Microphone access could not be acquired or is not supported in this browser.");
    }
  };

  const processLiveAnalysis = async (transcriptText: string, audioBlob?: Blob, persist = false) => {
    setIsAnalyzing(true);
    setActionExecuted(false);
    if (persist) setIsPersisted(false);

    try {
      const effectiveText = transcriptText || customTranscript || "";
      const data = await analyzeLiveMic(
        effectiveText,
        selectedTargetId || undefined,
        audioBlob
      );
      setCurrentScenario(data);
      if (data.transcript && data.transcript.length > 0) {
        const callerMsg = data.transcript.find((m) => m.speaker.includes("Caller"));
        if (callerMsg && callerMsg.text && !callerMsg.text.includes("Microphone audio frame received")) {
          setLiveSpeechText(callerMsg.text);
          liveSpeechTextRef.current = callerMsg.text;
        }
      }
      const computedVerdict: RiskState =
        data.actionType === "TERMINATE" ? "CRITICAL" : data.actionType === "STEP_UP" ? "WARNING" : "SAFE";
      setRiskState(computedVerdict);
      setIsSimulating(true);

      if (persist) {
        // Persist real call to SQLite database
        await saveCall({
          caller: data.callerName,
          agent: "Operator (SOC)",
          duration: formatTime(callDuration) || "0m 30s",
          verdict: computedVerdict,
          authenticity: data.authenticity,
          identity: data.identity,
          context: data.contextTitle,
          flaggedPhrases: data.threatKeywords,
        });
        setIsPersisted(true);
      }
    } catch (err) {
      console.error("Backend error analyzing live mic stream:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Handle genuine audio file upload to backend
  const handleFileUpload = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (isMicActive) toggleMicrophone();
    setIsAnalyzing(true);
    setActionExecuted(false);
    setIsPersisted(false);

    try {
      const data = await analyzeAudioUpload(file, customTranscript || undefined, selectedTargetId || undefined);
      setCurrentScenario(data);
      if (data.transcript && data.transcript.length > 0) {
        const callerMsg = data.transcript.find((m) => m.speaker.includes("Caller"));
        if (callerMsg && callerMsg.text) {
          setLiveSpeechText(callerMsg.text);
        }
      }
      const computedVerdict: RiskState =
        data.actionType === "TERMINATE" ? "CRITICAL" : data.actionType === "STEP_UP" ? "WARNING" : "SAFE";
      setRiskState(computedVerdict);
      setIsSimulating(true);

      // Persist to database
      await saveCall({
        caller: file.name,
        agent: "Operator (SOC)",
        duration: "1m 15s",
        verdict: computedVerdict,
        authenticity: data.authenticity,
        identity: data.identity,
        context: data.contextTitle,
        flaggedPhrases: data.threatKeywords,
      });
      setIsPersisted(true);
    } catch (err) {
      console.error("Failed to analyze audio file:", err);
      alert("Backend failed to process audio upload. Please ensure backend is running on http://127.0.0.1:8000.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Run contextual threat evaluation on custom text
  const handleEvaluateCustomText = async () => {
    if (!customTranscript.trim()) return;
    setIsAnalyzing(true);
    setActionExecuted(false);
    setIsPersisted(false);

    try {
      const data = await analyzeLiveMic(
        customTranscript.trim(),
        selectedTargetId || undefined
      );
      setCurrentScenario(data);
      const computedVerdict: RiskState =
        data.actionType === "TERMINATE" ? "CRITICAL" : data.actionType === "STEP_UP" ? "WARNING" : "SAFE";
      setRiskState(computedVerdict);
      setIsSimulating(true);

      await saveCall({
        caller: "Interactive Security Inspection",
        agent: "Operator (SOC)",
        duration: "0m 45s",
        verdict: computedVerdict,
        authenticity: data.authenticity,
        identity: data.identity,
        context: data.contextTitle,
        flaggedPhrases: data.threatKeywords,
      });
      setIsPersisted(true);
    } catch (err) {
      console.error("Evaluation failed:", err);
      alert("Evaluation failed. Please check backend connection.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const stopSimulation = () => {
    if (liveIntervalRef.current) {
      clearInterval(liveIntervalRef.current);
      liveIntervalRef.current = null;
    }
    if (isMicActive) toggleMicrophone();
    setIsSimulating(false);
    setRiskState("IDLE");
    setCurrentScenario(null);
    setActionExecuted(false);
    setIsPersisted(false);
    setLiveSpeechText("");
  };

  const formatTime = (secs: number) => {
    const mins = Math.floor(secs / 60);
    const rem = secs % 60;
    return `${mins.toString().padStart(2, "0")}:${rem.toString().padStart(2, "0")}`;
  };

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-gray-50/50">
      {/* ─── TOP SYSTEM BAR ─── */}
      <nav className="bg-white border-b border-gray-200 h-16 flex items-center justify-between px-6 sm:px-10 z-20 sticky top-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span className="text-sm font-semibold text-gray-900 tracking-tight">VoxGuard SOC</span>
            <ChevronRight className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-500 font-medium">Real-Time Multi-Modal Voice Trust Console</span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button className="text-gray-500 hover:text-gray-900 relative p-1.5 rounded-md hover:bg-gray-100 transition-colors">
            <Bell className="w-5 h-5" />
            {riskState === "CRITICAL" && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full animate-ping" />
            )}
          </button>
        </div>
      </nav>

      {/* ─── ACTIVE TELEPHONY & INGESTION HEADER ─── */}
      <header className="bg-white border-b border-gray-200 py-4 px-6 sm:px-10 shadow-sm">
        <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div
              className={cn(
                "p-3 rounded-xl border transition-all",
                riskState === "CRITICAL"
                  ? "bg-red-50 border-red-200 text-red-600 animate-pulse"
                  : riskState === "WARNING"
                  ? "bg-amber-50 border-amber-200 text-amber-600"
                  : riskState === "SAFE"
                  ? "bg-emerald-50 border-emerald-200 text-emerald-600"
                  : "bg-gray-100 border-gray-200 text-gray-500"
              )}
            >
              <Radio className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight">
                  {isSimulating || isMicActive
                    ? currentScenario?.callerName || "Active Audio Monitoring"
                    : "Audio Pipeline Standby"}
                </h1>
                {isSimulating || isMicActive ? (
                  <Badge className="bg-emerald-100 text-emerald-800 border-emerald-300 text-xs px-2 py-0.5 gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping" /> LIVE SESSION
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-gray-500 border-gray-300 text-xs">
                    READY
                  </Badge>
                )}
                {isPersisted && (
                  <Badge className="bg-blue-50 text-blue-700 border-blue-200 text-[10px] gap-1">
                    <CheckCircle2 className="w-3 h-3" /> Persisted to SQLite
                  </Badge>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 mt-1">
                <span>
                  Target Profile:{" "}
                  <strong className="text-gray-700 font-medium">
                    {currentScenario?.enrolledTarget ||
                      (selectedTargetId
                        ? enrolledProfiles.find((p) => p.id === selectedTargetId)?.name || selectedTargetId
                        : "Auto-Verify Across Registry")}
                  </strong>
                </span>
                <span>•</span>
                <span>
                  VAD:{" "}
                  <strong
                    className={
                      isSimulating || isMicActive ? "text-emerald-600 font-semibold" : "text-gray-400"
                    }
                  >
                    {isSimulating || isMicActive ? "VOICE ACTIVE" : "SILENCE"}
                  </strong>
                </span>
                <span>•</span>
                <span>
                  Duration:{" "}
                  <strong className="text-gray-700 font-mono">{formatTime(callDuration)}</strong>
                </span>
              </div>
            </div>
          </div>

          {/* Telephony Controls */}
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept="audio/*"
              className="hidden"
            />
            <Button
              onClick={() => fileInputRef.current?.click()}
              variant="outline"
              size="sm"
              className="gap-1.5 text-xs font-medium hover:border-[#F6821F] hover:text-[#F6821F] cursor-pointer"
            >
              <Upload className="w-3.5 h-3.5" /> Upload Audio (.wav, .mp3)
            </Button>
            <Button
              onClick={toggleMicrophone}
              variant="outline"
              size="sm"
              className={cn(
                "gap-1.5 text-xs font-medium cursor-pointer",
                isMicActive
                  ? "bg-red-50 text-red-700 border-red-300 hover:bg-red-100"
                  : "hover:border-[#F6821F] hover:text-[#F6821F]"
              )}
            >
              {isMicActive ? <MicOff className="w-3.5 h-3.5" /> : <Mic className="w-3.5 h-3.5" />}
              {isMicActive ? "Stop & Process Mic" : "Live Mic Stream"}
            </Button>
            <Button
              onClick={stopSimulation}
              disabled={!isSimulating && !isMicActive}
              variant="ghost"
              size="sm"
              className="text-xs text-gray-500 hover:text-red-600 gap-1 cursor-pointer"
            >
              <PhoneOff className="w-3.5 h-3.5" /> Reset
            </Button>
          </div>
        </div>
      </header>

      {/* ─── MAIN SOC MONITORING WORKSPACE ─── */}
      <main className="flex-1 w-full max-w-[1400px] mx-auto p-6 sm:p-10 space-y-6">
        {/* Registry Status Notice if 0 identities enrolled */}
        {enrolledProfiles.length === 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
            <Info className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1 text-xs text-amber-800">
              <p className="font-semibold text-sm text-amber-900">Zero Voiceprints Enrolled in Database</p>
              <p className="mt-0.5 text-amber-700">
                The speaker registry in SQLite currently has no enrolled reference voiceprints. Audio analysis will
                evaluate acoustic authenticity and contextual threat risks, but speaker consistency verification
                requires enrolled voiceprints.
              </p>
            </div>
            <Link href="/identities">
              <Button size="sm" className="bg-[#F6821F] hover:bg-[#E85D04] text-white text-xs shrink-0">
                <Fingerprint className="w-3.5 h-3.5 mr-1" /> Enroll Voiceprint
              </Button>
            </Link>
          </div>
        )}

        {/* Real Audio & Threat Analysis Control Panel */}
        <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-[#F6821F]" />
              <h2 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
                Real-Time AMVTF Multi-Signal Ingest Console
              </h2>
            </div>

            {/* Target Voiceprint Selector from SQLite */}
            <div className="flex items-center gap-2">
              <label className="text-xs text-gray-500 font-medium">Verify Against:</label>
              <select
                value={selectedTargetId}
                onChange={(e) => setSelectedTargetId(e.target.value)}
                className="text-xs border border-gray-300 rounded-md px-2.5 py-1.5 bg-white text-gray-800 focus:outline-none focus:border-[#F6821F]"
              >
                <option value="">Auto-Detect / All Registered Profiles</option>
                {enrolledProfiles.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.id}) — {p.department}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Interactive Dialogue / Threat Keyword Tester */}
          <div className="flex flex-col md:flex-row items-center gap-3 pt-2 border-t border-gray-100">
            <div className="relative flex-1 w-full">
              <input
                type="text"
                value={customTranscript}
                onChange={(e) => setCustomTranscript(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleEvaluateCustomText()}
                placeholder="Test contextual dialogue (e.g., 'Bypass protocol and execute wire transfer immediately, CEO approved')..."
                className="w-full text-xs px-3 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:bg-white focus:outline-none focus:border-[#F6821F]"
              />
            </div>
            <Button
              onClick={handleEvaluateCustomText}
              disabled={isAnalyzing || !customTranscript.trim()}
              size="sm"
              className="bg-gray-900 hover:bg-black text-white text-xs gap-1.5 shrink-0 cursor-pointer w-full md:w-auto"
            >
              {isAnalyzing ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
              Evaluate Contextual Risk
            </Button>
          </div>

          {/* Live Mic Speech Transcript Display if mic active */}
          {isMicActive && (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg flex items-center gap-3 animate-in fade-in">
              <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping" />
              <div className="flex-1 text-xs">
                <span className="font-semibold text-blue-900">Live Speech Transcription: </span>
                <span className="text-blue-800 font-mono">
                  {liveSpeechText || "Listening to speech... Speak into microphone to transcribe."}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* ─── WORKSPACE TWO-COLUMN LAYOUT ─── */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
          {/* LEFT 7 COLS: Live Voiceprint Analysis & Threat Feeds */}
          <div className="lg:col-span-7 space-y-6">
            {/* AMVTF Final Decision & Action Widget */}
            <div
              className={cn(
                "rounded-xl border p-5 transition-all shadow-sm",
                riskState === "CRITICAL"
                  ? "bg-red-50/80 border-red-200"
                  : riskState === "WARNING"
                  ? "bg-amber-50/80 border-amber-200"
                  : riskState === "SAFE"
                  ? "bg-emerald-50/80 border-emerald-200"
                  : "bg-white border-gray-200"
              )}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div
                    className={cn(
                      "p-2.5 rounded-lg border",
                      riskState === "CRITICAL"
                        ? "bg-red-100 border-red-300 text-red-700"
                        : riskState === "WARNING"
                        ? "bg-amber-100 border-amber-300 text-amber-700"
                        : riskState === "SAFE"
                        ? "bg-emerald-100 border-emerald-300 text-emerald-700"
                        : "bg-gray-100 border-gray-200 text-gray-500"
                    )}
                  >
                    {riskState === "CRITICAL" ? (
                      <ShieldAlert className="w-6 h-6" />
                    ) : riskState === "WARNING" ? (
                      <AlertTriangle className="w-6 h-6" />
                    ) : riskState === "SAFE" ? (
                      <ShieldCheck className="w-6 h-6" />
                    ) : (
                      <Activity className="w-6 h-6" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="text-base font-bold text-gray-900">
                        {currentScenario
                          ? `AMVTF Verdict: ${currentScenario.actionType === "TERMINATE" ? "CRITICAL THREAT" : currentScenario.actionType === "STEP_UP" ? "SUSPICIOUS / STEP-UP" : "VERIFIED SAFE"}`
                          : "AMVTF Engine Standby"}
                      </h3>
                      {riskState !== "IDLE" && (
                        <Badge
                          className={cn(
                            "text-xs font-semibold px-2 py-0.5",
                            riskState === "CRITICAL"
                              ? "bg-red-600 text-white"
                              : riskState === "WARNING"
                              ? "bg-amber-600 text-white"
                              : "bg-emerald-600 text-white"
                          )}
                        >
                          {riskState}
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-gray-600 mt-0.5">
                      {currentScenario?.recommendedAction || "Awaiting audio stream or file input to evaluate trust."}
                    </p>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-[10px] text-gray-400 uppercase tracking-wider block">Fused Risk Score</span>
                  <span
                    className={cn(
                      "text-2xl font-black font-mono",
                      riskState === "CRITICAL"
                        ? "text-red-600"
                        : riskState === "WARNING"
                        ? "text-amber-600"
                        : riskState === "SAFE"
                        ? "text-emerald-600"
                        : "text-gray-400"
                    )}
                  >
                    {currentScenario ? `${currentScenario.fusedRiskScore}` : "--"}
                  </span>
                  <span className="text-[10px] text-gray-400 block">/ 100</span>
                </div>
              </div>

              {/* Rationale Explanation */}
              {currentScenario && (
                <div className="mt-3 pt-3 border-t border-gray-200/60 text-xs text-gray-700">
                  <span className="font-semibold text-gray-900">Analysis Rationale: </span>
                  {currentScenario.rationale}
                </div>
              )}

              {/* Action Buttons */}
              {riskState !== "IDLE" && (
                <div className="flex flex-wrap items-center gap-2 mt-4 pt-3 border-t border-gray-200/60">
                  <span className="text-xs font-semibold text-gray-700 mr-2">Operator Action:</span>
                  {riskState === "CRITICAL" && (
                    <Button
                      size="sm"
                      onClick={() => setActionExecuted(true)}
                      className={cn(
                        "text-xs font-semibold gap-1.5 shadow-sm",
                        actionExecuted ? "bg-gray-800 text-white" : "bg-red-600 hover:bg-red-700 text-white"
                      )}
                    >
                      <Flame className="w-3.5 h-3.5" />
                      {actionExecuted ? "Account Frozen & Terminated" : "Terminate Call & Freeze Account"}
                    </Button>
                  )}
                  {riskState === "WARNING" && (
                    <Button
                      size="sm"
                      onClick={() => setActionExecuted(true)}
                      className={cn(
                        "text-xs font-semibold gap-1.5 shadow-sm",
                        actionExecuted ? "bg-gray-800 text-white" : "bg-amber-600 hover:bg-amber-700 text-white"
                      )}
                    >
                      <Lock className="w-3.5 h-3.5" />
                      {actionExecuted ? "Secondary OOB Challenge Sent" : "Trigger Out-of-Band Verification"}
                    </Button>
                  )}
                  {riskState === "SAFE" && (
                    <Button
                      size="sm"
                      onClick={() => setActionExecuted(true)}
                      className={cn(
                        "text-xs font-semibold gap-1.5 shadow-sm",
                        actionExecuted ? "bg-gray-800 text-white" : "bg-emerald-600 hover:bg-emerald-700 text-white"
                      )}
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      {actionExecuted ? "Session Cleared" : "Authorize Session Operations"}
                    </Button>
                  )}
                </div>
              )}
            </div>

            {/* Audio Waveform & Biometric Visualization */}
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Audio Ingestion & Frequency Spectrogram</h3>
                  <p className="text-xs text-gray-500">Live 16kHz PCM audio frequency bin magnitude</p>
                </div>
                <div className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      "w-2 h-2 rounded-full",
                      isSimulating || isMicActive ? "bg-emerald-500 animate-pulse" : "bg-gray-400"
                    )}
                  />
                  <span className="text-xs font-mono text-gray-500">
                    {isSimulating || isMicActive ? "LIVE SIGNAL" : "OFFLINE"}
                  </span>
                </div>
              </div>

              {/* Dynamic Audio Bars */}
              <div className="h-28 bg-gray-900 rounded-lg p-4 flex items-end justify-between gap-1.5 overflow-hidden">
                {micVolume.map((vol, i) => (
                  <div key={i} className="flex-1 flex flex-col items-center gap-1 h-full justify-end">
                    <div
                      className={cn(
                        "w-full rounded-t transition-all duration-75",
                        riskState === "CRITICAL"
                          ? "bg-gradient-to-t from-red-600 to-red-400"
                          : riskState === "WARNING"
                          ? "bg-gradient-to-t from-amber-600 to-amber-400"
                          : riskState === "SAFE"
                          ? "bg-gradient-to-t from-emerald-600 to-emerald-400"
                          : "bg-gray-700"
                      )}
                      style={{ height: `${isSimulating || isMicActive ? vol : 8}%` }}
                    />
                  </div>
                ))}
              </div>

              {/* Spectral Metadata */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs pt-1">
                <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                  <span className="text-gray-400 text-[10px] uppercase block">Spectral Entropy</span>
                  <span className="font-bold font-mono text-gray-800 text-xs">
                    {currentScenario?.spectralEntropy !== undefined ? `${currentScenario.spectralEntropy}` : "--"}
                  </span>
                </div>
                <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                  <span className="text-gray-400 text-[10px] uppercase block">Zero-Crossing Rate</span>
                  <span className="font-bold font-mono text-gray-800 text-xs">
                    {currentScenario?.zcr !== undefined ? `${currentScenario.zcr}` : "--"}
                  </span>
                </div>
                <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                  <span className="text-gray-400 text-[10px] uppercase block">Micro-Tremor / Jitter</span>
                  <span className="font-bold font-mono text-gray-800 text-xs">
                    {currentScenario?.jitter !== undefined ? `${currentScenario.jitter}%` : "--"}
                  </span>
                </div>
                <div className="bg-gray-50 p-2.5 rounded-lg border border-gray-200">
                  <span className="text-gray-400 text-[10px] uppercase block">Glottal Kurtosis</span>
                  <span
                    className={cn(
                      "font-bold font-mono text-xs",
                      currentScenario?.kurtosis !== undefined && currentScenario.kurtosis < 4.0
                        ? "text-red-600"
                        : "text-emerald-700"
                    )}
                  >
                    {currentScenario?.kurtosis !== undefined ? `${currentScenario.kurtosis}` : "--"}
                  </span>
                </div>
              </div>

              {/* Dynamic Spoofing Indicators Banner if detected */}
              {currentScenario?.syntheticIndicators && currentScenario.syntheticIndicators.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-800 space-y-1">
                  <span className="font-semibold flex items-center gap-1.5 text-red-900">
                    <AlertTriangle className="w-3.5 h-3.5 text-red-600" />
                    Synthetic / AI Acoustic Artifacts Detected:
                  </span>
                  <ul className="list-disc list-inside space-y-0.5 text-[11px] text-red-700">
                    {currentScenario.syntheticIndicators.map((ind, idx) => (
                      <li key={idx}>{ind}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Live Conversation Transcript Feed */}
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-gray-900">Audited Dialogue Feed</h3>
                  <p className="text-xs text-gray-500">Real-time transcripts analyzed by DistilBERT NLP</p>
                </div>
                {currentScenario && (
                  <Badge variant="outline" className="text-[10px] text-gray-600 border-gray-300">
                    {currentScenario.nlpIntent}
                  </Badge>
                )}
              </div>

              <div className="space-y-2.5 max-h-72 overflow-y-auto pr-1">
                {!currentScenario ? (
                  <div className="py-12 text-center text-gray-400 text-xs">
                    No active dialogue recorded. Start live microphone monitoring or upload an audio file above.
                  </div>
                ) : (
                  currentScenario.transcript.map((msg, i) => (
                    <div
                      key={i}
                      className={cn(
                        "p-3 rounded-lg border text-xs transition-all",
                        msg.alert
                          ? "bg-red-50/80 border-red-200 text-red-900"
                          : msg.speaker === "Caller"
                          ? "bg-gray-50 border-gray-200 text-gray-800"
                          : "bg-blue-50/50 border-blue-100 text-blue-900"
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold">{msg.speaker}</span>
                        <span className="text-[10px] text-gray-400 font-mono">{msg.time}</span>
                      </div>
                      <p>{msg.text}</p>
                      {msg.threatKeywords && msg.threatKeywords.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2 pt-1 border-t border-red-200/50">
                          {msg.threatKeywords.map((kw, ki) => (
                            <Badge key={ki} className="bg-red-100 text-red-800 border-red-300 text-[10px] px-1.5 py-0">
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* RIGHT 5 COLS: Multi-Signal Engine Breakdown */}
          <div className="lg:col-span-5 space-y-6">
            {/* Three Signal Layer Breakdown */}
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-5">
              <div>
                <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
                  AMVTF Multi-Signal Trust Breakdown
                </h3>
                <p className="text-xs text-gray-500 mt-0.5">Real-time fusion across 3 defense layers</p>
              </div>

              {/* Layer 1: AASIST Authenticity */}
              <div>
                <div className="flex justify-between items-end mb-1.5">
                  <div>
                    <p className="text-xs font-bold text-gray-900">Layer 1: AASIST Authenticity (40%)</p>
                    <p className="text-[10px] text-gray-500">Audio Anti-Spoofing & Vocoder Detection</p>
                  </div>
                  <span className="text-sm font-bold font-mono text-gray-900">
                    {currentScenario ? `${currentScenario.authenticity}%` : "--"}
                  </span>
                </div>
                <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden border border-gray-200">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      !currentScenario
                        ? "w-0"
                        : currentScenario.authenticity > 50
                        ? "bg-emerald-500"
                        : "bg-red-500"
                    )}
                    style={{ width: currentScenario ? `${currentScenario.authenticity}%` : "0%" }}
                  />
                </div>
                <div className="flex justify-between items-center mt-1 text-[10px] text-gray-500">
                  <span>Threshold: &gt;50% Human</span>
                  <span className="font-semibold text-gray-800">
                    {currentScenario?.authStatus || "Awaiting Stream"}
                  </span>
                </div>
              </div>

              {/* Layer 2: ECAPA-TDNN Speaker Identity */}
              <div>
                <div className="flex justify-between items-end mb-1.5">
                  <div>
                    <p className="text-xs font-bold text-gray-900">Layer 2: ECAPA-TDNN Identity (35%)</p>
                    <p className="text-[10px] text-gray-500">192-Dim Cosine Match vs Enrolled Profiles</p>
                  </div>
                  <span className="text-sm font-bold font-mono text-gray-900">
                    {currentScenario ? `${currentScenario.identity}%` : "--"}
                  </span>
                </div>
                <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden border border-gray-200 relative">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      !currentScenario
                        ? "w-0"
                        : currentScenario.identity > 70
                        ? "bg-emerald-500"
                        : "bg-amber-500"
                    )}
                    style={{ width: currentScenario ? `${currentScenario.identity}%` : "0%" }}
                  />
                  <div
                    className="absolute top-0 bottom-0 w-0.5 bg-gray-500"
                    style={{ left: "70%" }}
                    title="Threshold 70%"
                  />
                </div>
                <div className="flex justify-between items-center mt-1 text-[10px] text-gray-500">
                  <span>Target: {currentScenario?.enrolledTarget || (selectedTargetId || "Auto-detect in Registry")}</span>
                  <span className="font-semibold text-gray-800">
                    {currentScenario?.idStatus || "Awaiting Stream"}
                  </span>
                </div>
              </div>

              {/* Layer 3: Contextual Threat Risk */}
              <div>
                <div className="flex justify-between items-end mb-1.5">
                  <div>
                    <p className="text-xs font-bold text-gray-900">Layer 3: Context Risk (25%)</p>
                    <p className="text-[10px] text-gray-500">DistilBERT Intent & Social Engineering Risk</p>
                  </div>
                  <span className="text-sm font-bold font-mono text-gray-900">
                    {currentScenario ? `${currentScenario.contextRisk}%` : "--"}
                  </span>
                </div>
                <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden border border-gray-200">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      !currentScenario
                        ? "w-0"
                        : currentScenario.contextRisk > 60
                        ? "bg-red-500"
                        : currentScenario.contextRisk > 30
                        ? "bg-amber-500"
                        : "bg-emerald-500"
                    )}
                    style={{ width: currentScenario ? `${currentScenario.contextRisk}%` : "0%" }}
                  />
                </div>
                <div className="flex justify-between items-center mt-1 text-[10px] text-gray-500">
                  <span>Calculated via NLP Classification</span>
                  <span className="font-semibold text-gray-800">
                    {currentScenario
                      ? currentScenario.contextRisk > 50
                        ? "High Threat"
                        : "Benign"
                      : "Awaiting Stream"}
                  </span>
                </div>
              </div>
            </div>

            {/* Semantic Risk Flags */}
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-5 space-y-3">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider">
                Extracted Threat Keywords & Semantic Flags
              </h3>
              <p className="text-xs text-gray-500">
                Rule-based security flags detected during NLP conversation analysis
              </p>

              <div className="flex flex-wrap gap-2 pt-2">
                {!currentScenario || (!currentScenario.threatKeywords.length && !currentScenario.semanticFlags.length) ? (
                  <p className="text-xs text-gray-400 py-4">No threat flags detected in active stream.</p>
                ) : (
                  <>
                    {currentScenario.threatKeywords.map((kw, i) => (
                      <Badge key={i} className="bg-red-50 text-red-700 border-red-200 text-xs px-2 py-1 gap-1">
                        <AlertTriangle className="w-3 h-3 text-red-500" />
                        {kw}
                      </Badge>
                    ))}
                    {currentScenario.semanticFlags.map((flag, i) => (
                      <Badge key={i} className="bg-amber-50 text-amber-700 border-amber-200 text-xs px-2 py-1 gap-1">
                        <CheckCircle2 className="w-3 h-3 text-amber-500" />
                        {flag}
                      </Badge>
                    ))}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
