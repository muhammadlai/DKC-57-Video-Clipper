"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import type { AuthResponse } from "@aitzaz/types";

import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input, Label } from "@/components/ui/input";

export default function RegisterPage() {
  const router = useRouter();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (name.trim().length < 2) {
      setError("Please enter your name.");
      return;
    }
    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      await api<AuthResponse>("/auth/register", {
        method: "POST",
        body: { name: name.trim(), email: email.trim(), password },
      });
      router.replace("/dashboard");
      router.refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Registration failed. Please try again.");
      setLoading(false);
    }
  }

  return (
    <div>
      <h2 className="text-2xl font-semibold tracking-tight text-ink">Create your account</h2>
      <p className="mt-1.5 text-sm text-muted">
        Set up your personal AI agent. Your data stays in your own database.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-4" noValidate>
        <div>
          <Label htmlFor="name">Full name</Label>
          <Input
            id="name"
            autoComplete="name"
            required
            placeholder="Aitzaz"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </div>
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
            autoComplete="new-password"
            required
            minLength={8}
            placeholder="At least 8 characters"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          <p className="mt-1.5 text-[11px] text-muted">
            Hashed with bcrypt — we never store or log your password.
          </p>
        </div>

        {error ? (
          <p role="alert" className="rounded-lg border border-danger/25 bg-danger/10 px-3 py-2 text-xs text-danger">
            {error}
          </p>
        ) : null}

        <Button type="submit" size="lg" loading={loading} className="w-full">
          Create account
        </Button>
      </form>

      <p className="mt-6 text-center text-sm text-muted">
        Already registered?{" "}
        <Link href="/login" className="font-medium text-accent hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
