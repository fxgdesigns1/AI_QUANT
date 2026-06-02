import { test, expect } from "@playwright/test";

const baseURL = process.env.DASHBOARD_URL || "http://127.0.0.1:8787/";

test.describe("Forensic dashboard safety", () => {
  test("all interactive controls are safe", async ({ page }) => {
    const consoleErrors: string[] = [];
    const serverErrors: string[] = [];

    page.on("console", (msg) => {
      if (msg.type() === "error") {
        consoleErrors.push(msg.text());
      }
    });
    page.on("pageerror", (err) => {
      consoleErrors.push(err.message);
    });
    page.on("response", (resp) => {
      if (resp.status() >= 500) {
        serverErrors.push(`${resp.status()} ${resp.url()}`);
      }
    });
    page.on("dialog", (dialog) => dialog.accept());

    await page.goto(baseURL, { waitUntil: "domcontentloaded" });
    const token = process.env.CONTROL_PLANE_TOKEN || "";
    if (token) {
      await page.evaluate((value) => {
        localStorage.setItem("control_plane_token", value);
      }, token);
    }

    const clickIfVisible = async (selector: string) => {
      const loc = page.locator(selector);
      if (await loc.count()) {
        if (await loc.first().isVisible()) await loc.first().click();
      }
    };
    const ensureSettingsClosed = async () => {
      const modal = page.locator("#settings-modal");
      if (await modal.count()) {
        if (await modal.isVisible()) {
          await page.click("#settings-close", { force: true }).catch(() => {});
          await page.keyboard.press("Escape").catch(() => {});
          await modal.waitFor({ state: "hidden", timeout: 2000 }).catch(() => {});
        }
      }
    };

    await clickIfVisible("#nav-terminal");
    if (token) {
      const strategyButtons = page.locator("#strategy-buttons [data-strategy-key]");
      const strategyCount = await strategyButtons.count();
      for (let i = 0; i < Math.min(strategyCount, 3); i += 1) {
        await strategyButtons.nth(i).click();
      }
    }
    await page.selectOption("#chart-symbol", { value: "OANDA:EURUSD" });
    await clickIfVisible("#btn-manual-override");

    await clickIfVisible("#nav-journal");
    await ensureSettingsClosed();
    await clickIfVisible("#btn-export-csv");
    await clickIfVisible("#btn-settings");
    await clickIfVisible("#settings-close");
    await ensureSettingsClosed();
    await clickIfVisible("#btn-filter-trades");
    await ensureSettingsClosed();
    const tradeToggles = page.locator("[onclick*=\"toggleTradeDetails\"]");
    const toggleCount = await tradeToggles.count();
    for (let i = 0; i < Math.min(toggleCount, 3); i += 1) {
      await ensureSettingsClosed();
      await tradeToggles.nth(i).click();
    }

    await ensureSettingsClosed();
    await clickIfVisible("#nav-strategies");
    await clickIfVisible("#btn-reload-cloud-sync");
    await clickIfVisible("#btn-deploy-nodes");

    await clickIfVisible("#nav-news");
    await clickIfVisible("#nav-reports");
    await clickIfVisible("#nav-mesh");

    expect(consoleErrors).toEqual([]);
    expect(serverErrors).toEqual([]);
  });
});
