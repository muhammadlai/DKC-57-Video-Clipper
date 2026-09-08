"use client";

import { useMemo, useState } from "react";
import { Play, Wrench } from "lucide-react";

import type { ToolInfo, ToolRunResult } from "@aitzaz/types";
import { formatDateTime } from "@aitzaz/shared";

import { api, ApiError } from "@/lib/api";
import { useApiData } from "@/lib/hooks";
import { cn, formatMs } from "@/lib/utils";
import { Badge, Skeleton } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, ErrorState } from "@/components/ui/empty-state";
import { Input, Label, Select, Textarea } from "@/components/ui/input";
import { PageHeader } from "@/components/ui/page-header";
import { useToast } from "@/components/ui/toast";

function defaultInput(tool: ToolInfo): Record<string, unknown> {
  const values: Record<string, unknown> = {};
  for (const [key, schema] of Object.entries(tool.input_schema.properties ?? {})) {
    if (schema.default !== undefined) values[key] = schema.default;
    else if (schema.type === "boolean") values[key] = false;
    else if (schema.type === "number" || schema.type === "integer") values[key] = schema.minimum ?? 0;
    else values[key] = "";
  }
  return values;
}

/** Demo-friendly starter values so every tool can be tried with one click. */
const SUGGESTED_INPUTS: Record<string, Record<string, unknown>> = {
  calculator: { expression: "125 × 48" },
  current_time: { timezone: "UTC" },
  echo: { message: "Hello from the Tools page!" },
  task_create: { title: "Try me: created from the Tools page" },
  memory_create: { content: "I was saved from the Tools page", category: "fact" },
  approval_request: {
    action_type: "send_email",
    description: "Demo request created from the Tools page",
  },
};

function InputField({
  name,
  schema,
  value,
  onChange,
}: {
  name: string;
  schema: { type?: string; description?: string; enum?: string[] };
  value: unknown;
  onChange: (value: unknown) => void;
}) {
  const id = `tool-input-${name}`;
  const requiredNote = schema.description ? <p className="mt-1 text-[10px] text-muted">{schema.description}</p> : null;

  if (schema.enum) {
    return (
      <div>
        <Label htmlFor={id}>{name}</Label>
        <Select id={id} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)}>
          {schema.enum.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </Select>
        {requiredNote}
      </div>
    );
  }
  if (schema.type === "integer" || schema.type === "number") {
    return (
      <div>
        <Label htmlFor={id}>{name}</Label>
        <Input
          id={id}
          type="number"
          value={value === null || value === undefined ? "" : String(value)}
          onChange={(event) => onChange(event.target.value === "" ? undefined : Number(event.target.value))}
        />
        {requiredNote}
      </div>
    );
  }
  if (name === "description" || name === "content") {
    return (
      <div>
        <Label htmlFor={id}>{name}</Label>
        <Textarea
          id={id}
          value={String(value ?? "")}
          onChange={(event) => onChange(event.target.value)}
          className="min-h-[64px]"
        />
        {requiredNote}
      </div>
    );
  }
  return (
    <div>
      <Label htmlFor={id}>{name}</Label>
      <Input id={id} value={String(value ?? "")} onChange={(event) => onChange(event.target.value)} />
      {requiredNote}
    </div>
  );
}

export default function ToolsPage() {
  const { toast } = useToast();
  const { data: tools, error, loading, refresh } = useApiData<ToolInfo[]>("/tools");
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [inputs, setInputs] = useState<Record<string, Record<string, unknown>>>({});
  const [running, setRunning] = useState(false);
  const [lastRun, setLastRun] = useState<ToolRunResult | null>(null);

  const selected = useMemo(
    () => tools?.find((tool) => tool.slug === selectedSlug) ?? null,
    [tools, selectedSlug],
  );

  function select(tool: ToolInfo) {
    setSelectedSlug(tool.slug);
    setLastRun(null);
    setInputs((current) => ({
      ...current,
      [tool.slug]: current[tool.slug] ?? SUGGESTED_INPUTS[tool.slug] ?? defaultInput(tool),
    }));
  }

  async function execute() {
    if (!selected) return;
    setRunning(true);
    setLastRun(null);
    try {
      const result = await api<ToolRunResult>(`/tools/${selected.slug}/execute`, {
        method: "POST",
        body: { input: inputs[selected.slug] ?? {} },
      });
      setLastRun(result);
      if (result.ok) {
        toast({ title: `${selected.name} executed`, description: `in ${formatMs(result.duration_ms)}`, variant: "success" });
      }
    } catch (err) {
      toast({
        title: "Execution failed",
        description: err instanceof ApiError ? err.message : undefined,
        variant: "error",
      });
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="animate-fade-in">
      <PageHeader
        title="Tools"
        description="The capabilities your agent can use. Executions here run the exact same validated, permission-checked, audited pipeline the agent uses."
      />

      {error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : loading ? (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-40 w-full" />
          ))}
        </div>
      ) : !tools?.length ? (
        <EmptyState icon={<Wrench className="h-5 w-5" />} title="No tools registered" />
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          {/* Tool list */}
          <div className="space-y-3 lg:col-span-2">
            {tools.map((tool) => (
              <Card
                key={tool.slug}
                className={cn(
                  "cursor-pointer p-4 transition hover:border-line",
                  selectedSlug === tool.slug && "border-accent/40 ring-1 ring-accent/30",
                )}
                onClick={() => select(tool)}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="truncate text-sm font-medium text-ink">{tool.name}</h3>
                      <Badge variant="outline">{tool.category}</Badge>
                    </div>
                    <p className="mt-1 line-clamp-2 text-xs text-muted">{tool.description}</p>
                  </div>
                  <Badge variant={tool.enabled ? "ok" : "danger"} dot>
                    {tool.enabled ? "enabled" : "disabled"}
                  </Badge>
                </div>
                <p className="mt-2 font-mono text-[10px] text-muted">
                  {tool.slug} · {tool.execution}
                  {tool.required_permission ? ` · ${tool.required_permission}` : ""}
                </p>
              </Card>
            ))}
          </div>

          {/* Run panel */}
          <div className="lg:col-span-3">
            {selected ? (
              <Card>
                <CardHeader>
                  <CardTitle>Run · {selected.name}</CardTitle>
                  <CardDescription>{selected.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {Object.keys(selected.input_schema.properties ?? {}).length === 0 ? (
                    <p className="text-xs text-muted">This tool takes no input.</p>
                  ) : (
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                      {Object.entries(selected.input_schema.properties ?? {}).map(([name, schema]) => (
                        <InputField
                          key={name}
                          name={name}
                          schema={schema}
                          value={(inputs[selected.slug] ?? {})[name]}
                          onChange={(value) =>
                            setInputs((current) => ({
                              ...current,
                              [selected.slug]: { ...(current[selected.slug] ?? {}), [name]: value },
                            }))
                          }
                        />
                      ))}
                    </div>
                  )}

                  <Button onClick={() => void execute()} loading={running}>
                    <Play className="h-4 w-4" /> Execute
                  </Button>

                  {lastRun ? (
                    <div
                      className={cn(
                        "animate-fade-in rounded-xl border p-4",
                        lastRun.ok ? "border-ok/30 bg-ok/5" : "border-danger/30 bg-danger/5",
                      )}
                    >
                      <div className="flex items-center justify-between">
                        <Badge variant={lastRun.ok ? "ok" : "danger"}>
                          {lastRun.ok ? "Success" : "Failed"} · {formatMs(lastRun.duration_ms)}
                        </Badge>
                        <span className="text-[10px] text-muted">{formatDateTime(new Date().toISOString())}</span>
                      </div>
                      <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-ink">
                        {lastRun.ok
                          ? JSON.stringify(lastRun.result, null, 2)
                          : `${lastRun.error} (${lastRun.error_code})`}
                      </pre>
                    </div>
                  ) : null}

                  <details className="text-xs text-muted">
                    <summary className="cursor-pointer select-none hover:text-ink">Input schema</summary>
                    <pre className="mt-2 overflow-auto rounded-lg bg-surface2/60 p-3 font-mono text-[10px]">
                      {JSON.stringify(selected.input_schema, null, 2)}
                    </pre>
                  </details>
                </CardContent>
              </Card>
            ) : (
              <EmptyState
                icon={<Play className="h-5 w-5" />}
                title="Pick a tool to run"
                description="Select any tool on the left, review its inputs, and execute it."
                className="h-full"
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
