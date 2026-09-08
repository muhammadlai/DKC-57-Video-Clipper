"use client";

import type { ApiErrorEnvelope } from "@aitzaz/types";

export class ApiError extends Error {
  status: number;
  code: string;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

interface ApiOptions {
  method?: "GET" | "POST" | "PATCH" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

/** Same-origin API client (Next.js rewrites proxy to FastAPI). */
export async function api<T>(path: string, options: ApiOptions = {}): Promise<T> {
  const { method = "GET", body, signal } = options;
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal,
      cache: "no-store",
    });
  } catch (error) {
    if ((error as Error)?.name === "AbortError") throw error;
    throw new ApiError(0, "network_error", "Cannot reach the Aitzaz AI server. Is the API running?");
  }

  if (response.status === 204) return undefined as T;

  const text = await response.text();
  let payload: unknown = undefined;
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { raw: text };
    }
  }

  if (!response.ok) {
    const envelope = (payload as ApiErrorEnvelope | undefined)?.error;
    throw new ApiError(
      response.status,
      envelope?.code ?? "http_error",
      envelope?.message ?? `Request failed (${response.status})`,
      envelope?.details,
    );
  }
  return payload as T;
}
