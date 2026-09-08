"use client";

import { useCallback, useEffect, useState } from "react";

import type { User } from "@aitzaz/types";

import { api, ApiError } from "@/lib/api";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { Skeleton } from "@/components/ui/badge";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pendingApprovals, setPendingApprovals] = useState(0);

  const loadUser = useCallback(async () => {
    try {
      const me = await api<User>("/auth/me");
      setUser(me);
      try {
        const approvals = await api<{ total: number }>("/approvals?status=pending&limit=1");
        setPendingApprovals(approvals.total ?? 0);
      } catch {
        /* non-fatal */
      }
    } catch (error) {
      if (error instanceof ApiError && (error.status === 401 || error.status === 0)) {
        window.location.href = "/login";
        return;
      }
      setAuthError(error instanceof Error ? error.message : "Failed to load session");
    }
  }, []);

  useEffect(() => {
    void loadUser();
  }, [loadUser]);

  if (authError) {
    return (
      <div className="flex min-h-screen items-center justify-center p-6">
        <div className="max-w-sm rounded-2xl border border-danger/25 bg-danger/5 p-6 text-center">
          <p className="text-sm font-medium text-danger">{authError}</p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="mt-3 rounded-lg border border-line px-3 py-1.5 text-xs text-muted hover:text-ink"
          >
            Reload
          </button>
        </div>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="min-h-screen bg-canvas">
        <div className="flex h-16 items-center border-b border-line px-6">
          <Skeleton className="h-8 w-40" />
        </div>
        <div className="mx-auto max-w-6xl space-y-6 p-6">
          <Skeleton className="h-24 w-full" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-28 w-full" />
            ))}
          </div>
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-canvas">
      <Sidebar mobileOpen={mobileOpen} onCloseMobile={() => setMobileOpen(false)} />
      <div className="lg:pl-64">
        <Topbar
          user={user}
          pendingApprovals={pendingApprovals}
          onOpenMobileNav={() => setMobileOpen(true)}
          onLoggedOut={() => {
            setUser(null);
            setPendingApprovals(0);
          }}
        />
        <main className="mx-auto w-full max-w-7xl px-4 py-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
