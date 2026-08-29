import {
  Project,
  Clip,
  Settings,
  CaptionStyle,
  ClipSettings,
  Stats,
  CommandCenterState,
  AdminSession,
  AdminConfigResponse,
} from './types';

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

function getAuthHeaders(): Record<string, string> {
  const key = process.env.NEXT_PUBLIC_API_KEY;
  return key ? { 'X-API-Key': key } : {};
}

async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  return fetch(`${getBaseUrl()}${path}`, {
    credentials: 'include',
    cache: 'no-store',
    ...init,
    headers: {
      ...getAuthHeaders(),
      ...(init?.headers || {}),
    },
  });
}

export const getProjects = async (): Promise<Project[]> => {
  try {
    const res = await apiFetch('/api/projects');
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
};

export const getProject = async (id: string): Promise<Project & { clips: Clip[] }> => {
  const res = await apiFetch(`/api/projects/${id}`);
  if (!res.ok) throw new Error('Project not found');
  return res.json();
};

export const createProject = async (youtube_url: string): Promise<{ project_id: string }> => {
  const res = await apiFetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url }),
  });
  if (!res.ok) throw new Error('Failed to create project');
  return res.json();
};

export const deleteProject = async (id: string): Promise<void> => {
  const res = await apiFetch(`/api/projects/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete project');
};

export async function getSettings(): Promise<Settings> {
  try {
    const res = await apiFetch('/api/settings');
    if (!res.ok) {
      return {
        whisper_model: 'base',
        caption_style: 'viral_word',
      };
    }
    return res.json();
  } catch {
    return {
      whisper_model: 'base',
      caption_style: 'viral_word',
    };
  }
}

export async function saveSettings(
  settings: Partial<Settings>
): Promise<void> {
  const res = await apiFetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
  });
  if (!res.ok) throw new Error('Failed to save settings');
}

export async function getCaptionStyles(): Promise<CaptionStyle[]> {
  try {
    const res = await apiFetch('/api/caption-styles');
    if (res.ok) return res.json();
  } catch {
  }
  return [
    {
      key: 'none',
      name: 'No Captions',
      animation: 'word_by_word',
      preview_colors: { text: '#666666', highlight: null, background: null },
    },
    {
      key: 'classic_white',
      name: 'Classic White',
      animation: 'word_by_word',
      preview_colors: { text: '#FFFFFF', highlight: null, background: null },
    },
    {
      key: 'tiktok_style',
      name: 'TikTok Style',
      animation: 'highlight',
      preview_colors: { text: '#FFFFFF', highlight: '#FFFF00', background: null },
    },
    {
      key: 'viral_word',
      name: 'Viral Word',
      animation: 'one_word',
      preview_colors: { text: '#FFFFFF', highlight: null, background: null },
    },
  ];
}

export const getStats = async (): Promise<Stats> => {
  try {
    const res = await apiFetch('/api/stats');
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
  const res = await apiFetch('/api/projects', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_url, settings }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || 'Failed to create project');
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
  const res = await apiFetch('/api/projects/upload', {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || 'Upload failed');
  }
  return res.json();
};

export const bulkCreateProjects = async (
  youtube_urls: string[],
  settings?: ClipSettings
): Promise<{ projects: { project_id: string; status: string }[] }> => {
  const res = await apiFetch('/api/projects/bulk', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ youtube_urls, settings }),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail || 'Bulk create failed');
  }
  return res.json();
};

export const retryProject = async (id: string): Promise<void> => {
  const res = await apiFetch(`/api/projects/${id}/retry`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to retry project');
};

export const cancelProject = async (id: string): Promise<void> => {
  const res = await apiFetch(`/api/projects/${id}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to cancel project');
};

export const getClips = async (): Promise<Clip[]> => {
  const res = await apiFetch('/api/clips');
  if (!res.ok) return [];
  return res.json();
};

export const deleteClip = async (id: string): Promise<void> => {
  const res = await apiFetch(`/api/clips/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete clip');
};

export const updateClipTitle = async (id: string, title: string): Promise<void> => {
  const res = await apiFetch(`/api/clips/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error('Failed to update clip');
};

export const clipDownloadUrl = (clip: Clip): string =>
  `${getBaseUrl()}/api/clips/${clip.id}/download`;

export const fileUrl = (path: string): string =>
  path.startsWith('http') ? path : `${getBaseUrl()}${path}`;

export const getCommandCenterState = async (): Promise<CommandCenterState> => {
  const res = await apiFetch('/api/command-center/state');
  if (!res.ok) throw new Error('Failed to load command center state');
  return res.json();
};

export const startYouTubeAuth = async (): Promise<{ auth_url: string }> => {
  const res = await apiFetch('/api/youtube/auth/start', { method: 'POST' });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to start YouTube OAuth');
  return body;
};

export const disconnectYouTube = async (): Promise<CommandCenterState> => {
  const res = await apiFetch('/api/youtube/disconnect', { method: 'POST' });
  if (!res.ok) throw new Error('Failed to disconnect YouTube');
  return res.json();
};

export const getAdminSession = async (): Promise<AdminSession> => {
  const res = await apiFetch('/api/admin/session');
  if (!res.ok) throw new Error('Failed to load admin session');
  return res.json();
};

export const unlockAdmin = async (code: string): Promise<AdminSession & { message: string }> => {
  const res = await apiFetch('/api/admin/unlock', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code }),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to unlock admin mode');
  return body;
};

export const lockAdmin = async (): Promise<void> => {
  const res = await apiFetch('/api/admin/lock', { method: 'POST' });
  if (!res.ok) throw new Error('Failed to lock admin mode');
};

export const getAdminConfig = async (): Promise<AdminConfigResponse> => {
  const res = await apiFetch('/api/admin/config');
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to load admin config');
  return body;
};

export const saveAdminConfig = async (payload: Partial<AdminConfigResponse['config']>): Promise<AdminConfigResponse> => {
  const res = await apiFetch('/api/admin/config', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to save admin config');
  return body;
};

export const startProductionMode = async (): Promise<CommandCenterState> => {
  const res = await apiFetch('/api/production/start', { method: 'POST' });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to start production mode');
  return body;
};

export const stopProductionMode = async (): Promise<CommandCenterState> => {
  const res = await apiFetch('/api/production/stop', { method: 'POST' });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to stop production mode');
  return body;
};

export const approvePublishingJob = async (jobId: string): Promise<CommandCenterState> => {
  const res = await apiFetch(`/api/publishing/jobs/${jobId}/approve`, { method: 'POST' });
  const body = await res.json().catch(() => null);
  if (!res.ok) throw new Error(body?.detail || 'Failed to approve publishing job');
  return body;
};
