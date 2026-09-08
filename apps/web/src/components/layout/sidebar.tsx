"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Bot,
  Brain,
  FolderOpen,
  Globe,
  History,
  LayoutDashboard,
  ListTodo,
  MessageSquare,
  Settings,
  ShieldCheck,
  Telescope,
  Workflow,
  Wrench,
  X,
  type LucideIcon,
} from "lucide-react";

import { APP_NAME, NAV_ITEMS } from "@aitzaz/shared";

import { cn } from "@/lib/utils";

const ICONS: Record<string, LucideIcon> = {
  LayoutDashboard,
  MessageSquare,
  ListTodo,
  Workflow,
  Brain,
  Wrench,
  FolderOpen,
  Telescope,
  Globe,
  Bot,
  History,
  ShieldCheck,
  Settings,
};

interface SidebarProps {
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ mobileOpen, onCloseMobile }: SidebarProps) {
  const pathname = usePathname();

  const content = (
    <div className="flex h-full flex-col">
      <div className="flex h-16 items-center justify-between border-b border-line px-5">
        <Link href="/dashboard" className="flex items-center gap-2.5" onClick={onCloseMobile}>
          <span className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-accent-strong to-ok text-sm font-bold text-white">
            A
          </span>
          <span className="text-[15px] font-semibold tracking-tight text-ink">
            Aitzaz <span className="brand-gradient">AI</span>
          </span>
        </Link>
        <button
          type="button"
          className="rounded-lg p-1.5 text-muted hover:text-ink lg:hidden"
          onClick={onCloseMobile}
          aria-label="Close menu"
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-4" aria-label="Main navigation">
        {NAV_ITEMS.map((item) => {
          const Icon = ICONS[item.icon] ?? Bot;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={onCloseMobile}
              className={cn(
                "group flex items-center gap-3 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-accent/10 text-accent"
                  : "text-muted hover:bg-surface2 hover:text-ink",
              )}
            >
              <Icon className={cn("h-[18px] w-[18px]", active && "text-accent")} aria-hidden />
              <span className="flex-1">{item.label}</span>
              {item.phase ? (
                <span className="rounded-md border border-line px-1.5 py-0.5 text-[10px] text-muted opacity-80">
                  P{item.phase}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-line px-5 py-4">
        <p className="text-[11px] leading-relaxed text-muted">
          {APP_NAME} · Phase 1 foundation
          <br />
          Demo AI mode — no real LLM connected yet.
        </p>
      </div>
    </div>
  );

  return (
    <>
      {/* Desktop */}
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-64 border-r border-line bg-surface/60 backdrop-blur lg:block">
        {content}
      </aside>

      {/* Mobile overlay */}
      {mobileOpen ? (
        <div className="fixed inset-0 z-40 lg:hidden">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onCloseMobile} aria-hidden />
          <aside className="absolute inset-y-0 left-0 w-72 max-w-[85vw] border-r border-line bg-surface animate-fade-in">
            {content}
          </aside>
        </div>
      ) : null}
    </>
  );
}
