import { defineConfig } from "@playwright/test";

/**
 * Standalone Playwright config for the Phase 1 browser E2E.
 * See apps/web/e2e/phase1.spec.ts for run instructions.
 */
export default defineConfig({
  testDir: ".",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: process.env.WEB_ORIGIN ?? "http://127.0.0.1:3000",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
  expect: { timeout: 10_000 },
});
