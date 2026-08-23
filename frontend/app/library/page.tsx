"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
    getProjects,
    getClips,
    deleteClip,
    deleteProject,
    updateClipTitle,
    retryProject,
    clipDownloadUrl,
    fileUrl,
} from "@/lib/api";
import { Project, Clip, ProjectStatus } from "@/lib/types";

function formatTimeAgo(dateStr: string): string {
    const diff = Date.now() - new Date(dateStr).getTime();
    const hours = Math.floor(diff / 3600000);
    if (hours < 1) return "just now";
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
}

function formatDuration(s: number) {
    const m = Math.floor(s / 60);
    const sec = Math.round(s % 60);
    return `${m}:${sec.toString().padStart(2, "0")}`;
}

function getYouTubeThumbnail(url: string): string | null {
    const match = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?/]+)/);
    return match ? `https://img.youtube.com/vi/${match[1]}/hqdefault.jpg` : null;
}

function StatusBadge({ status }: { status: ProjectStatus }) {
    const cfg: Record<string, { label: string; cls: string }> = {
        done: { label: "Completed", cls: "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" },
        error: { label: "Failed", cls: "bg-red-500/20 text-red-400 border border-red-500/30" },
        cancelled: { label: "Cancelled", cls: "bg-slate-500/20 text-slate-400 border border-slate-500/30" },
        pending: { label: "Queued", cls: "bg-slate-500/20 text-slate-300 border border-slate-500/30" },
        retrying: { label: "Retrying", cls: "bg-amber-500/20 text-amber-400 border border-amber-500/30" },
        downloading: { label: "Downloading", cls: "bg-blue-500/20 text-blue-400 border border-blue-500/30" },
        transcribing: { label: "Transcribing", cls: "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30" },
        analyzing: { label: "AI Analyzing", cls: "bg-violet-500/20 text-violet-400 border border-violet-500/30" },
        processing: { label: "Rendering", cls: "bg-primary/20 text-primary border border-primary/30" },
    };
    const c = cfg[status] || cfg.pending;
    return (
        <span className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${c.cls}`}>
            {c.label}
        </span>
    );
}

/** Simple video preview modal (DKC 57). */
function PreviewModal({ clip, onClose }: { clip: Clip; onClose: () => void }) {
    return (
        <div
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 backdrop-blur-sm p-6"
            onClick={onClose}
        >
            <div
                className="relative w-full max-w-sm rounded-3xl bg-panel border border-white/10 p-5"
                onClick={e => e.stopPropagation()}
            >
                <button
                    onClick={onClose}
                    className="absolute -top-3 -right-3 z-10 flex h-8 w-8 items-center justify-center rounded-full bg-black border border-white/20 text-slate-300 hover:text-white"
                >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
                </button>
                <video
                    key={clip.id}
                    src={fileUrl(clip.file_path)}
                    controls
                    autoPlay
                    playsInline
                    className="w-full aspect-[9/16] rounded-2xl bg-black"
                />
                <p className="mt-3 text-sm font-bold text-white truncate">{clip.title || "Untitled short"}</p>
                <p className="text-[11px] text-slate-500">
                    {formatDuration(clip.duration)} • {clip.project_title || "Unknown project"}
                </p>
                <a
                    href={clipDownloadUrl(clip)}
                    download
                    className="mt-3 flex items-center justify-center gap-2 rounded-xl bg-primary py-3 text-sm font-bold text-white hover:bg-primary/90 transition-all"
                >
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5 5 5-5M12 15V3" /></svg>
                    EXPORT
                </a>
            </div>
        </div>
    );
}

export default function LibraryPage() {
    const [projects, setProjects] = useState<Project[]>([]);
    const [clips, setClips] = useState<Clip[]>([]);
    const [loading, setLoading] = useState(true);
    const [preview, setPreview] = useState<Clip | null>(null);
    const [editingId, setEditingId] = useState<string | null>(null);
    const [editTitle, setEditTitle] = useState("");

    const refresh = useCallback(() => {
        Promise.all([getProjects(), getClips()])
            .then(([p, c]) => { setProjects(p); setClips(c); })
            .catch(console.error)
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => {
        refresh();
        const t = setInterval(refresh, 8000);
        return () => clearInterval(t);
    }, [refresh]);

    const handleDeleteClip = async (id: string) => {
        await deleteClip(id).catch(console.error);
        refresh();
    };

    const handleSaveTitle = async (clip: Clip) => {
        const title = editTitle.trim();
        if (title) {
            await updateClipTitle(clip.id, title).catch(console.error);
        }
        setEditingId(null);
        refresh();
    };

    const handleRegenerate = async (projectId: string) => {
        if (!confirm("Regenerate all shorts for this video? Existing shorts will be replaced.")) return;
        await retryProject(projectId).catch(console.error);
        refresh();
    };

    if (loading) {
        return (
            <div className="mx-auto w-full max-w-7xl px-6 lg:px-20 py-10">
                <div className="h-8 w-64 rounded-xl bg-panel animate-pulse mb-8" />
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[...Array(6)].map((_, i) => (
                        <div key={i} className="h-40 rounded-2xl bg-panel border border-white/5 animate-pulse" />
                    ))}
                </div>
            </div>
        );
    }

    return (
        <div className="mx-auto w-full max-w-7xl px-6 lg:px-20 py-10">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white">DKC 57 <span className="text-primary">VIDEO LIBRARY</span></h1>
                <p className="mt-1 text-sm text-slate-500">
                    Source videos and every generated short, in one place.
                </p>
            </header>

            {/* Source videos */}
            <section className="mb-12">
                <h2 className="mb-4 text-lg font-bold text-white">
                    Source Videos <span className="text-xs text-slate-500 font-normal">({projects.length})</span>
                </h2>
                {projects.length === 0 ? (
                    <div className="rounded-2xl bg-panel border border-white/5 py-10 text-center text-sm text-slate-500">
                        No source videos yet — <Link href="/" className="text-primary font-bold">upload one</Link> to get started.
                    </div>
                ) : (
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                        {projects.map(p => {
                            const thumb = getYouTubeThumbnail(p.youtube_url);
                            return (
                                <div key={p.id} className="group rounded-2xl bg-panel border border-white/5 overflow-hidden hover:border-primary/40 transition-all">
                                    <Link href={`/project/${p.id}`} className="block">
                                        <div className="relative aspect-video bg-black flex items-center justify-center">
                                            {thumb ? (
                                                <img src={thumb} alt="" className="h-full w-full object-cover" />
                                            ) : (
                                                <svg className="h-10 w-10 text-slate-700" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                                            )}
                                            <span className="absolute top-2 left-2 rounded bg-black/70 px-2 py-0.5 text-[9px] font-bold text-white">
                                                {p.source_type === "upload" ? "UPLOAD" : "YOUTUBE"}
                                            </span>
                                        </div>
                                    </Link>
                                    <div className="p-4">
                                        <Link href={`/project/${p.id}`} className="block">
                                            <h3 className="text-sm font-bold text-white truncate group-hover:text-primary transition-colors">
                                                {p.title || "Untitled"}
                                            </h3>
                                        </Link>
                                        <p className="mt-1 text-[11px] text-slate-500">
                                            {formatTimeAgo(p.created_at)} • {p.clip_count || 0} shorts
                                        </p>
                                        <div className="mt-2 flex items-center justify-between">
                                            <StatusBadge status={p.status} />
                                            <div className="flex gap-1">
                                                <button
                                                    onClick={() => handleRegenerate(p.id)}
                                                    title="Regenerate shorts"
                                                    className="rounded-lg bg-white/5 hover:bg-primary/20 border border-white/10 px-2 py-1 text-[10px] font-bold text-slate-300 hover:text-primary transition-colors"
                                                >
                                                    REGEN
                                                </button>
                                                <button
                                                    onClick={() => { if (confirm("Delete this project and all its shorts?")) deleteProject(p.id).then(refresh); }}
                                                    title="Delete project"
                                                    className="rounded-lg bg-white/5 hover:bg-red-500/20 border border-white/10 hover:border-red-500/30 px-2 py-1 text-[10px] font-bold text-slate-300 hover:text-red-400 transition-colors"
                                                >
                                                    DEL
                                                </button>
                                            </div>
                                        </div>
                                        {p.error_message && (
                                            <p className="mt-2 text-[10px] text-red-400/80 line-clamp-2" title={p.error_message}>
                                                {p.error_message}
                                            </p>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                    </div>
                )}
            </section>

            {/* Generated shorts */}
            <section>
                <h2 className="mb-4 text-lg font-bold text-white">
                    Generated Shorts <span className="text-xs text-slate-500 font-normal">({clips.length})</span>
                </h2>
                {clips.length === 0 ? (
                    <div className="rounded-2xl bg-panel border border-white/5 py-10 text-center text-sm text-slate-500">
                        No shorts generated yet.
                    </div>
                ) : (
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
                        {clips.map((clip, i) => (
                            <div key={clip.id} className="group rounded-2xl bg-panel border border-white/5 overflow-hidden hover:border-primary/40 transition-all">
                                <button onClick={() => setPreview(clip)} className="block w-full">
                                    <div className="relative aspect-[9/16] bg-black overflow-hidden">
                                        {clip.thumbnail ? (
                                            <img
                                                src={fileUrl(clip.thumbnail)}
                                                alt=""
                                                className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
                                            />
                                        ) : (
                                            <div className="h-full w-full flex items-center justify-center">
                                                <svg className="h-8 w-8 text-slate-700" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                                            </div>
                                        )}
                                        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/40">
                                            <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/90 text-black">
                                                <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z" /></svg>
                                            </span>
                                        </div>
                                        <span className="absolute bottom-2 left-2 rounded bg-black/75 px-1.5 py-0.5 text-[10px] font-bold text-white">
                                            {formatDuration(clip.duration)}
                                        </span>
                                        {clip.viral_score != null && (
                                            <span className="absolute top-2 right-2 rounded bg-primary/90 px-1.5 py-0.5 text-[9px] font-bold text-white">
                                                AI {Math.round(clip.viral_score / 10 * 100)}%
                                            </span>
                                        )}
                                    </div>
                                </button>
                                <div className="p-3">
                                    {editingId === clip.id ? (
                                        <div className="flex gap-1">
                                            <input
                                                value={editTitle}
                                                onChange={e => setEditTitle(e.target.value)}
                                                autoFocus
                                                onKeyDown={e => {
                                                    if (e.key === "Enter") handleSaveTitle(clip);
                                                    if (e.key === "Escape") setEditingId(null);
                                                }}
                                                className="w-full rounded-lg bg-black/50 border border-primary/40 px-2 py-1 text-xs text-white focus:outline-none"
                                            />
                                            <button onClick={() => handleSaveTitle(clip)} className="rounded-lg bg-primary px-2 text-[10px] font-bold text-white">OK</button>
                                        </div>
                                    ) : (
                                        <h4 className="text-xs font-bold text-white line-clamp-2 leading-snug min-h-[2rem]" title={clip.title || ""}>
                                            {clip.title || `Short ${i + 1}`}
                                        </h4>
                                    )}
                                    <p className="mt-0.5 text-[10px] text-slate-600 truncate">
                                        {clip.project_title || "—"}
                                        {clip.captioned ? " • captions" : ""}
                                    </p>
                                    <div className="mt-2 flex gap-1">
                                        <button
                                            onClick={() => setPreview(clip)}
                                            className="flex-1 rounded-lg bg-white/5 hover:bg-primary/20 py-1 text-[9px] font-bold text-slate-300 hover:text-primary transition-colors"
                                        >
                                            PREVIEW
                                        </button>
                                        <button
                                            onClick={() => { setEditingId(clip.id); setEditTitle(clip.title || ""); }}
                                            className="flex-1 rounded-lg bg-white/5 hover:bg-white/10 py-1 text-[9px] font-bold text-slate-300 transition-colors"
                                        >
                                            EDIT
                                        </button>
                                        <a
                                            href={clipDownloadUrl(clip)}
                                            download
                                            className="flex-1 rounded-lg bg-primary/15 hover:bg-primary py-1 text-[9px] font-bold text-primary hover:text-white transition-colors text-center"
                                        >
                                            EXPORT
                                        </a>
                                        <button
                                            onClick={() => handleDeleteClip(clip.id)}
                                            className="rounded-lg bg-white/5 hover:bg-red-500/20 py-1 px-1.5 text-[9px] font-bold text-slate-400 hover:text-red-400 transition-colors"
                                        >
                                            <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>

            {preview && <PreviewModal clip={preview} onClose={() => setPreview(null)} />}
        </div>
    );
}
