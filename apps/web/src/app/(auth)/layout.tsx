import { Sparkles } from "lucide-react";

import { APP_NAME, APP_TAGLINE } from "@aitzaz/shared";

const HIGHLIGHTS = [
  "One agent for your digital life — chat, tasks, memory, approvals.",
  "Safe by design: sensitive actions always wait for your approval.",
  "Built for Chromebooks — everything runs in the browser.",
];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen bg-canvas">
      {/* Brand panel */}
      <div className="relative hidden w-[42%] flex-col justify-between overflow-hidden border-r border-line bg-surface/50 p-10 lg:flex">
        <div
          className="pointer-events-none absolute -left-32 -top-32 h-96 w-96 rounded-full bg-accent/20 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-40 -right-24 h-96 w-96 rounded-full bg-ok/10 blur-3xl"
          aria-hidden
        />
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-2xl bg-gradient-to-br from-accent-strong to-ok text-lg font-bold text-white">
            A
          </span>
          <span className="text-lg font-semibold tracking-tight text-ink">
            Aitzaz <span className="brand-gradient">AI</span>
          </span>
        </div>
        <div className="relative">
          <h1 className="max-w-md text-3xl font-semibold leading-tight tracking-tight text-ink">
            ME → <span className="brand-gradient">Aitzaz AI</span> → Tools → Results
          </h1>
          <p className="mt-4 max-w-md text-sm leading-relaxed text-muted">
            Your central personal agent: it understands requests, uses tools, remembers what
            matters, and asks for approval before doing anything sensitive.
          </p>
          <ul className="mt-8 space-y-3">
            {HIGHLIGHTS.map((highlight) => (
              <li key={highlight} className="flex items-start gap-3 text-sm text-muted">
                <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-accent" aria-hidden />
                {highlight}
              </li>
            ))}
          </ul>
        </div>
        <p className="relative text-xs text-muted">
          Phase 1 · Foundation · Running in Demo AI mode
        </p>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 items-center justify-center p-6">
        <div className="w-full max-w-md">
          <div className="mb-8 flex items-center gap-3 lg:hidden">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-accent-strong to-ok text-base font-bold text-white">
              A
            </span>
            <span className="text-base font-semibold tracking-tight text-ink">
              Aitzaz <span className="brand-gradient">AI</span>
            </span>
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
