"use client";

import { Bot, Clock, Sparkles } from "lucide-react";

import type { Agent, FutureAgent } from "@aitzaz/types";
import { formatDateTime } from "@aitzaz/shared";

import { useApiData } from "@/lib/hooks";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ErrorState } from "@/components/ui/empty-state";
import { PageHeader } from "@/components/ui/page-header";

export default function AgentsPage() {
  const agentsState = useApiData<Agent[]>("/agents");
  const futureState = useApiData<{ agents: FutureAgent[] }>("/agents/future");

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Agents"
        description="Your agent roster. Phase 1 ships the Personal Assistant; specialist agents arrive in later phases on the same architecture."
      />

      {agentsState.error ? (
        <ErrorState message={agentsState.error} onRetry={agentsState.refresh} />
      ) : agentsState.loading ? (
        <Skeleton className="h-64 w-full" />
      ) : (
        <div className="space-y-4">
          {agentsState.data?.map((agent) => (
            <Card key={agent.id}>
              <CardHeader className="flex-row items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-strong to-ok text-white">
                    <Bot className="h-5 w-5" />
                  </span>
                  <div>
                    <CardTitle className="text-base">{agent.name}</CardTitle>
                    <CardDescription className="mt-1 max-w-2xl">{agent.description}</CardDescription>
                  </div>
                </div>
                <Badge variant={agent.status === "active" ? "ok" : "warn"} dot>
                  {agent.status}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Capabilities</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {agent.capabilities.map((capability) => (
                        <Badge key={capability} variant="accent">
                          <Sparkles className="h-3 w-3" /> {capability}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Tools</p>
                    <div className="mt-2 flex flex-wrap gap-1.5">
                      {agent.tools.map((tool) => (
                        <Badge key={tool} variant="outline">
                          {tool}
                        </Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">Details</p>
                    <ul className="mt-2 space-y-1 text-xs text-muted">
                      <li>slug: <span className="font-mono text-ink">{agent.slug}</span></li>
                      <li>created {formatDateTime(agent.created_at)}</li>
                      <li>updated {formatDateTime(agent.updated_at)}</li>
                    </ul>
                  </div>
                </div>
                <details className="mt-4 text-xs text-muted">
                  <summary className="cursor-pointer select-none hover:text-ink">System instructions</summary>
                  <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-surface2/60 p-3 font-mono text-[10px] leading-relaxed">
                    {agent.system_instructions}
                  </pre>
                </details>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <h2 className="mb-3 mt-10 text-sm font-semibold uppercase tracking-wide text-muted">
        Coming in later phases
      </h2>
      {futureState.loading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-28 w-full" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          {futureState.data?.agents.map((futureAgent) => (
            <Card key={futureAgent.slug} className="p-4 opacity-80">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium text-ink">{futureAgent.name}</h3>
                <Badge variant="outline">
                  <Clock className="h-3 w-3" /> {futureAgent.phase}
                </Badge>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-muted">{futureAgent.description}</p>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
