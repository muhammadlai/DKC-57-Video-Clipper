import { Project, Clip, Settings, CaptionStyle } from './types';

function getBaseUrl(): string {
    if (typeof window !== 'undefined') {
        const host = window.location.hostname;
        if (host !== 'localhost' && host !== '127.0.0.1') {
            return `https://${host.replace(/^(\d+)-/, '8000-')}`;
        }
    }
    return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
}

export function getApiBaseUrl(): string {
    return getBaseUrl();
}

export const getProjects = async (): Promise<Project[]> => {
    try {
        const res = await fetch(`${getBaseUrl()}/api/projects`, { cache: 'no-store' });
        if (!res.ok) return [];
        return res.json();
    } catch {
        // Backend not running or network error - return empty array
        return [];
    }
};

export const getProject = async (id: string): Promise<Project & { clips: Clip[] }> => {
    const res = await fetch(`${getBaseUrl()}/api/projects/${id}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Project not found");
    return res.json();
};

export const createProject = async (youtube_url: string): Promise<{ project_id: string }> => {
    const res = await fetch(`${getBaseUrl()}/api/projects`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ youtube_url })
    });
    if (!res.ok) throw new Error("Failed to create project");
    return res.json();
};

export const deleteProject = async (id: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/projects/${id}`, {
        method: 'DELETE'
    });
    if (!res.ok) throw new Error("Failed to delete project");
};

export async function getSettings(): Promise<Settings> {
    try {
        const res = await fetch(`${getBaseUrl()}/api/settings`);
        if (!res.ok) {
            // Return default settings if backend returns error
            return {
                llm_provider: "openai",
                llm_model: "gpt-4o",
                whisper_model: "base",
                caption_style: "viral_word",
                has_api_key: false
            };
        }
        return res.json();
    } catch {
        // Backend not running - return default settings
        return {
            llm_provider: "openai",
            llm_model: "gpt-4o",
            whisper_model: "base",
            caption_style: "viral_word",
            has_api_key: false
        };
    }
}

export async function saveSettings(
    settings: Partial<Settings> & { llm_api_key?: string }
): Promise<void> {
    const res = await fetch(`${getBaseUrl()}/api/settings`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings)
    });
    if (!res.ok) throw new Error("Failed to save settings");
}

export async function getCaptionStyles(): Promise<CaptionStyle[]> {
    try {
        const res = await fetch(`${getBaseUrl()}/api/caption-styles`);
        if (res.ok) return res.json();
    } catch {
    }
    return [
        {
            key: "none",
            name: "No Captions",
            animation: "word_by_word",
            preview_colors: { text: "#666666", highlight: null, background: null }
        },
        {
            key: "classic_white",
            name: "Classic White",
            animation: "word_by_word",
            preview_colors: { text: "#FFFFFF", highlight: null, background: null }
        },
        {
            key: "tiktok_style",
            name: "TikTok Style",
            animation: "highlight",
            preview_colors: { text: "#FFFFFF", highlight: "#FFFF00", background: null }
        },
        {
            key: "viral_word",
            name: "Viral Word",
            animation: "one_word",
            preview_colors: { text: "#FFFFFF", highlight: null, background: null }
        }
    ];
}

// ---------------------------------------------------------------------------
// DKC 57 — stats, upload, bulk, retry/cancel, clips
// ---------------------------------------------------------------------------

import { ClipSettings, Stats } from './types';

function getAuthHeaders(): Record<string, string> {
    const key = process.env.NEXT_PUBLIC_API_KEY;
    return key ? { 'X-API-Key': key } : {};
}

export const getStats = async (): Promise<Stats> => {
    try {
        const res = await fetch(`${getBaseUrl()}/api/stats`, { cache: 'no-store', headers: getAuthHeaders() });
        if (!res.ok) return { videos: 0, shorts: 0, processing: 0, failed: 0 };
        return res.json();
    } catch {
        return { videos: 0, shorts: 0, processing: 0, failed: 0 };
    }
};

export const createProjectWithSettings = async (
    youtube_url: string,
    settings?: ClipSettings
): Promise<{ project_id: string }> => {
    const res = await fetch(`${getBaseUrl()}/api/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ youtube_url, settings }),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || "Failed to create project");
    }
    return res.json();
};

export const uploadVideo = async (
    file: File,
    settings?: ClipSettings
): Promise<{ project_id: string }> => {
    const form = new FormData();
    form.append('file', file);
    if (settings) form.append('settings_json', JSON.stringify(settings));
    const res = await fetch(`${getBaseUrl()}/api/projects/upload`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: form,
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || "Upload failed");
    }
    return res.json();
};

export const bulkCreateProjects = async (
    youtube_urls: string[],
    settings?: ClipSettings
): Promise<{ projects: { project_id: string; status: string }[] }> => {
    const res = await fetch(`${getBaseUrl()}/api/projects/bulk`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ youtube_urls, settings }),
    });
    if (!res.ok) {
        const detail = await res.json().catch(() => null);
        throw new Error(detail?.detail || "Bulk create failed");
    }
    return res.json();
};

export const retryProject = async (id: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/projects/${id}/retry`, {
        method: 'POST',
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to retry project");
};

export const cancelProject = async (id: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/projects/${id}/cancel`, {
        method: 'POST',
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to cancel project");
};

export const getClips = async (): Promise<Clip[]> => {
    const res = await fetch(`${getBaseUrl()}/api/clips`, { cache: 'no-store', headers: getAuthHeaders() });
    if (!res.ok) return [];
    return res.json();
};

export const deleteClip = async (id: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/clips/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(),
    });
    if (!res.ok) throw new Error("Failed to delete clip");
};

export const updateClipTitle = async (id: string, title: string): Promise<void> => {
    const res = await fetch(`${getBaseUrl()}/api/clips/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ title }),
    });
    if (!res.ok) throw new Error("Failed to update clip");
};

export const clipDownloadUrl = (clip: Clip): string =>
    `${getBaseUrl()}/api/clips/${clip.id}/download`;

export const fileUrl = (path: string): string =>
    path.startsWith('http') ? path : `${getBaseUrl()}${path}`;
