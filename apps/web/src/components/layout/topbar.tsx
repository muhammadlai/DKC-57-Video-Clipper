"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Bell, ChevronDown, LogOut, Menu, Search, Settings as SettingsIcon } from "lucide-react";

import type { ApiErrorEnvelope, User } from "@aitzaz/types";
import { timeAgo } from "@aitzaz/shared";

import { api, ApiError } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import { cn, initials } from "@/lib/utils";
import { useToast } from "@/components/ui/toast";

interface SearchResults {
  query: string;
  tasks: { id: string; title: string; status: string }[];
  memories: { id: string; content: string; category: string }[];
  conversations: { id: string; title: string }[];
}

interface TopbarProps {
  user: User;
  pendingApprovals: number;
  onOpenMobileNav: () => void;
  onLoggedOut: () => void;
}

export function Topbar({ user, pendingApprovals, onOpenMobileNav, onLoggedOut }: TopbarProps) {
  const router = useRouter();
  const { toast } = useToast();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [searching, setSearching] = useState(false);
  const [showResults, setShowResults] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [bellOpen, setBellOpen] = useState(false);
  const [notifications, setNotifications] = useState<{ id: string; message: string; created_at: string }[]>([]);
  const debouncedQuery = useDebounced(query, 280);
  const searchRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const bellRef = useRef<HTMLDivElement>(null);

  // close popovers on outside click
  useEffect(() => {
    function onDocClick(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) setShowResults(false);
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
      if (bellRef.current && !bellRef.current.contains(event.target as Node)) setBellOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  // global search
  useEffect(() => {
    const q = debouncedQuery.trim();
    if (q.length < 2) {
      setResults(null);
      return;
    }
    let cancelled = false;
    setSearching(true);
    api<SearchResults>(`/search?q=${encodeURIComponent(q)}`)
      .then((data) => {
        if (!cancelled) {
          setResults(data);
          setShowResults(true);
        }
      })
      .catch(() => undefined)
      .finally(() => {
        if (!cancelled) setSearching(false);
      });
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  // notifications = recent activity + pending approvals
  useEffect(() => {
    api<{ items: { id: string; message: string; created_at: string }[] }>("/activity?limit=6")
      .then((data) => setNotifications(data.items ?? []))
      .catch(() => undefined);
  }, [pendingApprovals]);

  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      onLoggedOut();
      router.replace("/login");
    } catch (error) {
      toast({
        title: "Sign out failed",
        description: error instanceof ApiError ? error.message : "Please try again.",
        variant: "error",
      });
    }
  }

  const hasResults =
    results && (results.tasks.length > 0 || results.memories.length > 0 || results.conversations.length > 0);

  return (
    <header className="sticky top-0 z-20 flex h-16 items-center gap-3 border-b border-line bg-canvas/85 px-4 backdrop-blur lg:px-6">
      <button
        type="button"
        className="rounded-lg p-2 text-muted hover:bg-surface2 hover:text-ink lg:hidden"
        onClick={onOpenMobileNav}
        aria-label="Open menu"
      >
        <Menu className="h-5 w-5" />
      </button>

      {/* Global search */}
      <div ref={searchRef} className="relative flex-1 max-w-xl">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onFocus={() => results && setShowResults(true)}
          placeholder="Search tasks, memories, conversations…"
          className="h-10 w-full rounded-xl border border-line bg-surface2/50 pl-9 pr-3 text-sm text-ink placeholder:text-muted/70 focus:outline-none focus:ring-2 focus:ring-accent/50"
          aria-label="Global search"
        />
        {showResults && (query.trim().length >= 2) ? (
          <div className="absolute left-0 right-0 top-12 max-h-96 overflow-y-auto rounded-xl border border-line bg-surface p-2 shadow-card animate-fade-in">
            {searching && !results ? <p className="px-3 py-2 text-xs text-muted">Searching…</p> : null}
            {results && !hasResults ? (
              <p className="px-3 py-2 text-xs text-muted">No matches for “{results.query}”.</p>
            ) : null}
            {hasResults ? (
              <div className="space-y-1">
                {results!.tasks.map((task) => (
                  <Link
                    key={task.id}
                    href={`/tasks?highlight=${task.id}`}
                    onClick={() => setShowResults(false)}
                    className="block rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface2"
                  >
                    <span className="mr-2 text-[10px] uppercase tracking-wide text-accent">Task</span>
                    {task.title}
                  </Link>
                ))}
                {results!.memories.map((memory) => (
                  <Link
                    key={memory.id}
                    href={`/memory?highlight=${memory.id}`}
                    onClick={() => setShowResults(false)}
                    className="block rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface2"
                  >
                    <span className="mr-2 text-[10px] uppercase tracking-wide text-ok">Memory</span>
                    {memory.content}
                  </Link>
                ))}
                {results!.conversations.map((conversation) => (
                  <Link
                    key={conversation.id}
                    href={`/chat?conversation=${conversation.id}`}
                    onClick={() => setShowResults(false)}
                    className="block rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface2"
                  >
                    <span className="mr-2 text-[10px] uppercase tracking-wide text-warn">Chat</span>
                    {conversation.title}
                  </Link>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="flex-1" />

      {/* Notifications */}
      <div ref={bellRef} className="relative">
        <button
          type="button"
          onClick={() => setBellOpen((open) => !open)}
          className="relative rounded-lg p-2 text-muted transition hover:bg-surface2 hover:text-ink"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {pendingApprovals > 0 ? (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
              {pendingApprovals}
            </span>
          ) : null}
        </button>
        {bellOpen ? (
          <div className="absolute right-0 top-12 w-80 rounded-xl border border-line bg-surface p-2 shadow-card animate-fade-in">
            <p className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted">
              Notifications
            </p>
            {pendingApprovals > 0 ? (
              <Link
                href="/approvals"
                onClick={() => setBellOpen(false)}
                className="block rounded-lg border border-warn/25 bg-warn/10 px-3 py-2 text-xs text-warn hover:bg-warn/15"
              >
                {pendingApprovals} approval request{pendingApprovals > 1 ? "s" : ""} waiting for your
                decision
              </Link>
            ) : null}
            <div className="mt-1 space-y-0.5">
              {notifications.length === 0 ? (
                <p className="px-3 py-2 text-xs text-muted">Nothing yet — activity will appear here.</p>
              ) : (
                notifications.map((notification) => (
                  <div key={notification.id} className="rounded-lg px-3 py-2 hover:bg-surface2">
                    <p className="truncate text-xs text-ink">{notification.message}</p>
                    <p className="text-[10px] text-muted">{timeAgo(notification.created_at)}</p>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : null}
      </div>

      {/* User menu */}
      <div ref={menuRef} className="relative">
        <button
          type="button"
          onClick={() => setMenuOpen((open) => !open)}
          className="flex items-center gap-2 rounded-xl border border-line bg-surface2/50 py-1.5 pl-1.5 pr-2.5 transition hover:bg-surface2"
          aria-haspopup="menu"
          aria-expanded={menuOpen}
        >
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-accent-strong to-ok text-xs font-bold text-white">
            {initials(user.name || user.email)}
          </span>
          <span className="hidden max-w-28 truncate text-sm font-medium text-ink sm:block">
            {user.name}
          </span>
          <ChevronDown className="h-3.5 w-3.5 text-muted" />
        </button>
        {menuOpen ? (
          <div className="absolute right-0 top-12 w-56 rounded-xl border border-line bg-surface p-2 shadow-card animate-fade-in" role="menu">
            <div className="px-3 py-2">
              <p className="truncate text-sm font-medium text-ink">{user.name}</p>
              <p className="truncate text-xs text-muted">{user.email}</p>
            </div>
            <div className="my-1 border-t border-line" />
            <Link
              href="/settings"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-ink hover:bg-surface2"
              role="menuitem"
            >
              <SettingsIcon className="h-4 w-4 text-muted" /> Settings
            </Link>
            <button
              type="button"
              onClick={logout}
              className={cn(
                "flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-danger hover:bg-danger/10",
              )}
              role="menuitem"
            >
              <LogOut className="h-4 w-4" /> Sign out
            </button>
          </div>
        ) : null}
      </div>
    </header>
  );
}
