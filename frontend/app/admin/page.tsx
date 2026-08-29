"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { getAdminConfig, getAdminSession, lockAdmin, saveAdminConfig, unlockAdmin } from '@/lib/api';
import { AdminConfigResponse, AdminSession } from '@/lib/types';

const DEFAULT_CONFIG = {
  stumps_team_id: '-OiyGifAxdcSXcSbbE5m',
  publish_mode: 'approval' as const,
  auto_publish_minimum: 85,
  pre_roll_seconds: 10,
  post_roll_seconds: 15,
  youtube_privacy_status: 'private' as const,
};

export default function AdminPage() {
  const [session, setSession] = useState<AdminSession | null>(null);
  const [config, setConfig] = useState<AdminConfigResponse['config']>(DEFAULT_CONFIG);
  const [auditLogs, setAuditLogs] = useState<AdminConfigResponse['audit_logs']>([]);
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const adminSession = await getAdminSession();
      setSession(adminSession);
      if (adminSession.active) {
        const adminConfig = await getAdminConfig();
        setConfig(adminConfig.config);
        setAuditLogs(adminConfig.audit_logs);
        setSecrets(adminConfig.secrets);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load admin state');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const result = await unlockAdmin(code);
      setSession(result);
      setMessage(result.message);
      setCode('');
      const adminConfig = await getAdminConfig();
      setConfig(adminConfig.config);
      setAuditLogs(adminConfig.audit_logs);
      setSecrets(adminConfig.secrets);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unlock failed');
    } finally {
      setSaving(false);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const saved = await saveAdminConfig(config);
      setConfig(saved.config);
      setAuditLogs(saved.audit_logs);
      setSecrets(saved.secrets);
      setMessage('Admin configuration saved.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed');
    } finally {
      setSaving(false);
    }
  };

  const handleLock = async () => {
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      await lockAdmin();
      setSession({ configured: true, active: false, expires_at: null });
      setMessage('Admin session locked.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lock failed');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="mx-auto max-w-5xl px-6 py-10 text-slate-300">Loading admin controls…</div>;
  }

  return (
    <div className="mx-auto max-w-5xl px-6 py-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm font-black uppercase tracking-[0.35em] text-rose-400">🔒 ADMIN / DEVELOPER</p>
          <h1 className="mt-3 text-3xl font-black text-white">Backend Configuration & Audit</h1>
          <p className="mt-2 text-sm text-slate-400">
            Secrets remain masked. This area controls server-side production settings only.
          </p>
        </div>
        <div className="flex gap-3">
          <Link href="/" className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-slate-200 hover:bg-white/10">
            Back to Command Center
          </Link>
          {session?.active && (
            <button
              onClick={handleLock}
              disabled={saving}
              className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-slate-200 hover:bg-white/10 disabled:opacity-50"
            >
              Lock
            </button>
          )}
        </div>
      </div>

      {error && <p className="mb-4 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</p>}
      {message && <p className="mb-4 rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{message}</p>}

      {!session?.configured && (
        <div className="rounded-3xl border border-amber-500/30 bg-amber-500/10 p-6 text-sm text-amber-100">
          ADMIN_UNLOCK_CODE is not configured on the backend yet.
        </div>
      )}

      {session?.configured && !session.active && (
        <form onSubmit={handleUnlock} className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <label className="block text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Unlock Code</label>
          <input
            type="password"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none transition focus:border-rose-500"
            placeholder="Enter backend admin code"
          />
          <button
            type="submit"
            disabled={saving || !code.trim()}
            className="mt-4 rounded-2xl bg-rose-600 px-5 py-3 text-sm font-black text-white hover:bg-rose-500 disabled:opacity-50"
          >
            {saving ? 'Unlocking…' : 'UNLOCK ADMIN MODE'}
          </button>
        </form>
      )}

      {session?.active && (
        <div className="space-y-6">
          <div className="rounded-3xl border border-emerald-500/30 bg-emerald-500/10 p-5 text-emerald-100">
            🔐 ADMIN MODE ACTIVE
            {session.expires_at && <span className="ml-2 text-sm text-emerald-200">Session expires at {session.expires_at}</span>}
          </div>

          <form onSubmit={handleSave} className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
            <h2 className="text-lg font-black text-white">Production Settings</h2>
            <div className="mt-6 grid grid-cols-1 gap-5 md:grid-cols-2">
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">STUMPS Team ID</span>
                <input
                  value={config.stumps_team_id}
                  onChange={(e) => setConfig({ ...config, stumps_team_id: e.target.value })}
                  className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none focus:border-rose-500"
                />
              </label>
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Publishing Mode</span>
                <select
                  value={config.publish_mode}
                  onChange={(e) => setConfig({ ...config, publish_mode: e.target.value as typeof config.publish_mode })}
                  className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none focus:border-rose-500"
                >
                  <option value="approval">Approval</option>
                  <option value="auto">Auto</option>
                  <option value="manual">Manual</option>
                </select>
              </label>
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Auto-Publish Minimum</span>
                <input
                  type="number"
                  min={0}
                  max={100}
                  value={config.auto_publish_minimum}
                  onChange={(e) => setConfig({ ...config, auto_publish_minimum: Number(e.target.value) })}
                  className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none focus:border-rose-500"
                />
              </label>
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">YouTube Privacy</span>
                <select
                  value={config.youtube_privacy_status}
                  onChange={(e) => setConfig({ ...config, youtube_privacy_status: e.target.value as typeof config.youtube_privacy_status })}
                  className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none focus:border-rose-500"
                >
                  <option value="private">Private</option>
                  <option value="unlisted">Unlisted</option>
                  <option value="public">Public</option>
                </select>
              </label>
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Pre-Roll Seconds</span>
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={config.pre_roll_seconds}
                  onChange={(e) => setConfig({ ...config, pre_roll_seconds: Number(e.target.value) })}
                  className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none focus:border-rose-500"
                />
              </label>
              <label className="block">
                <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Post-Roll Seconds</span>
                <input
                  type="number"
                  min={1}
                  max={60}
                  value={config.post_roll_seconds}
                  onChange={(e) => setConfig({ ...config, post_roll_seconds: Number(e.target.value) })}
                  className="mt-3 w-full rounded-2xl border border-white/10 bg-black/20 px-4 py-3 text-white outline-none focus:border-rose-500"
                />
              </label>
            </div>
            <button
              type="submit"
              disabled={saving}
              className="mt-6 rounded-2xl bg-rose-600 px-5 py-3 text-sm font-black text-white hover:bg-rose-500 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'SAVE BACKEND CONFIG'}
            </button>
          </form>

          <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
            <h2 className="text-lg font-black text-white">Masked Secrets</h2>
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
              {Object.entries(secrets).map(([key, value]) => (
                <div key={key} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <p className="text-xs font-bold uppercase tracking-[0.22em] text-slate-500">{key}</p>
                  <p className="mt-2 text-sm text-white">{value}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
            <h2 className="text-lg font-black text-white">Audit Logs</h2>
            <div className="mt-4 space-y-3">
              {auditLogs.length === 0 ? (
                <p className="text-sm text-slate-400">No audit activity recorded yet.</p>
              ) : (
                auditLogs.map((item) => (
                  <div key={item.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                      <div>
                        <p className="text-sm font-bold text-white">{item.event_type}</p>
                        <p className="mt-1 text-xs text-slate-400">{item.details}</p>
                      </div>
                      <div className="text-xs text-slate-400">
                        {item.actor} • {item.created_at} • {item.success ? 'SUCCESS' : 'FAILED'}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
