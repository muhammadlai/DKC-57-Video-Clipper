"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
    getProjects,
    getStats,
    deleteProject,
    createProjectWithSettings,
    uploadVideo,
    cancelProject,
} from "@/lib/api";
import { Project, Stats, ProjectStatus } from "@/lib/types";
import { useProjectProgress } from "@/lib/websocket";
import { DkcLogo } from "@/components/layout/DkcLogo";

const PROCESSING_STATUSES: ProjectStatus[] = [
    "pending", "retrying", "downloading", "transcribing", "analyzing", "processing",
];

function getYouTubeThumbnail(url: string): string | null {
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?/]+)/);
    return match ? `https://img.youtube.com/vi/${match[1]}/hqdefault.jpg` : null;
}

function formatTimeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return "just now";
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

function StatusBadge({ status }: { status: ProjectStatus }) {
    const cfg: Record<string, { label: string; cls: string; pulse?: boolean }> = {
        done: { label: "Completed", cls: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" },
        error: { label: "Failed", cls: "bg-red-500/20 text-red-400 border border-red-500/30" },
        cancelled: { label: "Cancelled", cls: "bg-slate-500/20 text-slate-400 border border-slate-500/30" },
        pending: { label: "Queued", cls: "bg-slate-500/20 text-slate-300 border border-slate-500/30", pulse: true },
        retrying: { label: "Retrying", cls: "bg-amber-500/20 text-amber-400 border border-amber-500/30", pulse: true },
        downloading: { label: "Downloading", cls: "bg-blue-500/20 text-blue-400 border border-blue-500/30", pulse: true },
        transcribing: { label: "Transcribing", cls: "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30", pulse: true },
        analyzing: { label: "AI Analyzing", cls: "bg-violet-500/20 text-violet-400 border border-violet-500/30", pulse: true },
        processing: { label: "Rendering", cls: "bg-primary/20 text-primary border border-primary/30", pulse: true },
    };
    const c = cfg[status] || cfg.pending;
    return (
        <span className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider backdrop-blur-md ${c.cls}`}>
            {c.pulse && <span className="h-1.5 w-1.5 rounded-full bg-current animate-pulse" />}
            {c.label}
        </span>
    );
}

/** Live progress bar for one active job (DKC 57 queue). */
function QueueItem({ project, onDone }: { project: Project; onDone: () => void }) {
    const { stage, percent, message, connected } = useProjectProgress(project.id);

    useEffect(() => {
        if (stage === "done" || stage === "error" || stage === "cancelled") {
            const t = setTimeout(onDone, 2500);
            return () => clearTimeout(t);
        }
    }, [stage, onDone]);

    const pct = Math.min(100, Math.max(0, percent));
    const displayStage = stage === "Initializing..." ? project.status : stage;

    return (
        <div className="rounded-2xl bg-panel border border-white/5 p-4">
            <div className="flex items-center justify-between gap-3 mb-2">
                <div className="min-w-0">
                    <p className="text-sm font-bold text-white truncate">
                        {project.title || (project.source_type === "upload" ? "Uploaded video" : "YouTube video")}
                    </p>
                    <p className="text-[11px] text-slate-500 truncate">
                        {message || displayStage}
                    </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                    <StatusBadge status={stage === "done" ? "done" : stage === "error" ? "error" : stage === "cancelled" ? "cancelled" : project.status} />
                    {PROCESSING_STATUSES.includes(project.status) && stage !== "done" && stage !== "error" && (
                        <button
                            onClick={() => cancelProject(project.id).then(onDone).catch(console.error)}
                            className="rounded-lg bg-white/5 hover:bg-red-500/20 border border-white/10 hover:border-red-500/30 px-3 py-1 text-[10px] font-bold text-slate-300 hover:text-red-400 transition-colors"
                        >
                            CANCEL
                        </button>
                    )}
                </div>
            </div>
            <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                <div
                    className="h-full rounded-full bg-gradient-to-r from-primary to-accent-red transition-all duration-500"
                    style={{ width: `${pct}%` }}
                />
            </div>
            {!connected && stage === "Initializing..." && (
                <p className="mt-1 text-[10px] text-slate-600">Connecting to progress stream…</p>
            )}
        </div>
    );
}

export default function Dashboard() {
    return (
        <Suspense>
            <DashboardInner />
        </Suspense>
    );
}

function DashboardInner() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const searchQuery = (searchParams.get("q") || "").toLowerCase();

    const [projects, setProjects] = useState<Project[]>([]);
    const [stats, setStats] = useState<Stats>({ videos: 0, shorts: 0, processing: 0, failed: 0 });
    const [loading, setLoading] = useState(true);
    const [urlInput, setUrlInput] = useState("");
    const [submitting, setSubmitting] = useState(false);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const urlRef = useRef<HTMLInputElement>(null);
    const fileRef = useRef<HTMLInputElement>(null);
    const [dragOver, setDragOver] = useState(false);

    const refresh = useCallback(() => {
        getProjects().then(setProjects).catch(console.error).finally(() => setLoading(false));
        getStats().then(setStats).catch(console.error);
    }, []);

    useEffect(() => {
        refresh();
        const t = setInterval(refresh, 5000);
        return () => clearInterval(t);
    }, [refresh]);

    const handleDelete = async (e: React.MouseEvent, id: string) => {
        e.preventDefault();
        e.stopPropagation();
        await deleteProject(id).catch(console.error);
        refresh();
    };

    const handleQuickCreate = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!urlInput.trim() || submitting) return;
        setSubmitting(true);
        setError(null);
        try {
            const { project_id } = await createProjectWithSettings(urlInput.trim());
            router.push(`/project/${project_id}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to create project");
            setSubmitting(false);
        }
    };

    const handleFiles = async (files: FileList | File[]) => {
        const list = Array.from(files).filter(f =>
            /\.(mp4|mov|mkv|webm|avi|m4v)$/i.test(f.name)
        );
        if (list.length === 0) {
            setError("No supported video files (mp4, mov, mkv, webm, avi).");
            return;
        }
        setUploading(true);
        setError(null);
        try {
            // Background queue: each upload starts a job on the server.
            await Promise.all(list.map(f => uploadVideo(f)));
            refresh();
            router.push("/?queue=1");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Upload failed");
        } finally {
            setUploading(false);
            if (fileRef.current) fileRef.current.value = "";
        }
    };

    const handlePaste = async () => {
        try {
            const text = await navigator.clipboard.readText();
            setUrlInput(text);
            urlRef.current?.focus();
        } catch { /* ignore */ }
    };

    const queue = projects.filter(p => PROCESSING_STATUSES.includes(p.status));
    const recent = projects
        .filter(p =>
            !searchQuery ||
            (p.title || "").toLowerCase().includes(searchQuery) ||
            (p.youtube_url || "").toLowerCase().includes(searchQuery)
        )
        .slice(0, 12);

    return (
        <div className="mx-auto w-full max-w-7xl px-6 lg:px-20 py-10">

            {/* Header band */}
            <section className="relative mb-10 overflow-hidden rounded-3xl border border-white/5 bg-panel">
                <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(225,29,72,0.18),transparent_55%)]" />
                <div className="relative flex flex-col lg:flex-row lg:items-center gap-8 p-8 lg:p-12">
                    <div className="flex items-center gap-5">
                        <DkcLogo size={72} />
                        <div>
                            <h1 className="text-3xl lg:text-4xl font-bold tracking-tight text-white">
                                DKC 57 <span className="text-primary">VIDEO CLIPPER</span>
                            </h1>
                            <p className="mt-1 text-sm font-semibold uppercase tracking-[0.25em] text-slate-500">
                                AI-Powered Shorts Generator
                            </p>
                        </div>
                    </div>
                    <div className="flex-1" />
                    {/* Stat cards */}
                    <div className="grid grid-cols-3 gap-4 lg:w-auto">
                        {[
                            { label: "Videos", value: stats.videos, cls: "text-white" },
                            { label: "Shorts", value: stats.shorts, cls: "text-primary" },
                            { label: "Processing", value: stats.processing, cls: "text-amber-400" },
                        ].map(s => (
                            <div key={s.label} className="rounded-2xl bg-black/40 border border-white/5 px-6 py-4 text-center min-w-[110px]">
                                <p className={`text-3xl font-bold tabular-nums ${s.cls}`}>{s.value}</p>
                                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mt-1">{s.label}</p>
                            </div>
                        ))}
                    </div>
                </div>
            </section>

            {/* Upload hero */}
            <section className="mb-10 grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* File upload */}
                <div
                    onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files); }}
                    className={`relative flex flex-col items-center justify-center gap-4 rounded-3xl border-2 border-dashed p-10 text-center transition-all ${
                        dragOver ? "border-primary bg-primary/10" : "border-white/10 bg-panel hover:border-primary/40"
                    }`}
                >
                    <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15 border border-primary/25">
                        <svg className="h-7 w-7 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M12 4v12m0-12l-4 4m4-4l4 4" />
                        </svg>
                    </div>
                    <div>
                        <p className="text-lg font-bold text-white">
                            {uploading ? "Uploading to background queue…" : "Upload long videos"}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                            Drag & drop or browse — mp4, mov, mkv, webm, avi.
                            Multiple files supported (bulk processing).
                        </p>
                    </div>
                    <button
                        onClick={() => fileRef.current?.click()}
                        disabled={uploading}
                        className="flex items-center gap-2 rounded-xl bg-primary px-6 py-3.5 text-sm font-bold text-white glow-primary hover:bg-primary/90 transition-all disabled:opacity-50"
                    >
                        <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                        + UPLOAD VIDEO
                    </button>
                    <input
                        ref={fileRef}
                        type="file"
                        accept=".mp4,.mov,.mkv,.webm,.avi,.m4v"
                        multiple
                        className="hidden"
                        onChange={e => e.target.files && handleFiles(e.target.files)}
                    />
                </div>

                {/* YouTube URL + settings CTA */}
                <div className="flex flex-col justify-between gap-6 rounded-3xl bg-panel border border-white/5 p-8">
                    <div>
                        <h2 className="text-xl font-bold text-white mb-1">Create Shorts</h2>
                        <p className="text-sm text-slate-500">
                            Paste a YouTube link, or open the full workflow to configure
                            clip count, duration, captions, face tracking, watermark and more.
                        </p>
                    </div>
                    <form onSubmit={handleQuickCreate} className="flex items-center gap-2 rounded-xl bg-black/40 px-4 py-3 border border-white/10 focus-within:border-primary/50 transition-all">
                        <svg className="h-5 w-5 text-slate-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" /></svg>
                        <input
                            ref={urlRef}
                            value={urlInput}
                            onChange={e => setUrlInput(e.target.value)}
                            className="flex-1 bg-transparent border-none text-sm text-white placeholder-slate-500 focus:ring-0 focus:outline-none p-0"
                            placeholder="Paste YouTube link…"
                            type="text"
                        />
                        <button
                            type="button"
                            onClick={handlePaste}
                            className="rounded-lg bg-white/5 px-3 py-1.5 text-xs font-bold text-slate-300 hover:bg-white/10 transition-colors uppercase tracking-wider"
                        >
                            Paste
                        </button>
                    </form>
                    {error && (
                        <div className="flex items-center gap-2 rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">
                            <svg className="h-4 w-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                            {error}
                        </div>
                    )}
                    <div className="flex flex-wrap gap-3">
                        <Link
                            href="/create"
                            className="flex flex-1 items-center justify-center gap-2 rounded-xl bg-primary px-6 py-4 text-sm font-bold text-white glow-primary hover:bg-primary/90 transition-all"
                        >
                            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>
                            CREATE SHORTS
                        </Link>
                    </div>
                </div>
            </section>

            {/* Processing queue */}
            {queue.length > 0 && (
                <section className="mb-10">
                    <div className="mb-4 flex items-center justify-between">
                        <h2 className="flex items-center gap-2 text-lg font-bold text-white">
                            <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                            Processing Queue
                            <span className="text-xs font-bold text-slate-500">({queue.length} active)</span>
                        </h2>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {queue.map(p => (
                            <QueueItem key={p.id} project={p} onDone={refresh} />
                        ))}
                    </div>
                </section>
            )}

            {/* Recent projects */}
            <section>
                <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-lg font-bold text-white">
                        Recent Projects
                        {searchQuery && <span className="text-xs text-slate-500 font-normal"> (filtered by “{searchQuery}”)</span>}
                    </h2>
                    <Link href="/library" className="text-xs font-bold uppercase tracking-wider text-primary hover:text-white transition-colors">
                        Video Library →
                    </Link>
                </div>

                {loading ? (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {[...Array(3)].map((_, i) => (
                            <div key={i} className="h-24 rounded-2xl bg-panel border border-white/5 animate-pulse" />
                        ))}
                    </div>
                ) : recent.length === 0 ? (
                    <div className="rounded-3xl bg-panel border border-white/5 py-16 text-center">
                        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10 border border-primary/20">
                            <svg className="h-8 w-8 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.069A1 1 0 0121 8.87v6.26a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" /></svg>
                        </div>
                        <p className="text-slate-300 font-semibold">No projects yet</p>
                        <p className="text-slate-500 text-sm mt-1">Upload a video or paste a YouTube URL to create your first shorts</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        {recent.map(project => {
                            const thumb = getYouTubeThumbnail(project.youtube_url);
                            return (
                                <Link
                                    key={project.id}
                                    href={`/project/${project.id}`}
                                    className="group flex items-center gap-4 rounded-2xl bg-panel border border-white/5 p-4 hover:border-primary/40 transition-all"
                                >
                                    <div className="relative w-20 aspect-[9/16] rounded-xl overflow-hidden flex-shrink-0 bg-black flex items-center justify-center">
                                        {thumb ? (
                                            <img src={thumb} alt="" className="h-full w-full object-cover" />
                                        ) : project.source_type === "upload" ? (
                                            <svg className="h-7 w-7 text-primary/50" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                                        ) : (
                                            <svg className="h-7 w-7 text-slate-700" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                                        )}
                                        <span className="absolute bottom-1 left-1 right-1 rounded bg-black/70 px-1 py-0.5 text-center text-[9px] font-bold text-white">
                                            {project.source_type === "upload" ? "UPLOAD" : "YT"}
                                        </span>
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <h3 className="font-bold text-white group-hover:text-primary transition-colors truncate text-sm">
                                            {project.title || (project.source_type === "upload" ? "Uploaded video" : "Untitled")}
                                        </h3>
                                        <p className="mt-0.5 text-xs text-slate-500">
                                            {formatTimeAgo(project.created_at)}
                                            {project.clip_count ? ` • ${project.clip_count} shorts` : ""}
                                        </p>
                                        <div className="mt-2"><StatusBadge status={project.status} /></div>
                                    </div>
                                    <button
                                        onClick={e => handleDelete(e, project.id)}
                                        className="text-slate-700 hover:text-red-400 transition-colors flex-shrink-0 opacity-0 group-hover:opacity-100"
                                        title="Delete project"
                                    >
                                        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                    </button>
                                </Link>
                            );
                        })}
                    </div>
                )}
            </section>
        </div>
    );
}
