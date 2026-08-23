"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
    createProjectWithSettings,
    uploadVideo,
    getProject,
    getSettings,
    getCaptionStyles,
    deleteClip,
    retryProject,
    updateClipTitle,
    clipDownloadUrl,
    fileUrl,
} from "@/lib/api";
import { Clip, CaptionStyle, ClipSettings } from "@/lib/types";
import { useProjectProgress } from "@/lib/websocket";

const STAGE_LABELS: Record<string, string> = {
    downloading: "Downloading video…",
    transcribing: "Transcribing…",
    analyzing: "Finding best moments…",
    processing: "Creating clips…",
    done: "All shorts ready!",
    error: "Processing failed",
    cancelled: "Cancelled",
};

// Pipeline checklist stages shown while processing (DKC 57)
const CHECK_STAGES = [
    "transcribing",
    "analyzing",
    "processing",
    "captions",
    "rendering",
] as const;

function formatDuration(s: number) {
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
}

function Toggle({ checked, onChange, label, desc }: {
    checked: boolean;
    onChange: (v: boolean) => void;
    label: string;
    desc?: string;
}) {
    return (
        <button
            type="button"
            onClick={() => onChange(!checked)}
            className="flex w-full items-center justify-between gap-3 rounded-xl bg-slate-900/40 border border-slate-800 px-4 py-3 text-left hover:border-slate-600 transition-all"
        >
            <span>
                <span className="block text-sm font-bold text-slate-100">{label}</span>
                {desc && <span className="block text-[11px] text-slate-500 mt-0.5">{desc}</span>}
            </span>
            <span className={`relative h-6 w-11 flex-shrink-0 rounded-full transition-colors ${checked ? "bg-primary" : "bg-slate-700"}`}>
                <span className={`absolute top-1 h-4 w-4 rounded-full bg-white transition-all ${checked ? "left-6" : "left-1"}`} />
            </span>
        </button>
    );
}

function StageChecklist({ stage, percent, message }: { stage: string; percent: number; message: string }) {
    // Map WS stages onto the user-facing checklist (caption burn-ins
    // report under the "processing" stage with a captions message)
    const isCaptions = stage === "processing" && /caption/i.test(message || "");
    const activeIdx =
        stage === "downloading" ? -1
        : stage === "transcribing" ? 0
        : stage === "analyzing" ? 1
        : stage === "processing" ? (isCaptions ? 3 : 2)
        : stage === "done" ? CHECK_STAGES.length
        : -1;

    return (
        <div className="space-y-2">
            {CHECK_STAGES.map((s, i) => {
                const label = {
                    transcribing: "Transcribing",
                    analyzing: "Finding moments",
                    processing: "Creating clips",
                    captions: "Captions",
                    rendering: "Rendering",
                }[s as string];
                const done = i < activeIdx || stage === "done";
                const active = i === activeIdx && stage !== "done";
                return (
                    <div key={s} className="flex items-center gap-3">
                        <span className={`flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold ${
                            done ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/40"
                            : active ? "bg-primary/20 text-primary border border-primary/50"
                            : "bg-white/5 text-slate-600 border border-white/10"
                        }`}>
                            {done ? "✓" : active ? "•" : "○"}
                        </span>
                        <span className={`text-sm ${done ? "text-emerald-400" : active ? "text-white" : "text-slate-600"}`}>
                            {label}
                        </span>
                        {active && (
                            <span className="ml-auto h-1 w-32 overflow-hidden rounded-full bg-white/10">
                                <span
                                    className="block h-full rounded-full bg-gradient-to-r from-primary to-accent-red transition-all duration-500"
                                    style={{ width: `${Math.min(100, Math.max(4, percent))}%` }}
                                />
                            </span>
                        )}
                    </div>
                );
            })}
        </div>
    );
}

export default function CreateProjectPage() {
    const router = useRouter();
    const [sourceMode, setSourceMode] = useState<"url" | "file">("url");
    const [url, setUrl] = useState("");
    const [file, setFile] = useState<File | null>(null);
    const [isProcessing, setIsProcessing] = useState(false);
    const [generatedClips, setGeneratedClips] = useState<Clip[]>([]);
    const [projectId, setProjectId] = useState<string | null>(null);
    const [apiError, setApiError] = useState<string | null>(null);
    const [hasApiKey, setHasApiKey] = useState<boolean | null>(null);

    // DKC 57 clip settings
    const [numClips, setNumClips] = useState(5);
    const [customCount, setCustomCount] = useState(false);
    const [minDuration, setMinDuration] = useState(30);
    const [maxDuration, setMaxDuration] = useState(90);
    const [captionsOn, setCaptionsOn] = useState(false);
    const [captionStyle, setCaptionStyle] = useState("classic_white");
    const [captionStyles, setCaptionStyles] = useState<CaptionStyle[]>([]);
    const [reframe, setReframe] = useState(true);
    const [faceTracking, setFaceTracking] = useState(true);
    const [aiDetection, setAiDetection] = useState(true);
    const [wmOn, setWmOn] = useState(false);
    const [wmPosition, setWmPosition] = useState<"top_left" | "top_right" | "bottom_left" | "bottom_right">("bottom_right");
    const [wmOpacity, setWmOpacity] = useState(0.6);
    const [editingClip, setEditingClip] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState("");

    const { stage, percent, message, logs } = useProjectProgress(isProcessing ? projectId : null);
    const fileRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);

    useEffect(() => {
        Promise.all([getSettings(), getCaptionStyles()])
            .then(([s, styles]) => {
                setHasApiKey(s.has_api_key);
                setCaptionStyles(styles.filter(x => x.key !== "none"));
                setWmOn(Boolean(s.watermark_enabled));
                setWmPosition(s.watermark_position || "bottom_right");
                setWmOpacity(typeof s.watermark_opacity === "number" ? s.watermark_opacity : 0.6);
                const globalStyle = s.caption_style;
                if (globalStyle && globalStyle !== "none") {
                    setCaptionsOn(true);
                    setCaptionStyle(globalStyle);
                }
            })
            .catch(console.error);
    }, []);

    useEffect(() => {
        if (stage === "done" && projectId) {
            getProject(projectId)
                .then(data => { setGeneratedClips(data.clips || []); setIsProcessing(false); })
                .catch(() => { setApiError("Failed to load clips."); setIsProcessing(false); });
        } else if (stage === "error" || stage === "cancelled") {
            setIsProcessing(false);
        }
    }, [stage, projectId]);

    const buildSettings = (): ClipSettings => ({
        num_clips: numClips,
        min_duration: minDuration,
        max_duration: maxDuration,
        aspect_ratio: "9:16",
        captions: captionsOn ? captionStyle : "none",
        reframe,
        face_tracking: faceTracking,
        ai_detection: aiDetection,
        watermark: { enabled: wmOn, position: wmPosition, opacity: wmOpacity },
    });

    const handlePaste = async () => {
        try { setUrl(await navigator.clipboard.readText()); } catch { /* ignore */ }
    };

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (isProcessing) return;
        if (sourceMode === "url" && !url.trim()) return;
        if (sourceMode === "file" && !file) return;
        setIsProcessing(true);
        setGeneratedClips([]);
        setApiError(null);
        setProjectId(null);
        try {
            const settings = buildSettings();
            const res = sourceMode === "url"
                ? await createProjectWithSettings(url.trim(), settings)
                : await uploadVideo(file!, settings);
            setProjectId(res.project_id);
        } catch (err) {
            setApiError(err instanceof Error ? err.message : "Something went wrong.");
            setIsProcessing(false);
        }
    };

    const handleRejectClip = async (clipId: string) => {
        await deleteClip(clipId).catch(console.error);
        setGeneratedClips(prev => prev.filter(c => c.id !== clipId));
        if (projectId) {
            getProject(projectId).then(d => setGeneratedClips(d.clips || [])).catch(() => {});
        }
    };

    const handleSaveTitle = async (clip: Clip) => {
        const t = editTitle.trim();
        if (t) await updateClipTitle(clip.id, t).catch(console.error);
        setEditingClip(null);
        if (projectId) getProject(projectId).then(d => setGeneratedClips(d.clips || [])).catch(() => {});
    };

    const clampedPercent = Math.min(100, Math.max(0, percent));
    const isLive = isProcessing && projectId;
    const needsKey = hasApiKey === false && aiDetection && sourceMode !== "file";

    return (
        <div className="mx-auto w-full max-w-5xl px-6 py-12">

            {/* Header */}
            {!isLive && generatedClips.length === 0 && (
                <div className="mb-10 text-center">
                    <span className="mb-4 inline-block rounded-full bg-primary/20 border border-primary/30 px-4 py-1 text-xs font-bold uppercase tracking-widest text-primary">
                        Create Shorts
                    </span>
                    <h1 className="text-4xl font-bold text-white mb-3">
                        One-click <span className="text-gradient">Shorts</span> generation
                    </h1>
                    <p className="text-slate-400 text-base max-w-xl mx-auto">
                        Upload a long video or paste a YouTube link. DKC 57 transcribes, finds the
                        best moments and exports ready-to-post 9:16 shorts with captions.
                    </p>
                </div>
            )}

            {/* No API key warning (only matters for AI detection + YouTube) */}
            {needsKey && (
                <div className="mb-8 flex items-center justify-between gap-4 rounded-2xl border border-amber-500/20 bg-amber-500/10 p-5">
                    <div className="flex items-center gap-3 text-amber-400">
                        <svg className="h-5 w-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
                        <div>
                            <p className="font-bold text-sm">No LLM configured</p>
                            <p className="text-xs opacity-80">
                                AI moment detection needs an API key — or turn it off below for
                                evenly spaced cuts (fully local, no key required).
                            </p>
                        </div>
                    </div>
                    <Link href="/settings" className="flex-shrink-0 rounded-xl bg-amber-500/20 px-4 py-2 text-xs font-bold text-amber-400 hover:bg-amber-500/30 transition-colors">
                        Configure →
                    </Link>
                </div>
            )}

            {/* Form */}
            {!isLive && generatedClips.length === 0 && (
                <form onSubmit={handleGenerate} className="space-y-6">

                    {/* Source selector */}
                    <div className="glass-card rounded-3xl p-6">
                        <div className="flex rounded-xl bg-slate-900/50 p-1 gap-1 mb-6">
                            <button type="button" onClick={() => setSourceMode("url")}
                                className={`flex-1 py-2.5 text-sm font-bold rounded-lg transition-all ${sourceMode === "url" ? "bg-primary text-white" : "text-slate-400 hover:text-white"}`}>
                                YouTube URL
                            </button>
                            <button type="button" onClick={() => setSourceMode("file")}
                                className={`flex-1 py-2.5 text-sm font-bold rounded-lg transition-all ${sourceMode === "file" ? "bg-primary text-white" : "text-slate-400 hover:text-white"}`}>
                                Upload File
                            </button>
                        </div>

                        {sourceMode === "url" ? (
                            <div className="flex items-center gap-2 rounded-xl glass px-4 py-3.5 border border-white/10 focus-within:border-primary/50 transition-all">
                                <svg className="h-5 w-5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                                <input
                                    value={url}
                                    onChange={e => setUrl(e.target.value)}
                                    className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none"
                                    placeholder="https://youtu.be/…"
                                    type="text"
                                    required
                                />
                                <button type="button" onClick={handlePaste}
                                    className="rounded-lg bg-primary/20 px-3 py-1.5 text-xs font-bold text-primary hover:bg-primary/30 transition-colors uppercase tracking-wider">
                                    Paste
                                </button>
                            </div>
                        ) : (
                            <div
                                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                                onDragLeave={() => setDragOver(false)}
                                onDrop={e => {
                                    e.preventDefault(); setDragOver(false);
                                    const f = e.dataTransfer.files?.[0];
                                    if (f) setFile(f);
                                }}
                                onClick={() => fileRef.current?.click()}
                                className={`cursor-pointer flex items-center justify-center gap-3 rounded-xl border-2 border-dashed px-4 py-10 transition-all ${
                                    dragOver ? "border-primary bg-primary/10"
                                    : file ? "border-primary/50 bg-primary/5" : "border-white/10 hover:border-primary/40"
                                }`}
                            >
                                <svg className="h-8 w-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0-12l-4 4m4-4l4 4" /></svg>
                                <div>
                                    <p className="text-sm font-bold text-white">
                                        {file ? file.name : "Click or drop a video here"}
                                    </p>
                                    <p className="text-xs text-slate-500">
                                        {file ? `${(file.size / 1024 / 1024).toFixed(1)} MB — transcribed locally` : "mp4, mov, mkv, webm, avi — processed locally"}
                                    </p>
                                </div>
                                <input ref={fileRef} type="file" accept=".mp4,.mov,.mkv,.webm,.avi,.m4v" className="hidden"
                                    onChange={e => e.target.files?.[0] && setFile(e.target.files[0])} />
                            </div>
                        )}
                    </div>

                    {/* Clip settings */}
                    <div className="glass-card rounded-3xl p-6 space-y-6">
                        <h2 className="text-sm font-bold uppercase tracking-widest text-slate-400">Clip Settings</h2>

                        {/* Number of shorts */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Number of Shorts</label>
                            <div className="flex flex-wrap gap-2">
                                {[1, 3, 5, 10].map(n => (
                                    <button key={n} type="button" onClick={() => { setNumClips(n); setCustomCount(false); }}
                                        className={`rounded-xl px-5 py-2.5 text-sm font-bold transition-all ${
                                            numClips === n && !customCount ? "bg-primary text-white" : "bg-slate-900/50 text-slate-400 hover:text-white border border-slate-800"
                                        }`}>
                                        {n}
                                    </button>
                                ))}
                                <button type="button" onClick={() => setCustomCount(true)}
                                    className={`rounded-xl px-4 py-2.5 text-sm font-bold transition-all ${
                                        customCount ? "bg-primary text-white" : "bg-slate-900/50 text-slate-400 hover:text-white border border-slate-800"
                                    }`}>
                                    Custom
                                </button>
                                {customCount && (
                                    <input
                                        type="number" min={1} max={20} value={numClips}
                                        onChange={e => setNumClips(Math.max(1, Math.min(20, parseInt(e.target.value || "1", 10))))}
                                        className="w-20 rounded-xl bg-slate-900/50 border border-primary/50 px-3 py-2 text-sm text-white focus:outline-none"
                                    />
                                )}
                            </div>
                        </div>

                        {/* Durations */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Min Duration (s)</label>
                                <input type="number" min={5} max={300} value={minDuration}
                                    onChange={e => {
                                        const v = Math.max(5, Math.min(300, parseInt(e.target.value || "5", 10)));
                                        setMinDuration(v);
                                        if (maxDuration < v) setMaxDuration(v);
                                    }}
                                    className="w-full rounded-xl bg-slate-900/50 border border-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:border-primary focus:outline-none" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Max Duration (s)</label>
                                <input type="number" min={10} max={600} value={maxDuration}
                                    onChange={e => setMaxDuration(Math.max(minDuration, Math.min(600, parseInt(e.target.value || "10", 10))))}
                                    className="w-full rounded-xl bg-slate-900/50 border border-slate-800 px-3 py-2.5 text-sm text-slate-100 focus:border-primary focus:outline-none" />
                            </div>
                        </div>

                        {/* Aspect ratio (fixed) */}
                        <div>
                            <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Aspect Ratio</label>
                            <div className="flex items-center gap-2 rounded-xl bg-slate-900/30 border border-slate-800 px-4 py-2.5">
                                <span className="text-sm font-bold text-slate-300">9:16</span>
                                <span className="text-[10px] text-slate-600 uppercase tracking-wider">vertical — Shorts / Reels / TikTok</span>
                            </div>
                        </div>

                        {/* Captions */}
                        <div className="space-y-3">
                            <Toggle checked={captionsOn} onChange={setCaptionsOn} label="Captions" desc="Burn in automatic subtitles from the transcript" />
                            {captionsOn && captionStyles.length > 0 && (
                                <div className="flex flex-wrap gap-2">
                                    {captionStyles.map(st => (
                                        <button key={st.key} type="button" onClick={() => setCaptionStyle(st.key)}
                                            className={`rounded-lg border px-3 py-1.5 text-xs font-bold transition-all ${
                                                captionStyle === st.key
                                                    ? "border-primary bg-primary/15 text-primary"
                                                    : "border-slate-800 bg-slate-900/30 text-slate-400 hover:border-slate-600"
                                            }`}>
                                            {st.name}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Processing options */}
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <Toggle checked={reframe} onChange={setReframe} label="Auto Reframe" desc="Crop to 9:16 vertical" />
                            <Toggle checked={faceTracking} onChange={setFaceTracking} label="Face Tracking" desc="Follow speakers (MediaPipe, local)" />
                            <Toggle checked={aiDetection} onChange={setAiDetection}
                                label="AI Moment Detection"
                                desc={aiDetection ? "LLM picks the strongest moments" : "Evenly spaced cuts — no API key needed"} />
                            <Toggle checked={wmOn} onChange={setWmOn} label="DKC 57 Watermark" desc="Optional brand overlay (off = no watermark)" />
                        </div>

                        {wmOn && (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 rounded-xl bg-slate-900/30 border border-slate-800 p-4">
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Position</label>
                                    <div className="grid grid-cols-2 gap-2">
                                        {(["top_left", "top_right", "bottom_left", "bottom_right"] as const).map(pos => (
                                            <button key={pos} type="button" onClick={() => setWmPosition(pos)}
                                                className={`rounded-lg border px-2 py-1.5 text-[11px] font-bold capitalize transition-all ${
                                                    wmPosition === pos
                                                        ? "border-primary bg-primary/15 text-primary"
                                                        : "border-slate-800 text-slate-400 hover:border-slate-600"
                                                }`}>
                                                {pos.replace("_", " ")}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                                <div>
                                    <label className="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                                        Opacity — {Math.round(wmOpacity * 100)}%
                                    </label>
                                    <input type="range" min={0.1} max={1} step={0.05} value={wmOpacity}
                                        onChange={e => setWmOpacity(parseFloat(e.target.value))}
                                        className="w-full accent-[#e11d48]" />
                                </div>
                            </div>
                        )}

                        {apiError && (
                            <div className="flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
                                <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                                {apiError}
                            </div>
                        )}

                        <button
                            type="submit"
                            disabled={isProcessing}
                            className="w-full rounded-xl bg-primary py-4 text-sm font-bold text-white glow-primary hover:bg-primary/90 transition-all disabled:opacity-50"
                        >
                            ⚡ CREATE SHORTS
                        </button>
                    </div>
                </form>
            )}

            {/* Live processing view */}
            {isLive && (
                <div className="mx-auto max-w-2xl space-y-6">
                    <div className="text-center mb-8">
                        <span className="mb-4 inline-block rounded-full bg-primary/20 border border-primary/30 px-4 py-1 text-xs font-bold uppercase tracking-widest text-primary">
                            Processing
                        </span>
                        <h1 className="text-3xl font-bold text-white">
                            {STAGE_LABELS[stage] || "Working…"}
                        </h1>
                    </div>

                    <div className="glass-card rounded-3xl p-6 space-y-6">
                        <StageChecklist stage={stage} percent={clampedPercent} message={message} />

                        {message && (
                            <p className="text-sm text-slate-400 rounded-xl bg-black/30 border border-white/5 px-4 py-3">{message}</p>
                        )}

                        <div>
                            <div className="h-2 w-full rounded-full bg-white/10 overflow-hidden">
                                <div
                                    className="h-full rounded-full transition-all duration-500"
                                    style={{ width: `${clampedPercent}%`, background: "linear-gradient(to right, #e11d48, #9f1239)" }}
                                />
                            </div>
                            <p className="mt-1 text-right text-[11px] font-bold text-slate-500">{Math.round(clampedPercent)}%</p>
                        </div>

                        <div className="bg-black/40 rounded-xl p-4 font-mono text-xs space-y-1 max-h-40 overflow-y-auto border border-white/5">
                            {logs.length === 0 ? (
                                <span className="text-slate-600 italic">Connecting…</span>
                            ) : (
                                logs.map((log, i) => (
                                    <p key={i} className="text-slate-400">
                                        <span className="text-primary/60">[LOG]</span> {log}
                                    </p>
                                ))
                            )}
                        </div>

                        <Link href="/" className="block text-center text-xs font-bold text-slate-500 hover:text-white transition-colors">
                            ← Back to dashboard (processing continues in the background)
                        </Link>
                    </div>
                </div>
            )}

            {/* Results: AI Recommended shorts */}
            {!isLive && generatedClips.length > 0 && projectId && (
                <div className="space-y-6">
                    <div className="text-center">
                        <span className="mb-3 inline-flex items-center gap-2 rounded-full bg-primary/20 border border-primary/30 px-4 py-1 text-xs font-bold uppercase tracking-widest text-primary">
                            <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 24 24"><path d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                            AI Recommended
                        </span>
                        <h1 className="text-3xl font-bold text-white mb-2">
                            {generatedClips.length} short{generatedClips.length !== 1 && "s"} ready
                        </h1>
                        <p className="text-sm text-slate-500">
                            Review, edit, reject or export. Scores are AI recommendations — not a guarantee of performance.
                        </p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                        {generatedClips.map((clip, i) => {
                            const scorePct = clip.viral_score != null ? Math.round(clip.viral_score / 10 * 100) : null;
                            return (
                                <div key={clip.id} className="glass rounded-3xl p-4 flex gap-4">
                                    <div className="relative w-24 aspect-[9/16] rounded-2xl overflow-hidden flex-shrink-0 bg-black">
                                        {clip.thumbnail ? (
                                            <img src={fileUrl(clip.thumbnail)} alt="" className="h-full w-full object-cover" />
                                        ) : (
                                            <div className="h-full w-full flex items-center justify-center">
                                                <svg className="h-7 w-7 text-slate-700" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                                            </div>
                                        )}
                                        <span className="absolute bottom-1.5 left-1.5 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-bold text-white">
                                            {formatDuration(clip.duration)}
                                        </span>
                                        {scorePct != null && (
                                            <span className="absolute top-1.5 right-1.5 rounded bg-primary/90 px-1.5 py-0.5 text-[10px] font-bold text-white">
                                                {scorePct}%
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex-1 flex flex-col min-w-0">
                                        <div className="flex items-start justify-between gap-2">
                                            <span className="text-[10px] font-bold uppercase tracking-widest text-slate-600">Short #{i + 1}</span>
                                            {scorePct != null && (
                                                <span className="text-[10px] font-bold text-primary">AI Score: {scorePct}%</span>
                                            )}
                                        </div>
                                        {editingClip === clip.id ? (
                                            <div className="mt-1 flex gap-1">
                                                <input value={editTitle} onChange={e => setEditTitle(e.target.value)} autoFocus
                                                    onKeyDown={e => { if (e.key === "Enter") handleSaveTitle(clip); if (e.key === "Escape") setEditingClip(null); }}
                                                    className="flex-1 min-w-0 rounded-lg bg-black/50 border border-primary/40 px-2 py-1 text-xs text-white focus:outline-none" />
                                                <button onClick={() => handleSaveTitle(clip)} className="rounded-lg bg-primary px-2 text-[10px] font-bold text-white">OK</button>
                                            </div>
                                        ) : (
                                            <h4 className="mt-1 text-sm font-bold text-white line-clamp-2 leading-snug">
                                                {clip.title || `Short ${i + 1}`}
                                            </h4>
                                        )}
                                        {clip.reason && (
                                            <p className="mt-1 text-[11px] text-slate-500 line-clamp-2">{clip.reason}</p>
                                        )}
                                        {clip.hashtags && clip.hashtags.length > 0 && (
                                            <p className="mt-1 text-[10px] text-slate-600 line-clamp-1">
                                                {clip.hashtags.slice(0, 4).join(" ")}
                                            </p>
                                        )}
                                        <div className="mt-auto pt-3 flex flex-wrap gap-1.5">
                                            <button onClick={() => {}} disabled
                                                className="flex-1 py-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 text-[10px] font-bold border border-emerald-500/20"
                                                title="Kept in the project">
                                                ✓ KEPT
                                            </button>
                                            <button onClick={() => { setEditingClip(clip.id); setEditTitle(clip.title || ""); }}
                                                className="flex-1 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-[10px] font-bold text-slate-300 transition-colors">
                                                EDIT
                                            </button>
                                            <a href={clipDownloadUrl(clip)} download
                                                className="flex-1 py-1.5 rounded-lg bg-primary/15 hover:bg-primary text-[10px] font-bold text-primary hover:text-white transition-colors text-center">
                                                EXPORT
                                            </a>
                                            <button onClick={() => handleRejectClip(clip.id)}
                                                className="py-1.5 px-2 rounded-lg bg-white/5 hover:bg-red-500/20 text-[10px] font-bold text-slate-400 hover:text-red-400 transition-colors">
                                                ✕
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            );
                        })}
                    </div>

                    <div className="flex flex-wrap gap-3 justify-center">
                        <button
                            onClick={() => retryProject(projectId).then(() => router.push(`/project/${projectId}`))}
                            className="flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 hover:border-primary/40 px-6 py-3 text-sm font-bold text-slate-300 hover:text-white transition-all"
                        >
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h5M20 20v-5h-5M5.6 9A8 8 0 0119 7.5M18.4 15A8 8 0 015 16.5" /></svg>
                            Regenerate All
                        </button>
                        <Link href="/library" className="flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-bold text-white glow-primary hover:bg-primary/90 transition-all">
                            Open Video Library
                        </Link>
                        <Link href="/create" className="flex items-center gap-2 rounded-xl bg-white/5 border border-white/10 hover:border-primary/40 px-6 py-3 text-sm font-bold text-slate-300 hover:text-white transition-all">
                            + New Project
                        </Link>
                    </div>
                </div>
            )}
        </div>
    );
}
