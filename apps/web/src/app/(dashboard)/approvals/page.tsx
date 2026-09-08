"use client";

import { useState } from "react";
import { Check, Plus, ShieldCheck, X } from "lucide-react";

import type { Approval, Paginated } from "@aitzaz/types";
import { APPROVAL_STATUS_META, formatDateTime } from "@aitzaz/shared";

import { api, ApiError } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";

const ACTION_TYPES = [
  "send_email",
  "send_message",
  "purchase",
  "transfer_money",
  "delete_files",
  "change_settings",
  "submit_form",
  "make_call",
  "post_publicly",
  "external_action",
];

export default function ApprovalsPage() {
  const { toast } = useToast();
  const pendingState = useApiData<Paginated<Approval>>("/approvals?status=pending");
  const historyState = useApiData<Paginated<Approval>>("/approvals?limit=25");
  const [deciding, setDeciding] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState({ action_type: "send_email", description: "" });
  const [saving, setSaving] = useState(false);

  function refreshAll() {
    pendingState.refresh();
    historyState.refresh();
  }

  async function decide(approval: Approval, decision: "approved" | "rejected") {
    setDeciding(approval.id);
    try {
      await api(`/approvals/${approval.id}/decision`, {
        method: "POST",
        body: { decision, note: note.trim() || undefined },
      });
      toast({
        title: decision === "approved" ? "Request approved" : "Request rejected",
        description: decision === "approved"
          ? "The connector for this action type arrives in a later phase — nothing was executed."
          : "The agent will not perform this action.",
        variant: decision === "approved" ? "success" : "info",
      });
      setNote("");
      refreshAll();
    } catch (err) {
      toast({
        title: "Decision failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setDeciding(null);
    }
  }

  async function createRequest(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/approvals", {
        method: "POST",
        body: { action_type: form.action_type, description: form.description.trim() },
      });
      setCreateOpen(false);
      setForm({ action_type: "send_email", description: "" });
      refreshAll();
      toast({ title: "Approval request created", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not create request",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  }

  const pending = pendingState.data?.items ?? [];
  const history = historyState.data?.items ?? [];

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Approvals"
        description="The agent prepares sensitive actions (emails, purchases, deletions…) but never executes them without your explicit approval."
        actions={
          <Button variant="secondary" onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> New request (demo)
          </Button>
        }
      />

      <div className="mb-4 rounded-xl border border-warn/25 bg-warn/5 px-4 py-3 text-xs text-warn">
        Phase 1 wires the approval architecture. No real email/banking/etc. connectors exist yet —
        approving records the decision and keeps the audit trail, it does not contact external
        services.
      </div>

      {pendingState.error ? (
        <ErrorState message={pendingState.error} onRetry={pendingState.refresh} />
      ) : pendingState.loading ? (
        <div className="space-y-3">
          {Array.from({ length: 2 }).map((_, index) => (
            <Skeleton key={index} className="h-32 w-full" />
          ))}
        </div>
      ) : pending.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck className="h-5 w-5" />}
          title="No pending approvals"
          description="You're all caught up. When the agent prepares a sensitive action, it will wait for you here."
          action={
            <Button variant="secondary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> Create a demo request
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {pending.map((approval) => (
            <Card key={approval.id} className="border-warn/25 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant="warn" dot>
                      {approval.action_type.replace(/_/g, " ")}
                    </Badge>
                    <span className="text-[11px] text-muted">
                      requested {formatDateTime(approval.requested_at)}
                      {approval.expires_at ? ` · expires ${formatDateTime(approval.expires_at)}` : ""}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-ink">{approval.description}</p>
                  {Object.keys(approval.payload ?? {}).length > 0 ? (
                    <pre className="mt-2 max-w-full overflow-x-auto rounded-lg bg-surface2/60 p-2.5 font-mono text-[11px] text-muted">
                      {JSON.stringify(approval.payload, null, 2)}
                    </pre>
                  ) : null}
                </div>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Input
                  value={note}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Optional note for the audit log…"
                  className="h-9 max-w-xs text-xs"
                />
                <Button
                  variant="success"
                  size="sm"
                  loading={deciding === approval.id}
                  onClick={() => void decide(approval, "approved")}
                >
                  <Check className="h-4 w-4" /> Approve
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  loading={deciding === approval.id}
                  onClick={() => void decide(approval, "rejected")}
                >
                  <X className="h-4 w-4" /> Reject
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* History */}
      <h2 className="mb-3 mt-10 text-sm font-semibold uppercase tracking-wide text-muted">
        Decision history
      </h2>
      {historyState.loading ? (
        <Skeleton className="h-24 w-full" />
      ) : history.length === 0 ? (
        <p className="text-xs text-muted">No decisions yet.</p>
      ) : (
        <div className="space-y-2">
          {history
            .filter((approval) => approval.status !== "pending")
            .map((approval) => {
              const meta = APPROVAL_STATUS_META[approval.status];
              return (
                <Card key={approval.id} className="flex flex-wrap items-center gap-3 p-3.5">
                  <Badge variant="outline" className={meta?.badge}>
                    {meta?.label ?? approval.status}
                  </Badge>
                  <span className="min-w-0 flex-1 truncate text-xs text-ink">
                    <span className="mr-2 text-muted">{approval.action_type.replace(/_/g, " ")}</span>
                    {approval.description}
                  </span>
                  {approval.decision_note ? (
                    <span className="max-w-48 truncate text-[11px] text-muted">“{approval.decision_note}”</span>
                  ) : null}
                  <span className="text-[11px] text-muted">{formatDateTime(approval.decided_at)}</span>
                </Card>
              );
            })}
        </div>
      )}

      {/* Create demo request */}
      <Dialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        title="New approval request"
        description="Simulate what the agent does when it needs permission for a sensitive action."
      >
        <form onSubmit={createRequest} className="space-y-4">
          <div>
            <Label htmlFor="approval-action">Action type</Label>
            <Select
              id="approval-action"
              value={form.action_type}
              onChange={(event) => setForm({ ...form, action_type: event.target.value })}
            >
              {ACTION_TYPES.map((action) => (
                <option key={action} value={action}>
                  {action.replace(/_/g, " ")}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <Label htmlFor="approval-description">What should be done?</Label>
            <Textarea
              id="approval-description"
              required
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="e.g. Send the contract to John at john@example.com"
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={saving} disabled={!form.description.trim()}>
              Create request
            </Button>
          </div>
        </form>
      </Dialog>
    </div>
  );
}
