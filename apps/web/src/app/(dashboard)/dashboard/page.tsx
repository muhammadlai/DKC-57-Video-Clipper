"use client";

import { useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  History,
  ListTodo,
  Send,
  ShieldCheck,
  Sparkles,
  Wrench,
} from "lucide-react";

import type { ChatResponse, DashboardStats } from "@aitzaz/types";
import { ACTIVITY_TYPE_META, TASK_STATUS_META, timeAgo } from "@aitzaz/shared";

import { api, ApiError } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton, Spinner } from "@/components/ui/badge";
import { ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";

const QUICK_PROMPTS = [
  "Hello Aitzaz",
  "Calculate 125 × 48",
  "What time is it?",
  "Remind me to stretch every hour",
];

function StatCard({
  icon,
  label,
  value,
  hint,
  href,
  tone = "accent",
}: {
  icon: React.ReactNode;
  label: string;
  value: React.ReactNode;
  hint?: string;
  href: string;
  tone?: "accent" | "ok" | "warn" | "muted";
}) {
  const tones = {
    accent: "text-accent bg-accent/10",
    ok: "text-ok bg-ok/10",
    warn: "text-warn bg-warn/10",
    muted: "text-muted bg-surface2",
  } as const;
  return (
    <Link href={href}>
      <Card className="group h-full transition hover:border-line hover:bg-surface">
        <CardContent className="flex items-start justify-between gap-3 pt-5">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
            <p className="mt-2 text-3xl font-semibold tracking-tight text-ink">{value}</p>
            {hint ? <p className="mt-1 text-[11px] text-muted">{hint}</p> : null}
          </div>
          <span className={`flex h-10 w-10 items-center justify-center rounded-xl ${tones[tone]}`}>
            {icon}
          </span>
        </CardContent>
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: stats, error, loading, refresh } = useApiData<DashboardStats>("/stats");
  const { toast } = useToast();
  const [command, setCommand] = useState("");
  const [sending, setSending] = useState(false);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);

  async function runCommand(message: string) {
    const text = message.trim();
    if (!text || sending) return;
    setSending(true);
    setLastResponse(null);
    try {
      const response = await api<ChatResponse>("/chat", { method: "POST", body: { message: text } });
      setLastResponse(response);
      setCommand("");
      refresh();
    } catch (err) {
      toast({
        title: "The agent could not process that",
        description: err instanceof ApiError ? err.message : "Please try again.",
        variant: "error",
      });
    } finally {
      setSending(false);
    }
  }

  if (error) {
    return (
      <div className="py-10">
        <ErrorState message={error} onRetry={refresh} />
      </div>
    );
  }

  const activeTasks = stats ? stats.tasks.pending + stats.tasks.running + stats.tasks.waiting_approval : 0;

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="AI Command Center"
        description="Tell Aitzaz what you need — it routes your request to the right tools, tasks and approvals."
        actions={
          stats ? (
            <Badge variant={stats.demo_mode ? "warn" : "ok"} dot>
              {stats.demo_mode ? "Demo AI — mock provider" : "LLM connected"}
            </Badge>
          ) : null
        }
      />

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {loading || !stats ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28 w-full" />)
        ) : (
          <>
            <StatCard
              icon={<ListTodo className="h-5 w-5" />}
              label="Active Tasks"
              value={activeTasks}
              hint={`${stats.tasks.total} total · ${stats.tasks.completed} completed`}
              href="/tasks"
              tone="accent"
            />
            <StatCard
              icon={<CheckCircle2 className="h-5 w-5" />}
              label="Completed Tasks"
              value={stats.tasks.completed}
              hint={`${stats.tasks.failed} failed · ${stats.tasks.cancelled} cancelled`}
              href="/tasks"
              tone="ok"
            />
            <StatCard
              icon={<ShieldCheck className="h-5 w-5" />}
              label="Pending Approvals"
              value={stats.pending_approvals}
              hint="Sensitive actions waiting for you"
              href="/approvals"
              tone={stats.pending_approvals > 0 ? "warn" : "muted"}
            />
            <StatCard
              icon={<Wrench className="h-5 w-5" />}
              label="Connected Tools"
              value={stats.tools_connected}
              hint="Safe Phase 1 demo tools"
              href="/tools"
              tone="muted"
            />
          </>
        )}
      </div>

      {/* Command center + agent status */}
      <div className="mt-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-accent" /> Tell Aitzaz what you need…
            </CardTitle>
            <CardDescription>
              Phase 1 Demo AI understands math, time, tasks, memory and approvals. Real LLM arrives
              in Phase 2.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={(event) => {
                event.preventDefault();
                void runCommand(command);
              }}
              className="flex gap-2"
            >
              <input
                value={command}
                onChange={(event) => setCommand(event.target.value)}
                placeholder="e.g. Calculate 300 × 12, or Remind me to call the bank tomorrow"
                className="h-12 flex-1 rounded-xl border border-line bg-surface2/50 px-4 text-sm text-ink placeholder:text-muted/60 focus:outline-none focus:ring-2 focus:ring-accent/50"
                aria-label="Ask Aitzaz AI"
              />
              <Button type="submit" size="lg" loading={sending} disabled={!command.trim()}>
                <Send className="h-4 w-4" aria-hidden />
                <span className="hidden sm:inline">Send</span>
              </Button>
            </form>

            <div className="mt-3 flex flex-wrap gap-2">
              {QUICK_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void runCommand(prompt)}
                  disabled={sending}
                  className="rounded-full border border-line bg-surface2/40 px-3 py-1.5 text-xs text-muted transition hover:border-accent/40 hover:text-ink disabled:opacity-50"
                >
                  {prompt}
                </button>
              ))}
            </div>

            {sending ? (
              <div className="mt-5 flex items-center gap-3 rounded-xl border border-line bg-surface2/30 px-4 py-3">
                <Spinner className="h-4 w-4" />
                <p className="text-xs text-muted">Aitzaz is thinking (Demo AI)…</p>
              </div>
            ) : null}

            {lastResponse ? (
              <div className="mt-5 animate-fade-in rounded-xl border border-accent/25 bg-accent/5 p-4">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-xs font-medium text-accent">Aitzaz AI (Demo)</p>
                  <Link
                    href={`/chat?conversation=${lastResponse.conversation_id}`}
                    className="flex items-center gap-1 text-xs text-muted hover:text-accent"
                  >
                    Continue in Chat <ArrowRight className="h-3 w-3" />
                  </Link>
                </div>
                <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-ink chat-content">
                  {lastResponse.assistant_message.content}
                </p>
                {lastResponse.tool_calls.length > 0 ? (
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {lastResponse.tool_calls.map((call, index) => (
                      <Badge key={index} variant={call.ok ? "ok" : "danger"}>
                        {call.slug} {call.ok ? "✓" : "✗"}
                      </Badge>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-accent" /> Agent Status
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {loading || !stats ? (
                <Skeleton className="h-20 w-full" />
              ) : (
                <>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">Personal Assistant</span>
                    <Badge variant={stats.agent_status === "active" ? "ok" : "warn"} dot>
                      {stats.agent_status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">Conversations</span>
                    <span className="text-ink">{stats.conversations_count}</span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted">Memories</span>
                    <span className="text-ink">{stats.memories_count}</span>
                  </div>
                  <Link
                    href="/agents"
                    className="flex items-center gap-1 pt-1 text-xs text-accent hover:underline"
                  >
                    View agent details <ArrowRight className="h-3 w-3" />
                  </Link>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex-row items-center justify-between">
              <CardTitle className="flex items-center gap-2">
                <History className="h-4 w-4 text-muted" /> Recent Activity
              </CardTitle>
              <Link href="/activity" className="text-xs text-accent hover:underline">
                View all
              </Link>
            </CardHeader>
            <CardContent>
              {loading || !stats ? (
                <div className="space-y-2">
                  {Array.from({ length: 4 }).map((_, index) => (
                    <Skeleton key={index} className="h-10 w-full" />
                  ))}
                </div>
              ) : stats.recent_activity.length === 0 ? (
                <p className="py-4 text-center text-xs text-muted">
                  No activity yet — send your first message above.
                </p>
              ) : (
                <ul className="space-y-1">
                  {stats.recent_activity.slice(0, 6).map((entry) => {
                    const meta = ACTIVITY_TYPE_META[entry.activity_type];
                    return (
                      <li key={entry.id} className="flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-surface2/50">
                        <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${TASK_STATUS_META[entry.activity_type]?.dot ?? "bg-accent"}`} />
                        <span className="min-w-0 flex-1 truncate text-xs text-ink">{entry.message}</span>
                        <span className="shrink-0 text-[10px] text-muted">{timeAgo(entry.created_at)}</span>
                        {meta ? <Badge variant="outline" className="hidden sm:inline-flex">{meta.label}</Badge> : null}
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
