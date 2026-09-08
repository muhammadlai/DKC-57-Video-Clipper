/**
 * Playwright E2E — the full Phase 1 user journey in a real browser.
 *
 * NOTE: run this on a machine with network access to Playwright's browser CDN
 * (the build sandbox could not download Chromium):
 *   cd apps/web
 *   npm i -D playwright && npx playwright install chromium
 *   BACKEND_ORIGIN=http://127.0.0.1:8000 npx playwright test --config e2e/playwright.config.ts
 *
 * Requires the API on :8000 and the web app on :3000 (both seeded).
 */
import { expect, test, type Page } from "@playwright/test";

const WEB = process.env.WEB_ORIGIN ?? "http://127.0.0.1:3000";
const EMAIL = `e2e-browser-${Date.now()}@aitzaz.test`;
const PASSWORD = "browser-e2e-123";

async function register(page: Page) {
  await page.goto(`${WEB}/register`);
  await page.getByLabel("Full name").fill("Browser Tester");
  await page.getByLabel("Email").fill(EMAIL);
  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await page.waitForURL("**/dashboard");
}

test.describe("Aitzaz AI — Phase 1 E2E", () => {
  test("register → chat → task → memory → tool → approval → activity → logout → login", async ({ page }) => {
    // REGISTER → DASHBOARD
    await register(page);
    await expect(page.getByRole("heading", { name: "AI Command Center" })).toBeVisible();

    // SEND MESSAGE → DEMO AI RESPONDS
    await page.getByRole("button", { name: "AI Chat" }).first().click();
    await page.getByLabel("Message").fill("Hello Aitzaz");
    await page.getByLabel("Message").press("Enter");
    await expect(page.getByText("Demo AI").first()).toBeVisible({ timeout: 15000 });

    // CALCULATOR VIA CHAT
    await page.getByLabel("Message").fill("Calculate 125 × 48");
    await page.getByLabel("Message").press("Enter");
    await expect(page.getByText("6,000").first()).toBeVisible({ timeout: 15000 });

    // CREATE TASK (UI)
    await page.getByRole("link", { name: "Tasks" }).click();
    await page.getByRole("button", { name: "New task" }).click();
    await page.getByLabel("Title").fill("Browser E2E task");
    await page.getByRole("button", { name: "Create task" }).click();
    await expect(page.getByText("Browser E2E task")).toBeVisible();

    // CREATE MEMORY (UI)
    await page.getByRole("link", { name: "Memory" }).click();
    await page.getByRole("button", { name: "Add memory" }).click();
    await page.getByLabel("What should Aitzaz remember?").fill("I like browser-driven tests");
    await page.getByRole("button", { name: "Save memory" }).click();
    await expect(page.getByText("I like browser-driven tests")).toBeVisible();

    // EXECUTE CALCULATOR TOOL (Tools page)
    await page.getByRole("link", { name: "Tools" }).click();
    await page.getByText("Calculator", { exact: true }).click();
    await page.getByRole("button", { name: "Execute" }).click();
    await expect(page.getByText("Success", { exact: false }).first()).toBeVisible({ timeout: 10000 });

    // CREATE + APPROVE an approval request
    await page.getByRole("link", { name: "Approvals" }).click();
    await page.getByRole("button", { name: "New request (demo)" }).click();
    await page.getByLabel("What should be done?").fill("Send the E2E report to John");
    await page.getByRole("button", { name: "Create request" }).click();
    await page.getByRole("button", { name: "Approve" }).first().click();
    await expect(page.getByText("Request approved")).toBeVisible();

    // ACTIVITY LOG UPDATED
    await page.getByRole("link", { name: "Activity" }).click();
    await expect(page.getByText("Tool executed").first()).toBeVisible();
    await expect(page.getByText("Approved").first()).toBeVisible();

    // LOGOUT → LOGIN AGAIN → data persists
    await page.getByRole("button", { name: /Browser Tester/ }).click();
    await page.getByRole("menuitem", { name: "Sign out" }).click();
    await page.waitForURL("**/login");
    await page.getByLabel("Email").fill(EMAIL);
    await page.getByLabel("Password").fill(PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await page.waitForURL("**/dashboard");

    await page.getByRole("link", { name: "Tasks" }).click();
    await expect(page.getByText("Browser E2E task")).toBeVisible();
  });
});
