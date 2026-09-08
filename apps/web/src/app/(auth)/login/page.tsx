"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";

import type { AuthResponse } from "@aitzaz/types";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  );
}

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await api<AuthResponse>("/auth/login", {
        method: "POST",
        body: { email: email.trim(), password },
      });
      const next = searchParams.get("next");
      router.replace(next && next.startsWith("/") ? next : "/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Sign in failed. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight text-ink">Welcome back</h2>
      <p className="mt-1.5 text-sm text-muted">Sign in to your Aitzaz AI workspace.</p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
        <div>
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            placeholder="••••••••"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        {error ? (
          <p role="alert" className="rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-danger">
            {error}
          </p>
        ) : null}

        <Button type="submit" size="lg" loading={loading} className="w-full">
          Sign in
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        No account yet?{" "}
        <Link href="/register" className="font-medium text-accent hover:underline">
          Create one
        </Link>
      </p>

      <div className="mt-8 rounded-xl border border-line bg-surface/60 p-4">
        <p className="text-xs font-medium text-muted">Development demo account</p>
        <p className="mt-1 font-mono text-xs text-ink">demo@aitzaz.ai / demo-user-2026</p>
        <p className="mt-1 text-[11px] text-muted">
          Created by the seed script — documented development credentials.
        </p>
      </div>
    </div>
  );
}
