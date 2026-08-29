"use client";

import Link from 'next/link';
import { useEffect, useState } from 'react';
import {
  approvePublishingJob,
  disconnectYouTube,
  getAdminSession,
  startProductionMode,
  startYouTubeAuth,
  stopProductionMode,
} from '@/lib/api';
import { useCommandCenterState } from '@/lib/command-center';
import { CommandCenterState, DiagnosticItem, PublishingJob } from '@/lib/types';

function Dot({ ok }: { ok: boolean }) {
  return <span className={`inline-block h-2.5 w-2.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-slate-500'}`} />;
}

function statusText(ok: boolean, yes = 'CONNECTED', no = 'OFFLINE') {
  return ok ? `🟢 ${yes}` : `⚪ ${no}`;
}

function diagColor(state: DiagnosticItem['state']) {
  return state === 'ok'
    ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
    : 'border-amber-500/30 bg-amber-500/10 text-amber-200';
}

function platformBadge(job: PublishingJob) {
  if (job.status === 'published') return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
  if (job.status === 'failed') return 'bg-red-500/15 text-red-300 border-red-500/30';
  if (job.status === 'approval_required') return 'bg-amber-500/15 text-amber-200 border-amber-500/30';
  if (job.status === 'blocked') return 'bg-slate-500/15 text-slate-300 border-slate-500/30';
  return 'bg-blue-500/15 text-blue-200 border-blue-500/30';
}

function MatchBlock({ state }: { state: CommandCenterState }) {
  const match = state.stumps.match;
  return (
    <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6 shadow-2xl shadow-black/20">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">STUMPS</p>
          <p className="mt-2 text-sm font-semibold text-white">{state.stumps.team_name || 'Configured Team'}</p>
        </div>
        <span className="text-sm font-semibold text-white">{state.stumps.connected ? '🟢 CONNECTED' : '⚪ NOT CONNECTED'}</span>
      </div>

      {match ? (
        <div className="space-y-4">
          <InfoRow label="MATCH" value={[match.team_home, match.team_away].filter(Boolean).join(' vs ') || 'Active match'} />
          <InfoRow label="SCORE" value={match.score && match.wickets ? `${match.score}/${match.wickets}` : 'Unavailable'} />
          <InfoRow label="OVERS" value={match.overs || 'Unavailable'} />
          <InfoRow label="STRIKER" value={match.striker || 'Unavailable'} />
          <InfoRow label="NON-STRIKER" value={match.non_striker || 'Unavailable'} />
          <InfoRow label="BOWLER" value={match.bowler || 'Unavailable'} />
          <InfoRow label="RECENT BALLS" value={match.recent_balls?.join(' · ') || 'Unavailable'} />
          <InfoRow label="EVENT" value={match.event || 'Waiting'} />
        </div>
      ) : (
        <p className="text-sm leading-6 text-slate-400">
          {state.stumps.limitation || 'No active STUMPS match is currently available.'}
        </p>
      )}
    </section>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-white/5 pb-3 last:border-b-0 last:pb-0">
      <span className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">{label}</span>
      <span className="text-right text-sm font-medium text-white">{value}</span>
    </div>
  );
}

export default function Dashboard() {
  const { state, setState, loading, error } = useCommandCenterState();
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [adminActive, setAdminActive] = useState(false);

  useEffect(() => {
    getAdminSession().then((session) => setAdminActive(session.active)).catch(() => undefined);
  }, []);

  if (loading || !state) {
    return (
      <div className="mx-auto flex min-h-[70vh] max-w-7xl items-center justify-center px-6 text-slate-300">
        Loading AITZAZ AI command center…
      </div>
    );
  }

  const currentEvent = state.live_analysis.current_event;
  const approvalJobs = state.publishing.jobs.filter((job) => job.status === 'approval_required');

  const runAction = async (key: string, fn: () => Promise<CommandCenterState | void>) => {
    setBusy(key);
    setActionError(null);
    try {
      const next = await fn();
      if (next && typeof next === 'object' && 'app' in next) {
        setState(next);
      }
      const session = await getAdminSession();
      setAdminActive(session.active);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-8 lg:px-14">
      <section className="rounded-[32px] border border-white/10 bg-gradient-to-br from-[#111625] via-[#0b0f18] to-[#080b11] p-8 shadow-[0_20px_80px_rgba(0,0,0,0.35)]">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.4em] text-rose-400">AITZAZ AI</p>
            <h1 className="mt-3 text-4xl font-black tracking-tight text-white lg:text-5xl">LIVE CONTENT COMMAND CENTER</h1>
            <p className="mt-4 max-w-3xl text-sm leading-7 text-slate-400">
              Connect YouTube, verify the real STUMPS match feed, monitor live cricket context,
              and let the backend-only AI pipeline create, caption, score, and queue clips.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:min-w-[430px]">
            {[
              { label: 'YouTube', value: state.youtube.connected ? 'Connected' : 'Waiting' },
              { label: 'Live', value: state.youtube.live_active ? 'Active' : 'Offline' },
              { label: 'STUMPS', value: state.stumps.match ? 'Live Data' : 'Waiting' },
              { label: 'AI', value: state.ai_engine.online ? 'Online' : 'Offline' },
            ].map((item) => (
              <div key={item.label} className="rounded-2xl border border-white/10 bg-black/20 px-4 py-4 text-center">
                <p className="text-2xl font-black text-white">{item.value}</p>
                <p className="mt-2 text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">{item.label}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 flex flex-wrap gap-3">
          <button
            onClick={() => runAction('youtube-connect', async () => {
              const { auth_url } = await startYouTubeAuth();
              window.location.href = auth_url;
            })}
            disabled={busy === 'youtube-connect' || !state.youtube.configured}
            className="rounded-2xl bg-rose-600 px-5 py-3 text-sm font-bold text-white transition hover:bg-rose-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === 'youtube-connect' ? 'Opening OAuth…' : 'CONNECT YOUTUBE'}
          </button>
          <button
            onClick={() => runAction('youtube-disconnect', () => disconnectYouTube())}
            disabled={busy === 'youtube-disconnect' || !state.youtube.connected}
            className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-bold text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {busy === 'youtube-disconnect' ? 'Disconnecting…' : 'DISCONNECT'}
          </button>
          <Link href="/admin" className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-bold text-slate-200 transition hover:bg-white/10">
            🔒 ADMIN / DEVELOPER
          </Link>
          <Link href="/library" className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-bold text-slate-200 transition hover:bg-white/10">
            CLIP LIBRARY
          </Link>
        </div>

        {error && <p className="mt-5 text-sm text-amber-300">{error}</p>}
        {actionError && <p className="mt-2 text-sm text-red-300">{actionError}</p>}
        {!state.youtube.configured && (
          <p className="mt-4 text-sm text-amber-300">
            Google OAuth is not configured on the backend. Add GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET,
            YOUTUBE_OAUTH_REDIRECT_URI, and APP_BASE_URL before testing YouTube connection.
          </p>
        )}
      </section>

      <div className="mt-8 grid grid-cols-1 gap-6 xl:grid-cols-[1.2fr_1fr]">
        <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">YOUTUBE</p>
              <p className="mt-2 text-sm font-semibold text-white">
                {state.youtube.channel_name ? `Channel: ${state.youtube.channel_name}` : 'Channel not connected'}
              </p>
            </div>
            <span className="text-sm font-semibold text-white">
              {statusText(state.youtube.connected, 'CONNECTED', 'NOT CONNECTED')}
            </span>
          </div>

          <div className="space-y-4">
            <InfoRow label="LIVE" value={statusText(state.youtube.live_active, 'ACTIVE', 'OFFLINE')} />
            <InfoRow label="SOURCE" value={state.youtube.source.ok ? '🟢 VERIFIED' : '⚪ UNAVAILABLE'} />
            <InfoRow label="TITLE" value={state.youtube.live?.title || 'No active live broadcast'} />
            <InfoRow label="VIEWERS" value={String(state.youtube.live?.concurrent_viewers || '--')} />
            <InfoRow label="LIVE URL" value={state.youtube.live?.url || 'Unavailable'} />
          </div>
        </section>

        <MatchBlock state={state} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">AI ENGINE</p>
          <div className="mt-4 flex items-center gap-3 text-white">
            <Dot ok={state.ai_engine.online} />
            <span className="text-lg font-bold">{state.ai_engine.online ? 'ONLINE' : 'AI BACKEND NOT CONFIGURED'}</span>
          </div>
          <div className="mt-5 space-y-3 text-sm text-slate-300">
            <InfoRow label="PRIMARY" value={state.ai_engine.primary || 'Unavailable'} />
            <InfoRow label="FALLBACK" value={state.ai_engine.fallback || 'Unavailable'} />
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">LIVE ANALYSIS</p>
          <div className="mt-4 flex items-center gap-3 text-white">
            <Dot ok={state.live_analysis.watching} />
            <span className="text-lg font-bold">{state.live_analysis.watching ? 'WATCHING' : 'WAITING'}</span>
          </div>
          <div className="mt-5 space-y-4 text-sm text-slate-300">
            <InfoRow label="CURRENT EVENT" value={currentEvent?.event_type || 'WAITING'} />
            <InfoRow label="VIRAL SCORE" value={currentEvent?.viral_score != null ? `${currentEvent.viral_score}/100` : '--/100'} />
            <InfoRow label="BUFFER" value={state.buffer.ready ? `${state.buffer.segment_count} segments ready` : 'Not ready'} />
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">PUBLISHING</p>
          <div className="mt-4 space-y-4 text-sm text-slate-300">
            <InfoRow label="MODE" value={state.publishing.mode.toUpperCase()} />
            <InfoRow label="YouTube" value={state.publishing.platforms.youtube?.ready ? '🟢 READY' : `⚪ ${state.publishing.platforms.youtube?.message || 'Unavailable'}`} />
            <InfoRow label="Facebook" value={state.publishing.platforms.facebook?.ready ? '🟢 READY' : `⚪ ${state.publishing.platforms.facebook?.message || 'Unavailable'}`} />
            <InfoRow label="TikTok" value="🟡 APPROVAL REQUIRED" />
          </div>
        </section>
      </div>

      <div className="mt-6 rounded-3xl border border-white/10 bg-[#0d1017] p-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">PRODUCTION MODE</p>
            <p className="mt-2 text-sm text-slate-400">
              Start remains disabled until YouTube Live, STUMPS, AI, Media Pipeline, Rolling Buffer,
              Clip Worker, and Publishing Queue are verified by the backend.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button
              onClick={() => runAction('start-production', () => startProductionMode())}
              disabled={busy === 'start-production' || !state.production.can_start || !adminActive || state.production.active}
              className="rounded-2xl bg-emerald-600 px-6 py-3 text-sm font-black text-white transition hover:bg-emerald-500 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {state.production.active ? 'PRODUCTION ACTIVE' : 'START PRODUCTION MODE'}
            </button>
            <button
              onClick={() => runAction('stop-production', () => stopProductionMode())}
              disabled={busy === 'stop-production' || !adminActive || !state.production.active}
              className="rounded-2xl border border-white/10 bg-white/5 px-6 py-3 text-sm font-black text-slate-200 transition hover:bg-white/10 disabled:cursor-not-allowed disabled:opacity-50"
            >
              STOP
            </button>
          </div>
        </div>
        {!adminActive && (
          <p className="mt-4 text-sm text-amber-300">Admin unlock is required before production mode can be started or stopped.</p>
        )}
        {!state.production.can_start && (
          <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-amber-200">
            {state.production.blockers.map((blocker) => (
              <li key={blocker}>{blocker}</li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-[1fr_1fr]">
        <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <div className="mb-5 flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">RECENT MOMENTS</p>
            <span className="text-xs text-slate-500">Realtime backend state</span>
          </div>
          <div className="space-y-3">
            {state.moments.length === 0 ? (
              <p className="text-sm text-slate-400">No verified live moments have been detected yet.</p>
            ) : (
              state.moments.slice(0, 6).map((moment) => (
                <div key={moment.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm font-black text-white">{moment.title || moment.event_type}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {[moment.player, moment.bowler && `vs ${moment.bowler}`, moment.score_text, moment.over_text && `Over ${moment.over_text}`]
                          .filter(Boolean)
                          .join(' • ') || 'Verified match context only'}
                      </p>
                    </div>
                    <div className="rounded-full border border-rose-500/30 bg-rose-500/10 px-3 py-1 text-xs font-black text-rose-200">
                      {moment.viral_score != null ? `${moment.viral_score}` : '--'}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="rounded-3xl border border-white/10 bg-[#0d1017] p-6">
          <div className="mb-5 flex items-center justify-between">
            <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">PUBLISHING QUEUE</p>
            <span className="text-xs text-slate-500">Approval mode default</span>
          </div>
          <div className="space-y-3">
            {state.publishing.jobs.length === 0 ? (
              <p className="text-sm text-slate-400">No publishing jobs have been queued yet.</p>
            ) : (
              state.publishing.jobs.slice(0, 10).map((job) => (
                <div key={job.id} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                    <div>
                      <p className="text-sm font-bold text-white">{job.platform.toUpperCase()} — {job.metadata.title || job.title || job.platform}</p>
                      <p className="mt-1 text-xs text-slate-400">
                        {job.player ? `${job.player} • ` : ''}
                        {job.viral_score != null ? `Viral ${job.viral_score}/100` : 'Awaiting score'}
                        {job.error_message ? ` • ${job.error_message}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.2em] ${platformBadge(job)}`}>
                        {job.status.replace('_', ' ')}
                      </span>
                      {job.status === 'approval_required' && adminActive && (
                        <button
                          onClick={() => runAction(`approve-${job.id}`, () => approvePublishingJob(job.id))}
                          disabled={busy === `approve-${job.id}`}
                          className="rounded-xl bg-white/10 px-3 py-2 text-xs font-bold text-white hover:bg-white/20"
                        >
                          APPROVE
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
          {approvalJobs.length > 0 && !adminActive && (
            <p className="mt-4 text-sm text-amber-300">Unlock admin mode to approve queued publishing jobs.</p>
          )}
        </section>
      </div>

      <section className="mt-6 rounded-3xl border border-white/10 bg-[#0d1017] p-6">
        <div className="mb-5 flex items-center justify-between">
          <p className="text-xs font-bold uppercase tracking-[0.28em] text-slate-500">REAL DIAGNOSTICS</p>
          <span className="text-xs text-slate-500">Refreshed {state.refreshed_at}</span>
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {state.diagnostics.map((item) => (
            <div key={item.key} className={`rounded-2xl border p-4 ${diagColor(item.state)}`}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-black text-white">{item.label}</p>
                  <p className="mt-1 text-xs leading-5 text-inherit">{item.message}</p>
                </div>
                {item.required_for_start && (
                  <span className="rounded-full border border-current/20 px-2 py-1 text-[10px] font-black uppercase tracking-[0.18em]">Required</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
