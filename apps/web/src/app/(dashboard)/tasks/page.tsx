"use client";

import { useMemo, useState } from "react";
import { CalendarDays, ListTodo, Pencil, Plus, Trash2 } from "lucide-react";

import type { Paginated, Task } from "@aitzaz/types";
import { PRIORITY_META, TASK_STATUS_META, formatDateTime } from "@aitzaz/shared";

import { api, ApiError } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";

const STATUS_TABS = [
  { value: "", label: "All" },
  { value: "pending", label: "Pending" },
  { value: "running", label: "Running" },
  { value: "waiting_approval", label: "Waiting approval" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
  { value: "cancelled", label: "Cancelled" },
];

const NEXT_ACTIONS: Record<string, { status: string; label: string }[]> = {
  pending: [
    { status: "running", label: "Start" },
    { status: "completed", label: "Complete" },
    { status: "cancelled", label: "Cancel" },
  ],
  running: [
    { status: "completed", label: "Complete" },
    { status: "failed", label: "Fail" },
    { status: "cancelled", label: "Cancel" },
  ],
  waiting_approval: [{ status: "cancelled", label: "Cancel" }],
  failed: [{ status: "pending", label: "Reopen" }],
  completed: [],
  cancelled: [],
};

interface TaskForm {
  title: string;
  description: string;
  priority: string;
  due_at: string;
}

const EMPTY_FORM: TaskForm = { title: "", description: "", priority: "medium", due_at: "" };

export default function TasksPage() {
  const { toast } = useToast();
  const [statusFilter, setStatusFilter] = useState("");
  const { data, error, loading, refresh } = useApiData<Paginated<Task>>(
    `/tasks${statusFilter ? `?status=${statusFilter}` : ""}`,
    [statusFilter],
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [form, setForm] = useState<TaskForm>(EMPTY_FORM);
  const [editing, setEditing] = useState<Task | null>(null);
  const [saving, setSaving] = useState(false);

  const tasks = useMemo(() => data?.items ?? [], [data]);

  async function createTask(event: React.FormEvent) {
    event.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true);
    try {
      await api("/tasks", {
        method: "POST",
        body: {
          title: form.title.trim(),
          description: form.description.trim(),
          priority: form.priority,
          due_at: form.due_at ? new Date(form.due_at).toISOString() : null,
        },
      });
      setCreateOpen(false);
      setForm(EMPTY_FORM);
      refresh();
      toast({ title: "Task created", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not create task",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  }

  async function updateTask(task: Task, changes: Partial<TaskForm> & { status?: string }) {
    try {
      await api(`/tasks/${task.id}`, {
        method: "PATCH",
        body: {
          ...(changes.title !== undefined ? { title: changes.title } : {}),
          ...(changes.description !== undefined ? { description: changes.description } : {}),
          ...(changes.priority !== undefined ? { priority: changes.priority } : {}),
          ...(changes.status !== undefined ? { status: changes.status } : {}),
          ...(changes.due_at !== undefined
            ? { due_at: changes.due_at ? new Date(changes.due_at).toISOString() : null }
            : {}),
        },
      });
      refresh();
      toast({ title: "Task updated", variant: "success" });
    } catch (err) {
      toast({
        title: "Update failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    }
  }

  async function deleteTask(task: Task) {
    if (!window.confirm(`Delete task “${task.title}”?`)) return;
    try {
      await api(`/tasks/${task.id}`, { method: "DELETE" });
      refresh();
      toast({ title: "Task deleted", variant: "success" });
    } catch (err) {
      toast({
        title: "Delete failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    }
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editing || !editing.title.trim()) return;
    setSaving(true);
    await updateTask(editing, {
      title: editing.title,
      description: editing.description ?? "",
      priority: editing.priority,
      status: editing.status,
      due_at: editing.due_at ?? "",
    });
    setSaving(false);
    setEditing(null);
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Tasks"
        description="What Aitzaz is tracking for you. Tasks created by the agent (e.g. “Remind me to…”) appear here too."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> New task
          </Button>
        }
      />

      {/* Status tabs */}
      <div className="mb-4 flex flex-wrap gap-1.5">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            type="button"
            onClick={() => setStatusFilter(tab.value)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition",
              statusFilter === tab.value
                ? "border-accent/40 bg-accent/10 text-accent"
                : "border-line text-muted hover:text-ink",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : loading ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-20 w-full" />
          ))}
        </div>
      ) : tasks.length === 0 ? (
        <EmptyState
          icon={<ListTodo className="h-5 w-5" />}
          title="No tasks here"
          description="Create one manually, or tell the agent: “Remind me to call the bank tomorrow”."
          action={
            <Button variant="secondary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> New task
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => {
            const statusMeta = TASK_STATUS_META[task.status];
            const priorityMeta = PRIORITY_META[task.priority];
            const actions = NEXT_ACTIONS[task.status] ?? [];
            return (
              <Card key={task.id} className="p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h3 className="truncate text-sm font-medium text-ink">{task.title}</h3>
                      <Badge variant="outline" className={statusMeta?.badge}>{statusMeta?.label ?? task.status}</Badge>
                      <Badge variant="outline" className={priorityMeta?.badge}>{priorityMeta?.label ?? task.priority}</Badge>
                    </div>
                    {task.description ? (
                      <p className="mt-1.5 line-clamp-2 text-xs text-muted">{task.description}</p>
                    ) : null}
                    <p className="mt-2 flex items-center gap-1.5 text-[11px] text-muted">
                      <CalendarDays className="h-3 w-3" />
                      {task.due_at ? `Due ${formatDateTime(task.due_at)}` : "No due date"}
                      <span className="mx-1">·</span> created {formatDateTime(task.created_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5">
                    {actions.map((action) => (
                      <Button
                        key={action.status}
                        variant="secondary"
                        size="sm"
                        onClick={() => void updateTask(task, { status: action.status })}
                      >
                        {action.label}
                      </Button>
                    ))}
                    <Button variant="ghost" size="icon" aria-label="Edit task" onClick={() => setEditing({ ...task, description: task.description ?? "" })}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label="Delete task" onClick={() => void deleteTask(task)}>
                      <Trash2 className="h-4 w-4 text-danger" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} title="New task" description="Give the task a clear title — you can add details after.">
        <form onSubmit={createTask} className="space-y-4">
          <div>
            <Label htmlFor="task-title">Title</Label>
            <Input
              id="task-title"
              required
              value={form.title}
              onChange={(event) => setForm({ ...form, title: event.target.value })}
              placeholder="e.g. Prepare Q4 report"
            />
          </div>
          <div>
            <Label htmlFor="task-description">Description</Label>
            <Textarea
              id="task-description"
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
              placeholder="Optional details…"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="task-priority">Priority</Label>
              <Select
                id="task-priority"
                value={form.priority}
                onChange={(event) => setForm({ ...form, priority: event.target.value })}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </Select>
            </div>
            <div>
              <Label htmlFor="task-due">Due date</Label>
              <Input
                id="task-due"
                type="datetime-local"
                value={form.due_at}
                onChange={(event) => setForm({ ...form, due_at: event.target.value })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={saving} disabled={!form.title.trim()}>
              Create task
            </Button>
          </div>
        </form>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onClose={() => setEditing(null)} title="Edit task">
        {editing ? (
          <form onSubmit={saveEdit} className="space-y-4">
            <div>
              <Label htmlFor="edit-title">Title</Label>
              <Input
                id="edit-title"
                required
                value={editing.title}
                onChange={(event) => setEditing({ ...editing, title: event.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                value={editing.description ?? ""}
                onChange={(event) => setEditing({ ...editing, description: event.target.value })}
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label htmlFor="edit-status">Status</Label>
                <Select
                  id="edit-status"
                  value={editing.status}
                  onChange={(event) => setEditing({ ...editing, status: event.target.value as Task["status"] })}
                >
                  {STATUS_TABS.filter((tab) => tab.value).map((tab) => (
                    <option key={tab.value} value={tab.value}>
                      {tab.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="edit-priority">Priority</Label>
                <Select
                  id="edit-priority"
                  value={editing.priority}
                  onChange={(event) => setEditing({ ...editing, priority: event.target.value as Task["priority"] })}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="urgent">Urgent</option>
                </Select>
              </div>
              <div>
                <Label htmlFor="edit-due">Due</Label>
                <Input
                  id="edit-due"
                  type="datetime-local"
                  value={editing.due_at ? new Date(editing.due_at).toISOString().slice(0, 16) : ""}
                  onChange={(event) =>
                    setEditing({ ...editing, due_at: event.target.value ? event.target.value : null })
                  }
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="ghost" onClick={() => setEditing(null)}>
                Cancel
              </Button>
              <Button type="submit" loading={saving}>
                Save changes
              </Button>
            </div>
          </form>
        ) : null}
      </Dialog>
    </div>
  );
}
