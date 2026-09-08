"use client";

import { useEffect, useState } from "react";
import {
  Bell,
  Bot,
  Brain,
  Cpu,
  KeyRound,
  Moon,
  Palette,
  Save,
  Settings as SettingsIcon,
  ShieldCheck,
  Sun,
  Wrench,
} from "lucide-react";

import type { AppSettings, User } from "@aitzaz/types";

import { api, ApiError } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input, Label, Switch } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";

const SECTIONS = [
  { id: "general", label: "General", icon: SettingsIcon },
  { id: "ai_provider", label: "AI Provider", icon: Bot },
  { id: "appearance", label: "Appearance", icon: Palette },
  { id: "security", label: "Security", icon: ShieldCheck },
  { id: "notifications", label: "Notifications", icon: Bell },
  { id: "memory", label: "Memory", icon: Brain },
  { id: "tools", label: "Tools", icon: Wrench },
  { id: "permissions", label: "Permissions", icon: KeyRound },
] as const;

type SectionId = (typeof SECTIONS)[number]["id"];

const BASELINE_PERMISSIONS = [
  "chat.use",
  "tasks.create",
  "tasks.manage",
  "memory.write",
  "tools.execute",
  "approvals.request",
  "approvals.decide",
  "settings.write",
];

export default function SettingsPage() {
  const { toast } = useToast();
  const userState = useApiData<User>("/auth/me");
  const settingsState = useApiData<AppSettings>("/settings");
  const [section, setSection] = useState<SectionId>("general");
  const [name, setName] = useState("");
  const [savingName, setSavingName] = useState(false);
  const [patching, setPatching] = useState(false);

  const user = userState.data;
  const settings = settingsState.data?.data ?? {};

  useEffect(() => {
    if (user) setName(user.name);
  }, [user]);

  function applyTheme(theme: "dark" | "light") {
    const root = document.documentElement;
    root.classList.remove("dark", "light");
    root.classList.add(theme === "dark" ? "dark" : "light");
    try {
      localStorage.setItem("aitzaz.theme", theme);
    } catch {
      /* private mode */
    }
  }

  async function patchSection(id: SectionId, values: Record<string, unknown>, successTitle: string) {
    setPatching(true);
    try {
      await api("/settings", { method: "PATCH", body: { section: id, values } });
      settingsState.refresh();
      toast({ title: successTitle, variant: "success" });
    } catch (err) {
      toast({
        title: "Could not save setting",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setPatching(false);
    }
  }

  async function saveName(event: React.FormEvent) {
    event.preventDefault();
    if (!name.trim() || name.trim().length < 2) return;
    setSavingName(true);
    try {
      await api("/auth/me", { method: "PATCH", body: { name: name.trim() } });
      userState.refresh();
      toast({ title: "Profile updated", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not update profile",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setSavingName(false);
    }
  }

  const bool = (sectionKey: SectionId, key: string, fallback = false) =>
    Boolean((settings[sectionKey] as Record<string, unknown> | undefined)?.[key] ?? fallback);

  const str = (sectionKey: SectionId, key: string, fallback = "") =>
    String((settings[sectionKey] as Record<string, unknown> | undefined)?.[key] ?? fallback);

  return (
    <div className="animate-fade-in">
      <PageHeader title="Settings" description="Your account, agent and workspace preferences." />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[220px_1fr]">
        {/* Section nav */}
        <nav className="card-shadow h-fit rounded-2xl border border-line bg-surface/70 p-2">
          {SECTIONS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              onClick={() => setSection(id)}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-sm font-medium transition",
                section === id ? "bg-accent/10 text-accent" : "text-muted hover:bg-surface2 hover:text-ink",
              )}
            >
              <Icon className="h-4 w-4" /> {label}
            </button>
          ))}
        </nav>

        <div className="space-y-5">
          {/* --- General --- */}
          {section === "general" ? (
            <Card>
              <CardHeader>
                <CardTitle>General</CardTitle>
                <CardDescription>Account and profile basics.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                {userState.loading ? (
                  <Skeleton className="h-24 w-full" />
                ) : user ? (
                  <>
                    <form onSubmit={saveName} className="flex items-end gap-2">
                      <div className="flex-1">
                        <Label htmlFor="settings-name">Display name</Label>
                        <Input id="settings-name" value={name} onChange={(event) => setName(event.target.value)} />
                      </div>
                      <Button type="submit" variant="secondary" loading={savingName}>
                        <Save className="h-4 w-4" /> Save
                      </Button>
                    </form>
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div>
                        <Label>Email</Label>
                        <p className="text-sm text-ink">{user.email}</p>
                      </div>
                      <div>
                        <Label>Role</Label>
                        <Badge variant="accent">{user.role}</Badge>
                      </div>
                      <div>
                        <Label>Member since</Label>
                        <p className="text-sm text-ink">{new Date(user.created_at).toLocaleDateString()}</p>
                      </div>
                      <div>
                        <Label>Session</Label>
                        <p className="text-sm text-ink">JWT + httpOnly cookie (revocable)</p>
                      </div>
                    </div>
                  </>
                ) : null}
              </CardContent>
            </Card>
          ) : null}

          {/* --- AI Provider --- */}
          {section === "ai_provider" ? (
            <Card>
              <CardHeader>
                <CardTitle>AI Provider</CardTitle>
                <CardDescription>Which LLM powers the agent.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap items-center gap-3">
                  <Badge variant={bool("ai_provider", "demo_mode", true) ? "warn" : "ok"} dot>
                    {bool("ai_provider", "demo_mode", true) ? "Demo AI (mock provider)" : "Real LLM connected"}
                  </Badge>
                  <span className="font-mono text-xs text-muted">provider: {str("ai_provider", "provider", "mock")}</span>
                </div>
                <p className="text-xs leading-relaxed text-muted">
                  Phase 1 ships the <strong className="text-ink">Demo AI</strong> — a rule-based mock
                  so everything works without API keys. The provider abstraction (LLMProvider) already
                  supports OpenAI and Anthropic; connecting a real key and the full configuration UI
                  arrive in <strong className="text-ink">Phase 2</strong>. Never put API keys in the
                  frontend — they belong in backend environment variables only.
                </p>
                <div className="rounded-xl border border-line bg-surface2/40 p-3 font-mono text-[11px] text-muted">
                  AITZAZ_LLM_PROVIDER=mock · AITZAZ_OPENAI_API_KEY=<em>not set</em> ·
                  AITZAZ_ANTHROPIC_API_KEY=<em>not set</em>
                </div>
                <p className="text-[11px] text-muted">Provider configuration UI — coming in a later phase.</p>
              </CardContent>
            </Card>
          ) : null}

          {/* --- Appearance --- */}
          {section === "appearance" ? (
            <Card>
              <CardHeader>
                <CardTitle>Appearance</CardTitle>
                <CardDescription>Theme — saved to your preferences.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      applyTheme("dark");
                      void patchSection("appearance", { theme: "dark" }, "Theme set to dark");
                    }}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition",
                      str("appearance", "theme", "dark") === "dark"
                        ? "border-accent/50 bg-accent/10 text-accent"
                        : "border-line text-muted hover:text-ink",
                    )}
                  >
                    <Moon className="h-4 w-4" /> Dark
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      applyTheme("light");
                      void patchSection("appearance", { theme: "light" }, "Theme set to light");
                    }}
                    className={cn(
                      "flex items-center gap-2 rounded-xl border px-4 py-3 text-sm transition",
                      str("appearance", "theme") === "light"
                        ? "border-accent/50 bg-accent/10 text-accent"
                        : "border-line text-muted hover:text-ink",
                    )}
                  >
                    <Sun className="h-4 w-4" /> Light
                  </button>
                </div>
                <p className="text-[11px] text-muted">
                  Custom accent colors and density — coming in a later phase.
                </p>
              </CardContent>
            </Card>
          ) : null}

          {/* --- Security --- */}
          {section === "security" ? (
            <Card>
              <CardHeader>
                <CardTitle>Security</CardTitle>
                <CardDescription>Current protections on your account.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <ul className="space-y-2 text-sm text-muted">
                  <li className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-ok" /> Passwords hashed with bcrypt (12 rounds)
                  </li>
                  <li className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-ok" /> JWT sessions in httpOnly cookies, revocable server-side
                  </li>
                  <li className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-ok" /> Rate limiting + strict input validation on every endpoint
                  </li>
                  <li className="flex items-center gap-2">
                    <ShieldCheck className="h-4 w-4 text-ok" /> Full audit trail on the Activity page
                  </li>
                </ul>
                <p className="text-[11px] text-muted">
                  Two-factor authentication, session management UI and password change flow — coming
                  in a later phase (Phase 12).
                </p>
              </CardContent>
            </Card>
          ) : null}

          {/* --- Notifications --- */}
          {section === "notifications" ? (
            <Card>
              <CardHeader>
                <CardTitle>Notifications</CardTitle>
                <CardDescription>What Aitzaz should alert you about.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {[
                  { key: "in_app", label: "In-app notifications", hint: "Badge on the bell icon" },
                  { key: "approval_alerts", label: "Approval alerts", hint: "Ping me when an action needs approval" },
                  { key: "email", label: "Email notifications", hint: "Coming in a later phase" },
                  { key: "desktop", label: "Desktop notifications", hint: "Coming in a later phase" },
                ].map((item) => (
                  <div key={item.key} className="flex items-center justify-between gap-4">
                    <div>
                      <p className="text-sm text-ink">{item.label}</p>
                      <p className="text-[11px] text-muted">{item.hint}</p>
                    </div>
                    <Switch
                      checked={bool("notifications", item.key, item.key === "in_app" || item.key === "approval_alerts")}
                      onCheckedChange={(checked) =>
                        void patchSection("notifications", { [item.key]: checked }, "Notifications updated")
                      }
                      disabled={patching}
                    />
                  </div>
                ))}
              </CardContent>
            </Card>
          ) : null}

          {/* --- Memory --- */}
          {section === "memory" ? (
            <Card>
              <CardHeader>
                <CardTitle>Memory</CardTitle>
                <CardDescription>How much the agent should remember.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-ink">Auto-remember facts from chat</p>
                    <p className="text-[11px] text-muted">“Remember that…” statements are stored as memories</p>
                  </div>
                  <Switch
                    checked={bool("memory", "auto_remember", true)}
                    onCheckedChange={(checked) => void patchSection("memory", { auto_remember: checked }, "Memory settings updated")}
                    disabled={patching}
                  />
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-ink">Surface memories in chat</p>
                    <p className="text-[11px] text-muted">Let the agent use your memories when answering</p>
                  </div>
                  <Switch
                    checked={bool("memory", "memory_in_chat", true)}
                    onCheckedChange={(checked) => void patchSection("memory", { memory_in_chat: checked }, "Memory settings updated")}
                    disabled={patching}
                  />
                </div>
                <p className="rounded-xl border border-line bg-surface2/40 px-3 py-2.5 text-[11px] text-muted">
                  <Cpu className="mr-1.5 inline h-3 w-3" />
                  Semantic/vector memory with RAG — coming in Phase 3. Phase 1 uses structured
                  database retrieval.
                </p>
              </CardContent>
            </Card>
          ) : null}

          {/* --- Tools --- */}
          {section === "tools" ? (
            <Card>
              <CardHeader>
                <CardTitle>Tools</CardTitle>
                <CardDescription>Tool execution policy for the agent.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-ink">Allow safe tools to run automatically</p>
                    <p className="text-[11px] text-muted">Calculator, time, echo — validated and audited</p>
                  </div>
                  <Switch
                    checked={bool("tools", "allow_agent_auto_execute", true)}
                    onCheckedChange={(checked) => void patchSection("tools", { allow_agent_auto_execute: checked }, "Tool policy updated")}
                    disabled={patching}
                  />
                </div>
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm text-ink">Require approval for every tool run</p>
                    <p className="text-[11px] text-muted">Stricter mode — useful when untrusted content is expected</p>
                  </div>
                  <Switch
                    checked={bool("tools", "require_approval_for_tools", false)}
                    onCheckedChange={(checked) => void patchSection("tools", { require_approval_for_tools: checked }, "Tool policy updated")}
                    disabled={patching}
                  />
                </div>
                <p className="text-[11px] text-muted">
                  Per-tool enable/disable toggles — coming in a later phase.
                </p>
              </CardContent>
            </Card>
          ) : null}

          {/* --- Permissions --- */}
          {section === "permissions" ? (
            <Card>
              <CardHeader>
                <CardTitle>Permissions</CardTitle>
                <CardDescription>
                  Role-based authorization foundation for your account (role: {user?.role ?? "…"}).
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-1.5">
                  {BASELINE_PERMISSIONS.map((permission) => (
                    <Badge key={permission} variant="outline" className="font-mono">
                      {permission}
                    </Badge>
                  ))}
                </div>
                <p className="mt-4 text-[11px] text-muted">
                  Fine-grained per-user permission management — coming in a later phase. Sensitive
                  actions are already gated by the Approvals system regardless of permissions.
                </p>
              </CardContent>
            </Card>
          ) : null}
        </div>
      </div>
    </div>
  );
}
