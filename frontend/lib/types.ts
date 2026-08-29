export type ProjectStatus =
  | 'pending'
  | 'retrying'
  | 'downloading'
  | 'transcribing'
  | 'analyzing'
  | 'processing'
  | 'done'
  | 'error'
  | 'cancelled';

export interface Project {
  id: string;
  youtube_url: string;
  title: string;
  status: ProjectStatus;
  created_at: string;
  clip_count?: number;
  source_type?: 'youtube' | 'upload';
  source_file?: string | null;
  error_message?: string | null;
  config?: ClipSettings | null;
}

export interface Clip {
  id: string;
  project_id: string;
  project_title?: string;
  file_path: string;
  start_time: number;
  end_time: number;
  duration: number;
  reframed: boolean;
  captioned: boolean;
  title?: string;
  reason?: string;
  viral_score?: number | null;
  face_count?: number;
  layout_mode?: string;
  caption_style?: string;
  hashtags?: string[];
  tags?: string[];
  thumbnail?: string | null;
  created_at: string;
}

export interface ProgressUpdate {
  stage: string;
  percent: number;
  message: string;
}

export interface Settings {
  llm_provider: 'openai' | 'anthropic' | 'gemini' | 'ollama';
  llm_model: string;
  whisper_model: 'base' | 'small' | 'medium';
  has_api_key: boolean;
  caption_style: string;
  watermark_enabled?: boolean;
  watermark_position?: 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right';
  watermark_opacity?: number;
}

export interface CaptionStyle {
  key: string;
  name: string;
  animation: 'word_by_word' | 'highlight' | 'one_word';
  preview_colors: {
    text: string;
    highlight: string | null;
    background: string | null;
  };
}

export interface ClipSuggestion {
  start: number;
  end: number;
  title: string;
  reason: string;
}

export interface WatermarkSettings {
  enabled: boolean;
  position: 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right';
  opacity: number;
}

export interface ClipSettings {
  num_clips: number;
  min_duration: number;
  max_duration: number;
  aspect_ratio: '9:16';
  captions: string;
  reframe: boolean;
  face_tracking: boolean;
  ai_detection: boolean;
  watermark: WatermarkSettings;
}

export const DEFAULT_CLIP_SETTINGS: ClipSettings = {
  num_clips: 5,
  min_duration: 30,
  max_duration: 90,
  aspect_ratio: '9:16',
  captions: 'none',
  reframe: true,
  face_tracking: true,
  ai_detection: true,
  watermark: { enabled: false, position: 'bottom_right', opacity: 0.6 },
};

export interface Stats {
  videos: number;
  shorts: number;
  processing: number;
  failed: number;
}

export type DiagnosticState = 'ok' | 'warn';

export interface DiagnosticItem {
  key: string;
  label: string;
  state: DiagnosticState;
  message: string;
  required_for_start: boolean;
}

export interface YouTubeStatus {
  configured: boolean;
  connected: boolean;
  channel_name?: string | null;
  channel_id?: string | null;
  live_active: boolean;
  live?: {
    video_id?: string;
    title?: string;
    description?: string;
    published_at?: string;
    actual_start_time?: string;
    concurrent_viewers?: string | number | null;
    url?: string;
  } | null;
  source: {
    ok: boolean;
    stream_url?: string | null;
    message: string;
  };
  limitation?: string | null;
}

export interface StumpsMatch {
  match_id?: string | null;
  team_home?: string | null;
  team_away?: string | null;
  inning?: string | null;
  score?: string | null;
  wickets?: string | null;
  overs?: string | null;
  striker?: string | null;
  non_striker?: string | null;
  bowler?: string | null;
  recent_balls?: string[];
  event?: string | null;
  timestamp?: string | null;
}

export interface StumpsStatus {
  provider: 'stumps';
  team_id: string;
  team_url?: string;
  team_name?: string | null;
  connected: boolean;
  live_data_available: boolean;
  limitation?: string | null;
  match?: StumpsMatch | null;
}

export interface ProviderCheck {
  ok: boolean;
  message: string;
}

export interface AIEngineStatus {
  online: boolean;
  primary?: string | null;
  fallback?: string | null;
  providers: {
    openai: ProviderCheck;
    gemini: ProviderCheck;
  };
  message: string;
}

export interface MomentRecord {
  id: string;
  event_type: string;
  player?: string | null;
  bowler?: string | null;
  over_text?: string | null;
  score_text?: string | null;
  viral_score?: number | null;
  confidence?: number | null;
  timestamp?: string | null;
  clip_path?: string | null;
  captioned_path?: string | null;
  title?: string | null;
  description?: string | null;
  hashtags?: string[];
  status?: string;
}

export interface PublishingPlatformStatus {
  platform: string;
  ready: boolean;
  state: 'ok' | 'warn';
  message: string;
}

export interface PublishingJob {
  id: string;
  moment_id: string;
  platform: string;
  status: string;
  approval_required: boolean;
  metadata: {
    title?: string;
    description?: string;
    hashtags?: string[];
  };
  error_message?: string | null;
  external_id?: string | null;
  title?: string | null;
  clip_path?: string | null;
  captioned_path?: string | null;
  player?: string | null;
  viral_score?: number | null;
  created_at?: string;
  updated_at?: string;
}

export interface CommandCenterState {
  app: {
    name: string;
    subtitle: string;
  };
  config: {
    stumps_team_id: string;
    publish_mode: 'auto' | 'approval' | 'manual';
    auto_publish_minimum: number;
    pre_roll_seconds: number;
    post_roll_seconds: number;
    youtube_privacy_status: 'private' | 'unlisted' | 'public';
  };
  youtube: YouTubeStatus;
  stumps: StumpsStatus;
  ai_engine: AIEngineStatus;
  live_analysis: {
    watching: boolean;
    current_event?: MomentRecord | null;
  };
  moments: MomentRecord[];
  publishing: {
    mode: string;
    jobs: PublishingJob[];
    platforms: Record<string, PublishingPlatformStatus>;
  };
  diagnostics: DiagnosticItem[];
  production: {
    active: boolean;
    can_start: boolean;
    blockers: string[];
  };
  buffer: {
    running: boolean;
    ready: boolean;
    segment_count: number;
    latest_segment_end?: number | null;
    source_url?: string | null;
  };
  refreshed_at: string;
}

export interface AdminSession {
  configured: boolean;
  active: boolean;
  expires_at?: string | null;
}

export interface AdminConfigResponse {
  config: CommandCenterState['config'];
  secrets: Record<string, string>;
  audit_logs: Array<{
    id: number;
    event_type: string;
    actor: string;
    success: number;
    details: string;
    created_at: string;
  }>;
}
