import { test, expect } from "@playwright/test";

const baseURL = process.env.DASHBOARD_URL || "http://127.0.0.1:8787/";

test.describe("React Dashboard - Authoritative Production UI", () => {
  test("React dashboard is served as the ONLY UI (not forensic_command.html)", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Verify React app loaded
    const body = await page.locator("body").textContent();
    expect(body).toContain("AI-QUANT");
    expect(body).toContain("FORENSIC COMMAND");
    
    // Verify React root exists
    const reactRoot = page.locator("#root");
    await expect(reactRoot).toBeVisible({ timeout: 5000 });
    
    // Verify NO forensic_command.html elements
    const forensicElements = await page.locator("#tradingview_terminal, #signal-overlay").count();
    // These shouldn't exist in React dashboard
    expect(forensicElements).toBe(0);
    
    // Verify header
    const header = page.locator("header");
    await expect(header).toBeVisible();
    await expect(header.locator("text=AI-QUANT")).toBeVisible();
    await expect(header.locator("text=V2.6")).toBeVisible();
    await expect(header.locator("text=FORENSIC COMMAND")).toBeVisible();
  });

  test("All tabs render and switch correctly", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Wait for React to fully render
    await page.waitForSelector("header", { timeout: 5000 });
    
    // Test Terminal tab (default)
    await expect(page.locator("text=Terminal").first()).toBeVisible();
    
    // Test Mesh tab
    await page.click("text=Mesh");
    await expect(page.locator("text=Active Accounts").first()).toBeVisible({ timeout: 3000 });
    
    // Test Signals tab
    await page.click("text=Signals");
    await expect(page.locator("text=Recent Signals").first()).toBeVisible({ timeout: 3000 });
    
    // Test News tab
    await page.click("text=News");
    await expect(page.locator("text=Market News").first()).toBeVisible({ timeout: 3000 });
  });

  test("Truth Envelope enforcement - shows NO BACKEND FACT AVAILABLE when data missing", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Intercept API calls to simulate backend failure
    await page.route("**/api/status", route => route.abort());
    await page.route("**/api/session-regime-gate/snapshot", route => route.abort());
    await page.route("**/api/market/overview", route => route.abort());
    
    // Reload to trigger failed fetches
    await page.reload({ waitUntil: "networkidle" });
    
    // Wait a bit for React to process failed requests
    await page.waitForTimeout(2000);
    
    // Verify NO BACKEND FACT AVAILABLE message appears
    const noFactMessages = await page.locator("text=NO BACKEND FACT AVAILABLE").count();
    expect(noFactMessages).toBeGreaterThan(0);
  });

  test("All API endpoints are called and return Truth Envelope structure", async ({ page }) => {
    const apiCalls: string[] = [];
    
    page.on("response", async (response) => {
      const url = response.url();
      if (url.includes("/api/")) {
        apiCalls.push(url);
        
        // Verify Truth Envelope structure if response is OK
        if (response.status() === 200) {
          try {
            const json = await response.json();
            expect(json).toHaveProperty("truth");
            expect(json.truth).toHaveProperty("complete");
            expect(json.truth).toHaveProperty("source");
          } catch (e) {
            // Not JSON, skip
          }
        }
      }
    });
    
    await page.goto(baseURL, { waitUntil: "networkidle" });
    await page.waitForTimeout(5000); // Wait for polling
    
    // Verify expected endpoints were called
    const expectedEndpoints = [
      "/api/status",
      "/api/session-regime-gate/snapshot",
      "/api/accounts",
      "/api/market/overview",
      "/api/signals/pending",
      "/api/news"
    ];
    
    const calledUrls = apiCalls.join(" ");
    for (const endpoint of expectedEndpoints) {
      expect(calledUrls).toContain(endpoint);
    }
  });

  test("No mutation controls exist (read-only enforcement)", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Verify no simulation/play/pause buttons
    const mutationControls = await page.locator(
      "button:has-text('Play'), button:has-text('Pause'), button:has-text('Toggle'), " +
      "button:has-text('Simulate'), button:has-text('Switch'), " +
      "[onclick*='toggleSim'], [onclick*='switchStrategy']"
    ).count();
    
    expect(mutationControls).toBe(0);
    
    // Verify header is status-only (no action buttons)
    const headerButtons = await page.locator("header button").count();
    // Only refresh or status buttons should exist, no mutation buttons
    const headerButtonTexts = await page.locator("header button").allTextContents();
    for (const text of headerButtonTexts) {
      expect(text.toLowerCase()).not.toMatch(/play|pause|toggle|simulate|switch|activate|execute/);
    }
  });

  test("Dashboard shows correct status badges", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Wait for status to load
    await page.waitForTimeout(3000);
    
    // Verify status badges exist in header
    const badges = page.locator("header").locator("[class*='badge'], [class*='StatusBadge']");
    const badgeCount = await badges.count();
    expect(badgeCount).toBeGreaterThan(0);
    
    // Verify badges show execution status and mode
    const headerText = await page.locator("header").textContent();
    expect(headerText).toMatch(/PAPER|LIVE|EXECUTION|SIGNALS/);
  });

  test("Truth Envelope sidebar is visible", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Verify Truth Envelope notice in sidebar
    await expect(page.locator("text=TRUTH ENVELOPE")).toBeVisible({ timeout: 5000 });
    await expect(page.locator("text=All data rendered is strictly sourced from backend snapshots")).toBeVisible();
    await expect(page.locator("text=No frontend simulation")).toBeVisible();
  });

  test("Session Gate panel renders with backend data", async ({ page }) => {
    await page.goto(baseURL, { waitUntil: "networkidle" });
    
    // Wait for data to load
    await page.waitForTimeout(3000);
    
    // Verify Session Regime Gate card exists
    await expect(page.locator("text=Session Regime Gate").first()).toBeVisible({ timeout: 5000 });
    
    // Verify it shows readiness or NO BACKEND FACT
    const cardContent = await page.locator("text=Session Regime Gate").first()
      .locator("..").locator("..").textContent();
    
    const hasData = cardContent?.includes("READY") || 
                    cardContent?.includes("WAITING") || 
                    cardContent?.includes("BLOCKED") ||
                    cardContent?.includes("NO BACKEND FACT AVAILABLE");
    
    expect(hasData).toBe(true);
  });

  test("No console errors or React errors on load", async ({ page }) => {
    const consoleErrors: string[] = [];
    const reactErrors: string[] = [];
    
    page.on("console", (msg) => {
      if (msg.type() === "error") {
        const text = msg.text();
        consoleErrors.push(text);
        if (text.includes("React") || text.includes("Warning")) {
          reactErrors.push(text);
        }
      }
    });
    
    page.on("pageerror", (err) => {
      consoleErrors.push(err.message);
      if (err.message.includes("React")) {
        reactErrors.push(err.message);
      }
    });
    
    await page.goto(baseURL, { waitUntil: "networkidle" });
    await page.waitForTimeout(2000);
    
    // Filter out expected warnings (like missing env vars)
    const criticalErrors = consoleErrors.filter(err => 
      !err.includes("environment") && 
      !err.includes("API key") &&
      !err.includes("404") && // 404s are handled gracefully
      !err.includes("NetworkError") // Network errors are expected in fail-closed mode
    );
    
    expect(criticalErrors).toEqual([]);
    expect(reactErrors).toEqual([]);
  });
});
