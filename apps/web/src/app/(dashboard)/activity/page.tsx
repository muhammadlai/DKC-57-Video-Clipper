"use client";

import { useState } from "react";
import { History, Loader2 } from "lucide-react";

import type { ActivityEntry, Paginated } from "@aitzaz/types";
import { ACTIVITY_TYPE_META, formatDateTime, timeAgo } from "@aitzaz/shared";

import { api } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

const PAGE_SIZE = 25;

export default function ActivityPage() {
  const [typeFilter, setTypeFilter] = useState("");
  const [entries, setEntries] = useState<ActivityEntry[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const baseState = useApiData<Paginated<ActivityEntry>>(
    `/activity?limit=${PAGE_SIZE}${typeFilter ? `&type=${typeFilter}` : ""}`,
    [typeFilter],
  );

  // Prefer locally-accumulated entries once "load more" has been used.
  const items = entries ?? baseState.data?.items ?? [];
  const shownTotal = total || baseState.data?.total || 0;

  async function loadMore() {
    setLoadingMore(true);
    try {
      const next = await api<Paginated<ActivityEntry>>(
        `/activity?limit=${PAGE_SIZE}&offset=${items.length}${typeFilter ? `&type=${typeFilter}` : ""}`,
      );
      setEntries([...items, ...next.items]);
      setTotal(next.total);
    } finally {
      setLoadingMore(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Activity"
        description="Complete audit trail: logins, AI messages, tasks, tool executions, approvals and memories — everything the agent does is recorded."
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => {
            setTypeFilter("");
            setEntries(null);
          }}
          className={
            "rounded-full border px-3 py-1.5 text-xs font-medium transition " +
            (typeFilter === "" ? "border-accent/40 bg-accent/10 text-accent" : "border-line text-muted hover:text-ink")
          }
        >
          All
        </button>
        {Object.entries(ACTIVITY_TYPE_META).map(([value, meta]) => (
          <button
            key={value}
            type="button"
            onClick={() => {
              setTypeFilter(value);
              setEntries(null);
            }}
            className={
              "rounded-full border px-3 py-1.5 text-xs font-medium transition " +
              (typeFilter === value
                ? "border-accent/40 bg-accent/10 text-accent"
                : "border-line text-muted hover:text-ink")
            }
          >
            {meta.label}
          </button>
        ))}
      </div>

      {baseState.error ? (
        <ErrorState message={baseState.error} onRetry={baseState.refresh} />
      ) : baseState.loading ? (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, index) => (
            <Skeleton key={index} className="h-14 w-full" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={<History className="h-5 w-5" />}
          title="No activity recorded yet"
          description="Sign in, chat with the agent, or create a task — everything shows up here."
        />
      ) : (
        <>
          <Card className="divide-y divide-line p-0">
            {items.map((entry) => {
              const meta = ACTIVITY_TYPE_META[entry.activity_type];
              return (
                <div key={entry.id} className="flex flex-wrap items-center gap-3 px-4 py-3">
                  <Badge variant="outline" className={meta?.badge}>
                    {meta?.label ?? entry.activity_type}
                  </Badge>
                  <span className="min-w-0 flex-1 truncate text-sm text-ink">{entry.message}</span>
                  <span className="text-[11px] text-muted" title={formatDateTime(entry.created_at)}>
                    {timeAgo(entry.created_at)}
                  </span>
                  {entry.ip ? <span className="hidden font-mono text-[10px] text-muted sm:inline">{entry.ip}</span> : null}
                </div>
              );
            })}
          </Card>
          {items.length < shownTotal ? (
            <div className="mt-4 flex justify-center">
              <Button variant="secondary" loading={loadingMore} onClick={() => void loadMore()}>
                <Loader2 className="h-4 w-4" /> Load more ({items.length}/{shownTotal})
              </Button>
            </div>
          ) : null}
        </>
      )}
    </div>
  );
}
