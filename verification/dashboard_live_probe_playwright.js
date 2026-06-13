#!/usr/bin/env node
/**
 * LAB Dashboard Live Probe (Playwright)
 *
 * Goals:
 * - Prove the page renders
 * - Prove /api calls happen
 * - Prove at least one response contains a truth envelope ("truth" object)
 * - Prove no non-GET requests are made (read-only)
 *
 * Secrets:
 * - This script never reads or logs passwords.
 */

const { chromium } = require("playwright");

const DASHBOARD_URL = process.env.DASHBOARD_URL || "http://127.0.0.1:9443/";
const TIMEOUT_MS = Number(process.env.PROBE_TIMEOUT_MS || 45_000);

function nowIso() {
  return new Date().toISOString();
}

async function main() {
  const result = {
    ts_utc: nowIso(),
    dashboard_url: DASHBOARD_URL,
    page_rendered: false,
    api_calls_present: false,
    truth_envelope_seen: false,
    non_readonly_requests: [],
    api_requests: [],
    console_errors: [],
  };

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  page.on("console", (msg) => {
    if (msg.type() === "error") {
      result.console_errors.push(msg.text());
    }
  });

  page.on("request", (req) => {
    const url = req.url();
    const method = req.method().toUpperCase();
    if (url.includes("/api/")) {
      result.api_requests.push({ method, url });
      if (method !== "GET") {
        result.non_readonly_requests.push(`${method} ${url}`);
      }
    }
  });

  page.on("response", async (resp) => {
    const url = resp.url();
    if (!url.includes("/api/")) return;
    result.api_calls_present = true;
    // Only inspect JSON-ish responses
    try {
      const ct = (resp.headers()["content-type"] || "").toLowerCase();
      if (!ct.includes("application/json")) return;
      const body = await resp.text();
      if (body && body.includes("\"truth\"")) {
        result.truth_envelope_seen = true;
      }
    } catch {
      // ignore parse/IO errors
    }
  });

  try {
    await page.goto(DASHBOARD_URL, { waitUntil: "domcontentloaded", timeout: TIMEOUT_MS });
    await page.waitForSelector("body", { timeout: TIMEOUT_MS });
    result.page_rendered = true;

    // Give app time to fetch initial endpoints (our app polls)
    await page.waitForTimeout(6_000);

    // Simple navigation: click a couple of tabs if present
    for (const label of ["Signals", "System", "News"]) {
      const button = page.getByRole("button", { name: new RegExp(label, "i") }).first();
      if (await button.count()) {
        await button.click();
        await page.waitForTimeout(1_000);
      }
    }

    // Final wait for any late /api calls
    await page.waitForTimeout(3_000);
  } finally {
    await browser.close();
  }

  const pass =
    result.page_rendered &&
    result.api_calls_present &&
    result.truth_envelope_seen &&
    result.non_readonly_requests.length === 0;

  result.status = pass ? "PASS" : "FAIL";

  // Print machine-readable output (safe: contains no secrets)
  console.log(JSON.stringify(result, null, 2));

  process.exit(pass ? 0 : 2);
}

main().catch((e) => {
  console.error("Probe crashed:", e && e.stack ? e.stack : String(e));
  process.exit(3);
});

