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
    id: string
    project_id: string
    project_title?: string
    file_path: string
    start_time: number
    end_time: number
    duration: number
    reframed: boolean
    captioned: boolean
    title?: string
    reason?: string
    viral_score?: number | null
    face_count?: number
    layout_mode?: string
    caption_style?: string
    hashtags?: string[]
    tags?: string[]
    thumbnail?: string | null
    created_at: string
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
    // DKC 57 watermark defaults
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

// ---------------------------------------------------------------------------
// DKC 57 clip settings
// ---------------------------------------------------------------------------

export interface WatermarkSettings {
    enabled: boolean;
    position: 'top_left' | 'top_right' | 'bottom_left' | 'bottom_right';
    opacity: number; // 0.05 – 1.0
}

export interface ClipSettings {
    num_clips: number;          // 1 – 20
    min_duration: number;       // seconds
    max_duration: number;       // seconds
    aspect_ratio: '9:16';
    captions: string;           // "none" or a caption style key
    reframe: boolean;           // auto 9:16 reframe
    face_tracking: boolean;     // MediaPipe face tracking
    ai_detection: boolean;      // LLM moment detection
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
