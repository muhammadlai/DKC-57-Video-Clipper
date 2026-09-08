"use client";

import { Clock, Sparkles } from "lucide-react";

import { ROADMAP } from "@aitzaz/shared";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/ui/page-header";

interface ComingSoonProps {
  title: string;
  phase: string;
  description: string;
  planned: string;
}

/** Honest placeholder for features that arrive in a later phase — no fake UI. */
export function ComingSoonPage({ title, phase, description, planned }: ComingSoonProps) {
  return (
    <div className="animate-fade-in">
      <PageHeader title={title} description={description} actions={<Badge variant="outline"><Clock className="h-3 w-3" /> {phase}</Badge>} />

      <Card className="overflow-hidden">
        <div className="h-1 w-full bg-gradient-to-r from-accent-strong via-accent to-ok" />
        <CardContent className="pt-6 text-center">
          <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-accent/10 text-accent">
            <Sparkles className="h-6 w-6" />
          </span>
          <h2 className="mt-4 text-lg font-semibold text-ink">{planned}</h2>
          <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-muted">
            This capability is part of the Aitzaz AI roadmap. The Phase 1 foundation (agents, tools,
            memory, tasks, approvals, audit log) was built so this feature plugs in without a
            rewrite.
          </p>
        </CardContent>
      </Card>

      <h3 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wide text-muted">Full roadmap</h3>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {ROADMAP.map((item) => (
          <Card key={item.phase} className="p-4">
            <div className="flex items-center justify-between">
              <Badge variant={item.phase === phase ? "accent" : "outline"}>{item.phase}</Badge>
              {item.phase === phase ? <span className="text-[10px] font-medium text-accent">next up</span> : null}
            </div>
            <p className="mt-2 text-sm font-medium text-ink">{item.title}</p>
            <p className="mt-1 text-xs leading-relaxed text-muted">{item.description}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}
