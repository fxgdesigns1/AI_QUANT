import { test, expect } from "@playwright/test";

const baseURL = process.env.DASHBOARD_URL || "http://127.0.0.1:8787/";

test.describe("Forensic dashboard exhaustive interaction", () => {
  test("all interactive elements are safe and truth-gated", async ({ page }) => {
    const consoleErrors: string[] = [];
    const badResponses: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") consoleErrors.push(msg.text());
    });
    page.on("pageerror", (err) => consoleErrors.push(err.message));
    page.on("response", (resp) => {
      if (resp.status() >= 400) badResponses.push(`${resp.status()} ${resp.url()}`);
    });
    page.on("dialog", (dialog) => dialog.accept());

    await page.goto(baseURL, { waitUntil: "domcontentloaded" });
    const token = process.env.CONTROL_PLANE_TOKEN || "";
    if (token) {
      await page.evaluate((value) => {
        localStorage.setItem("control_plane_token", value);
      }, token);
    }

    const truthResponse = await page.request.get(new URL("/api/truth/status", baseURL).toString());
    if (!truthResponse.ok()) {
      throw new Error(`Truth status request failed: ${truthResponse.status()}`);
    }
    const truthBody = await truthResponse.json();
    if (!truthBody || !truthBody.truth || truthBody.truth.complete !== true) {
      throw new Error("Truth status incomplete: truth.complete != true");
    }
    if (!truthBody.data || truthBody.data.system_truth_state !== "FULL") {
      throw new Error(`Truth status not FULL: ${truthBody?.data?.system_truth_state}`);
    }

    const clickIfVisible = async (selector: string) => {
      const loc = page.locator(selector);
      if (await loc.count()) {
        if (await loc.first().isVisible()) await loc.first().click();
      }
    };

    // Tabs
    await clickIfVisible("#nav-terminal");
    await page.evaluate(() => {
      const fn = (window as any).showTab;
      if (typeof fn === "function") {
        return fn("terminal");
      }
      throw new Error("showTab is not defined");
    });
    await expect(page.locator("#tab-terminal")).toHaveClass(/active/);
    await clickIfVisible("#nav-mesh");
    await clickIfVisible("#nav-reports");
    await clickIfVisible("#nav-journal");
    await clickIfVisible("#nav-strategies");
    await clickIfVisible("#nav-news");
    await clickIfVisible("#nav-terminal");

    // Terminal tab actions
    if (token) {
      const strategyButtons = page.locator("#strategy-buttons [data-strategy-key]");
      const strategyCount = await strategyButtons.count();
      for (let i = 0; i < Math.min(strategyCount, 3); i += 1) {
        await strategyButtons.nth(i).click();
      }
    }
    const chartSelect = page.locator("#chart-symbol");
    await expect(chartSelect).toBeVisible();
    await chartSelect.selectOption({ value: "OANDA:EURUSD" });
    await chartSelect.selectOption({ value: "OANDA:XAUUSD" });
    await clickIfVisible("#btn-manual-override");

    // Journal tab actions
    await clickIfVisible("#nav-journal");
    await clickIfVisible("#btn-export-csv");
    await clickIfVisible("#btn-filter-trades");
    const tradeToggles = page.locator("[onclick*=\"toggleTradeDetails\"]");
    const toggleCount = await tradeToggles.count();
    for (let i = 0; i < toggleCount; i += 1) {
      await tradeToggles.nth(i).click();
    }

    // Settings modal open/close/save/clear
    await clickIfVisible("#btn-settings");
    await clickIfVisible("#settings-save");
    await clickIfVisible("#settings-clear");
    await clickIfVisible("#settings-close");
    const settingsModal = page.locator("#settings-modal");
    if (await settingsModal.isVisible()) {
      await clickIfVisible("#settings-close");
      await expect(settingsModal).toBeHidden();
    }

    // Strategies tab actions
    await clickIfVisible("#nav-strategies");
    await clickIfVisible("#btn-reload-cloud-sync");
    await clickIfVisible("#btn-deploy-nodes");

    expect(consoleErrors).toEqual([]);
    expect(badResponses).toEqual([]);
  });
});
