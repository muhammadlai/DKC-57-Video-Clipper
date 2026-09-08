"use client";

import { useState } from "react";
import { Brain, Info, ListTodo, MessageSquare, Pencil, Plus, Sparkles, Star, Trash2 } from "lucide-react";

import type { Memory, Paginated } from "@aitzaz/types";
import { MEMORY_CATEGORY_META, formatDateTime } from "@aitzaz/shared";

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

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  preference: <Sparkles className="h-4 w-4" />,
  fact: <Info className="h-4 w-4" />,
  conversation: <MessageSquare className="h-4 w-4" />,
  task: <ListTodo className="h-4 w-4" />,
  system: <Brain className="h-4 w-4" />,
};

function ImportanceStars({ value }: { value: number }) {
  return (
    <span className="flex items-center gap-0.5" title={`Importance ${value}/5`}>
      {Array.from({ length: 5 }).map((_, index) => (
        <Star
          key={index}
          className={cn("h-3 w-3", index < value ? "fill-warn text-warn" : "text-line")}
        />
      ))}
    </span>
  );
}

export default function MemoryPage() {
  const { toast } = useToast();
  const [categoryFilter, setCategoryFilter] = useState("");
  const { data, error, loading, refresh } = useApiData<Paginated<Memory>>(
    `/memories${categoryFilter ? `?category=${categoryFilter}` : ""}`,
    [categoryFilter],
  );
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<Memory | null>(null);
  const [form, setForm] = useState({ content: "", category: "fact", importance: 3 });
  const [saving, setSaving] = useState(false);

  const memories = data?.items ?? [];

  async function createMemory(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    try {
      await api("/memories", {
        method: "POST",
        body: { content: form.content.trim(), category: form.category, importance: form.importance },
      });
      setCreateOpen(false);
      setForm({ content: "", category: "fact", importance: 3 });
      refresh();
      toast({ title: "Memory saved", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not save memory",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  }

  async function saveEdit(event: React.FormEvent) {
    event.preventDefault();
    if (!editing) return;
    setSaving(true);
    try {
      await api(`/memories/${editing.id}`, {
        method: "PATCH",
        body: { content: editing.content, category: editing.category, importance: editing.importance },
      });
      setEditing(null);
      refresh();
      toast({ title: "Memory updated", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not update memory",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setSaving(false);
    }
  }

  async function deleteMemory(memory: Memory) {
    if (!window.confirm("Delete this memory?")) return;
    try {
      await api(`/memories/${memory.id}`, { method: "DELETE" });
      refresh();
      toast({ title: "Memory deleted", variant: "success" });
    } catch (err) {
      toast({
        title: "Could not delete memory",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Memory"
        description="What Aitzaz AI remembers about you. The agent adds memories automatically when you say “Remember that…”."
        actions={
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="h-4 w-4" /> Add memory
          </Button>
        }
      />

      <div className="mb-4 flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => setCategoryFilter("")}
          className={cn(
            "rounded-full border px-3 py-1.5 text-xs font-medium transition",
            categoryFilter === "" ? "border-accent/40 bg-accent/10 text-accent" : "border-line text-muted hover:text-ink",
          )}
        >
          All
        </button>
        {Object.entries(MEMORY_CATEGORY_META).map(([value, meta]) => (
          <button
            key={value}
            type="button"
            onClick={() => setCategoryFilter(value)}
            className={cn(
              "rounded-full border px-3 py-1.5 text-xs font-medium transition",
              categoryFilter === value
                ? "border-accent/40 bg-accent/10 text-accent"
                : "border-line text-muted hover:text-ink",
            )}
          >
            {meta.label}
          </button>
        ))}
      </div>

      {error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : loading ? (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {Array.from({ length: 6 }).map((_, index) => (
            <Skeleton key={index} className="h-36 w-full" />
          ))}
        </div>
      ) : memories.length === 0 ? (
        <EmptyState
          icon={<Brain className="h-5 w-5" />}
          title="Nothing remembered yet"
          description="Add a memory manually, or tell the agent: “Remember that I prefer dark mode”."
          action={
            <Button variant="secondary" size="sm" onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" /> Add memory
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {memories.map((memory) => {
            const meta = MEMORY_CATEGORY_META[memory.category];
            return (
              <Card key={memory.id} className="group flex flex-col p-4">
                <div className="flex items-center justify-between gap-2">
                  <Badge variant="outline" className={meta?.badge}>
                    {CATEGORY_ICONS[memory.category]}
                    {meta?.label ?? memory.category}
                  </Badge>
                  <ImportanceStars value={memory.importance} />
                </div>
                <p className="mt-3 flex-1 text-sm leading-relaxed text-ink">{memory.content}</p>
                <div className="mt-3 flex items-center justify-between border-t border-line pt-2.5">
                  <span className="text-[11px] text-muted">{formatDateTime(memory.created_at)}</span>
                  <div className="flex gap-1 opacity-0 transition group-hover:opacity-100">
                    <Button variant="ghost" size="icon" aria-label="Edit memory" onClick={() => setEditing(memory)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label="Delete memory" onClick={() => void deleteMemory(memory)}>
                      <Trash2 className="h-3.5 w-3.5 text-danger" />
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} title="Add a memory">
        <form onSubmit={createMemory} className="space-y-4">
          <div>
            <Label htmlFor="memory-content">What should Aitzaz remember?</Label>
            <Textarea
              id="memory-content"
              required
              value={form.content}
              onChange={(event) => setForm({ ...form, content: event.target.value })}
              placeholder="e.g. My sister's birthday is March 3"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="memory-category">Category</Label>
              <Select
                id="memory-category"
                value={form.category}
                onChange={(event) => setForm({ ...form, category: event.target.value })}
              >
                {Object.entries(MEMORY_CATEGORY_META).map(([value, meta]) => (
                  <option key={value} value={value}>
                    {meta.label}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="memory-importance">Importance (1–5)</Label>
              <Input
                id="memory-importance"
                type="number"
                min={1}
                max={5}
                value={form.importance}
                onChange={(event) => setForm({ ...form, importance: Number(event.target.value) })}
              />
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={saving} disabled={!form.content.trim()}>
              Save memory
            </Button>
          </div>
        </form>
      </Dialog>

      <Dialog open={!!editing} onClose={() => setEditing(null)} title="Edit memory">
        {editing ? (
          <form onSubmit={saveEdit} className="space-y-4">
            <div>
              <Label htmlFor="edit-memory-content">Content</Label>
              <Textarea
                id="edit-memory-content"
                required
                value={editing.content}
                onChange={(event) => setEditing({ ...editing, content: event.target.value })}
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label htmlFor="edit-memory-category">Category</Label>
                <Select
                  id="edit-memory-category"
                  value={editing.category}
                  onChange={(event) => setEditing({ ...editing, category: event.target.value as Memory["category"] })}
                >
                  {Object.entries(MEMORY_CATEGORY_META).map(([value, meta]) => (
                    <option key={value} value={value}>
                      {meta.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="edit-memory-importance">Importance</Label>
                <Input
                  id="edit-memory-importance"
                  type="number"
                  min={1}
                  max={5}
                  value={editing.importance}
                  onChange={(event) => setEditing({ ...editing, importance: Number(event.target.value) })}
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
