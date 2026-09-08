/**
 * @aitzaz/shared — brand constants, navigation, status metadata and roadmap
 * shared by the frontend (and usable by any future Aitzaz AI client).
 */

export const APP_NAME = "Aitzaz AI";
export const APP_TAGLINE = "Your personal AI agent";

export interface NavItem {
  label: string;
  href: string;
  icon: string;
  phase?: string;
}

export const NAV_ITEMS: NavItem[] = [
  { label: "Overview", href: "/dashboard", icon: "LayoutDashboard" },
  { label: "AI Chat", href: "/chat", icon: "MessageSquare" },
  { label: "Tasks", href: "/tasks", icon: "ListTodo" },
  { label: "Automations", href: "/automations", icon: "Workflow", phase: "9" },
  { label: "Memory", href: "/memory", icon: "Brain" },
  { label: "Tools", href: "/tools", icon: "Wrench" },
  { label: "Files", href: "/files", icon: "FolderOpen", phase: "6" },
  { label: "Research", href: "/research", icon: "Telescope", phase: "4" },
  { label: "Browser", href: "/browser", icon: "Globe", phase: "5" },
  { label: "Agents", href: "/agents", icon: "Bot" },
  { label: "Activity", href: "/activity", icon: "History" },
  { label: "Approvals", href: "/approvals", icon: "ShieldCheck" },
  { label: "Settings", href: "/settings", icon: "Settings" },
];

export const TASK_STATUS_META: Record<
  string,
  { label: string; badge: string; dot: string }
> = {
  pending: {
    label: "Pending",
    badge: "bg-warn/15 text-warn border-warn/30",
    dot: "bg-warn",
  },
  running: {
    label: "Running",
    badge: "bg-accent/15 text-accent border-accent/30",
    dot: "bg-accent",
  },
  waiting_approval: {
    label: "Waiting approval",
    badge: "bg-warn/15 text-warn border-warn/30",
    dot: "bg-warn",
  },
  completed: {
    label: "Completed",
    badge: "bg-ok/15 text-ok border-ok/30",
    dot: "bg-ok",
  },
  failed: {
    label: "Failed",
    badge: "bg-danger/15 text-danger border-danger/30",
    dot: "bg-danger",
  },
  cancelled: {
    label: "Cancelled",
    badge: "bg-muted/10 text-muted border-line",
    dot: "bg-muted",
  },
};

export const PRIORITY_META: Record<string, { label: string; badge: string }> = {
  low: { label: "Low", badge: "bg-muted/10 text-muted border-line" },
  medium: { label: "Medium", badge: "bg-accent/10 text-accent border-accent/25" },
  high: { label: "High", badge: "bg-warn/15 text-warn border-warn/30" },
  urgent: { label: "Urgent", badge: "bg-danger/15 text-danger border-danger/30" },
};

export const APPROVAL_STATUS_META: Record<string, { label: string; badge: string }> = {
  pending: { label: "Pending", badge: "bg-warn/15 text-warn border-warn/30" },
  approved: { label: "Approved", badge: "bg-ok/15 text-ok border-ok/30" },
  rejected: { label: "Rejected", badge: "bg-danger/15 text-danger border-danger/30" },
  expired: { label: "Expired", badge: "bg-muted/10 text-muted border-line" },
};

export const MEMORY_CATEGORY_META: Record<string, { label: string; badge: string; icon: string }> = {
  preference: { label: "Preference", badge: "bg-accent/15 text-accent border-accent/30", icon: "Sparkles" },
  fact: { label: "Fact", badge: "bg-ok/15 text-ok border-ok/30", icon: "Info" },
  conversation: { label: "Conversation", badge: "bg-warn/15 text-warn border-warn/30", icon: "MessageSquare" },
  task: { label: "Task", badge: "bg-muted/15 text-ink border-line", icon: "ListTodo" },
  system: { label: "System", badge: "bg-muted/10 text-muted border-line", icon: "Cpu" },
};

export const ACTIVITY_TYPE_META: Record<string, { label: string; badge: string }> = {
  user_registered: { label: "Registered", badge: "bg-accent/15 text-accent border-accent/30" },
  login: { label: "Login", badge: "bg-ok/15 text-ok border-ok/30" },
  logout: { label: "Logout", badge: "bg-muted/10 text-muted border-line" },
  ai_message: { label: "AI message", badge: "bg-accent/15 text-accent border-accent/30" },
  task_created: { label: "Task created", badge: "bg-ok/15 text-ok border-ok/30" },
  task_updated: { label: "Task updated", badge: "bg-warn/15 text-warn border-warn/30" },
  task_deleted: { label: "Task deleted", badge: "bg-danger/15 text-danger border-danger/30" },
  tool_executed: { label: "Tool executed", badge: "bg-accent/15 text-accent border-accent/30" },
  approval_requested: { label: "Approval requested", badge: "bg-warn/15 text-warn border-warn/30" },
  approval_approved: { label: "Approved", badge: "bg-ok/15 text-ok border-ok/30" },
  approval_rejected: { label: "Rejected", badge: "bg-danger/15 text-danger border-danger/30" },
  memory_created: { label: "Memory created", badge: "bg-ok/15 text-ok border-ok/30" },
  memory_updated: { label: "Memory updated", badge: "bg-warn/15 text-warn border-warn/30" },
  memory_deleted: { label: "Memory deleted", badge: "bg-danger/15 text-danger border-danger/30" },
  settings_updated: { label: "Settings", badge: "bg-muted/10 text-muted border-line" },
  profile_updated: { label: "Profile", badge: "bg-muted/10 text-muted border-line" },
  conversation_created: { label: "New conversation", badge: "bg-accent/15 text-accent border-accent/30" },
  conversation_deleted: { label: "Conversation cleared", badge: "bg-muted/10 text-muted border-line" },
  error: { label: "Error", badge: "bg-danger/15 text-danger border-danger/30" },
};

export const ROADMAP: { phase: string; title: string; description: string }[] = [
  { phase: "Phase 2", title: "Real LLM providers", description: "OpenAI / Anthropic / Google integration with advanced agent configuration." },
  { phase: "Phase 3", title: "Long-term semantic memory", description: "Vector memory + RAG so the agent recalls what matters." },
  { phase: "Phase 4", title: "Web research agent", description: "Search the web, collect sources, build research reports." },
  { phase: "Phase 5", title: "Browser automation agent", description: "Operate websites on your behalf, with approval gates." },
  { phase: "Phase 6", title: "File & document intelligence", description: "Read, organize and summarize your documents." },
  { phase: "Phase 7", title: "Voice assistant", description: "Talk with Aitzaz AI in real time." },
  { phase: "Phase 8", title: "Email & calendar", description: "Explicitly connected, always approval-gated." },
  { phase: "Phase 9", title: "Automation & scheduling", description: "Scheduled tasks and multi-step automations." },
  { phase: "Phase 10", title: "Specialist sub-agents", description: "Research, browser, coding, finance agents working under the coordinator." },
  { phase: "Phase 11", title: "Mobile / PWA", description: "Aitzaz AI in your pocket." },
  { phase: "Phase 12", title: "Production hardening", description: "MFA, deployments, monitoring, advanced security." },
];

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function timeAgo(iso: string | null | undefined): string {
  if (!iso) return "—";
  const seconds = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return formatDateTime(iso);
}
