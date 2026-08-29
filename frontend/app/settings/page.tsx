"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCaptionStyles, getSettings, saveSettings } from "@/lib/api";
import { CaptionStyle, Settings } from "@/lib/types";

const WHISPER_OPTIONS = [
  { value: "base", label: "Base (Fast)", desc: "Lowest latency" },
  { value: "small", label: "Small (Balanced)", desc: "Balanced quality" },
  { value: "medium", label: "Medium (Accurate)", desc: "Highest precision" },
] as const;

export default function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [whisperModel, setWhisperModel] = useState<Settings['whisper_model']>('base');
  const [captionStyle, setCaptionStyle] = useState('none');
  const [captionStylesList, setCaptionStylesList] = useState<CaptionStyle[]>([]);
  const [wmEnabled, setWmEnabled] = useState(false);
  const [wmPosition, setWmPosition] = useState<'top_left' | 'top_right' | 'bottom_left' | 'bottom_right'>('bottom_right');
  const [wmOpacity, setWmOpacity] = useState(0.6);

  useEffect(() => {
    Promise.all([getSettings(), getCaptionStyles()])
      .then(([data, styles]) => {
        setWhisperModel(data.whisper_model);
        setCaptionStyle(data.caption_style || 'none');
        setWmEnabled(Boolean(data.watermark_enabled));
        setWmPosition(data.watermark_position || 'bottom_right');
        setWmOpacity(typeof data.watermark_opacity === 'number' ? data.watermark_opacity : 0.6);
        setCaptionStylesList(styles);
      })
      .catch(() => setError('Failed to load settings.'))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await saveSettings({
        whisper_model: whisperModel,
        caption_style: captionStyle,
        watermark_enabled: wmEnabled,
        watermark_position: wmPosition,
        watermark_opacity: wmOpacity,
      });
      setMessage('Legacy clip-processing settings saved.');
    } catch {
      setError('Failed to save settings.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-4xl px-6 py-10">
      <div className="mb-8 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.35em] text-rose-400">SETTINGS</p>
          <h1 className="mt-3 text-3xl font-black text-white">Legacy Clip Processing Defaults</h1>
          <p className="mt-2 text-sm text-slate-400">
            OpenAI, Gemini, YouTube OAuth, and admin secrets are backend-only and managed from the admin area.
          </p>
        </div>
        <Link href="/admin" className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-slate-200 hover:bg-white/10">
          Open Admin
        </Link>
      </div>

      {loading ? (
        <p className="text-slate-300">Loading settings…</p>
      ) : (
        <form onSubmit={handleSave} className="space-y-6 rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          {error && <p className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}
          {message && <p className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{message}</p>}

          <section>
            <h2 className="text-lg font-black text-white">Whisper Model</h2>
            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-3">
              {WHISPER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setWhisperModel(opt.value)}
                  className={`rounded-2xl border p-4 text-left ${whisperModel === opt.value ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-white/10 bg-black/20'}`}
                >
                  <p className="text-sm font-bold text-white">{opt.label}</p>
                  <p className="mt-1 text-xs text-slate-400">{opt.desc}</p>
                </button>
              ))}
            </div>
          </section>

          <section>
            <h2 className="text-lg font-black text-white">Caption Style</h2>
            <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
              {captionStylesList.map((style) => (
                <button
                  key={style.key}
                  type="button"
                  onClick={() => setCaptionStyle(style.key)}
                  className={`rounded-2xl border p-4 ${captionStyle === style.key ? 'border-emerald-500/40 bg-emerald-500/10' : 'border-white/10 bg-black/20'}`}
                >
                  <p className="text-sm font-bold text-white">{style.name}</p>
                  <p className="mt-1 text-xs text-slate-400">{style.animation}</p>
                </button>
              ))}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-black text-white">Watermark Default</h2>
              <button
                type="button"
                onClick={() => setWmEnabled((value) => !value)}
                className={`relative h-7 w-12 rounded-full ${wmEnabled ? 'bg-rose-500' : 'bg-slate-700'}`}
              >
                <span className={`absolute top-1 h-5 w-5 rounded-full bg-white transition-all ${wmEnabled ? 'left-6' : 'left-1'}`} />
              </button>
            </div>
            {wmEnabled && (
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <label>
                  <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Position</span>
                  <select
                    value={wmPosition}
                    onChange={(e) => setWmPosition(e.target.value as typeof wmPosition)}
                    className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white"
                  >
                    <option value="top_left">Top Left</option>
                    <option value="top_right">Top Right</option>
                    <option value="bottom_left">Bottom Left</option>
                    <option value="bottom_right">Bottom Right</option>
                  </select>
                </label>
                <label>
                  <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Opacity</span>
                  <input
                    type="range"
                    min={0.1}
                    max={1}
                    step={0.05}
                    value={wmOpacity}
                    onChange={(e) => setWmOpacity(parseFloat(e.target.value))}
                    className="mt-5 w-full accent-rose-500"
                  />
                </label>
              </div>
            )}
          </section>

          <button
            type="submit"
            disabled={saving}
            className="rounded-2xl bg-rose-600 px-5 py-3 text-sm font-black text-white hover:bg-rose-500 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'SAVE SETTINGS'}
          </button>
        </form>
      )}
    </div>
  );
}
