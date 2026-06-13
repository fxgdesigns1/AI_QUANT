import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

/**
 * VM Alpha Trade Journal – HARD VERIFICATION
 * Run against LIVE VM dashboard. Alpha (alpha.fxgdesigns.co.uk) is behind Cloudflare Access;
 * use tunnel URL for auth-free runs: DASHBOARD_URL=http://127.0.0.1:28787 npx playwright test ...
 * Waits for /api/vm/journal/trades, asserts trade rows, account suffixes, prices, stats.
 * Screenshots -> artifacts/playwright/
 * Appends PASS/FAIL to logs/vm_trade_journal_verification.log
 */

const BASE_URL = process.env.DASHBOARD_URL || process.env.VM_ALPHA_URL || 'https://alpha.fxgdesigns.co.uk';
const JOURNAL_API = '/api/vm/journal/trades';
const VERIFY_LOG = path.join(process.cwd(), 'logs', 'vm_trade_journal_verification.log');

function appendVerification(status: 'PASS' | 'FAIL', detail: string) {
  try {
    const dir = path.dirname(VERIFY_LOG);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    const line = `${new Date().toISOString()} | Playwright verification ${status} | ${detail}\n`;
    fs.appendFileSync(VERIFY_LOG, line);
  } catch (_) {}
}

test.describe('VM Alpha Trade Journal Verification', () => {
  test('VM Trade Journal loads authoritative OANDA data', async ({ page }) => {
    test.setTimeout(60_000);
    let body: { count?: number; success?: boolean; trades?: unknown[] } = {};
    try {
      // 1. Wait for /api/vm/journal/trades response (MANDATORY)
      const journalResponse = page.waitForResponse(
        (r) => r.url().includes(JOURNAL_API) && r.request().method() === 'GET',
        { timeout: 30000 }
      );

      // 2. Navigate directly to /vm (VMTradeJournal) – only route that fetches journal API
      await page.goto(`${BASE_URL}/vm`, { waitUntil: 'domcontentloaded' });

      // 3. WAIT for journal API response
      const res = await journalResponse;
      expect(res.status()).toBe(200);

      body = (await res.json().catch(() => ({}))) as typeof body;
      expect(body.success).toBe(true);
      expect(Array.isArray(body.trades)).toBe(true);
      expect((body.count ?? 0) >= 1).toBe(true);

      // 4. UI: VM Trade Journal header
      await expect(page.locator('h1')).toContainText('VM Trade Journal', { timeout: 10000 });

      // 6. ASSERT trade table rows >= 1
      const rows = page.locator('tbody tr');
      await expect(rows).not.toHaveCount(0, { timeout: 15000 });
      await expect(page.locator('text=No closed trades')).not.toBeVisible();
      await expect(page.locator('text=Loading authoritative data')).not.toBeVisible();

      // 7. ASSERT account suffixes visible (e.g. 001–006)
      await expect(page.locator('td', { hasText: /00[1-6]/ }).first()).toBeVisible();

      // 8. ASSERT entry/exit prices rendered (decimal)
      await expect(page.locator('td', { hasText: /\d+\.\d{2,}/ }).first()).toBeVisible();

      // 9. Date range inputs
      const dateInputs = page.locator('input[type="date"]');
      await expect(dateInputs).toHaveCount(2);

      // 10. Stats visible
      await expect(page.locator('text=Net P&L')).toBeVisible();

      // Screenshots -> artifacts/playwright/vm_alpha/
      const artifactsDir = 'artifacts/playwright/vm_alpha';
      const artifactsPath = path.join(process.cwd(), artifactsDir);
      if (!fs.existsSync(artifactsPath)) fs.mkdirSync(artifactsPath, { recursive: true });
      await page.screenshot({
        path: path.join(artifactsPath, 'vm_journal_tab_trades.png'),
        fullPage: true,
      });

      // Filter: last 7 days — wait for second journal request (stats change when date range changes)
      const lastWeek = new Date();
      lastWeek.setDate(lastWeek.getDate() - 7);
      const startDate = lastWeek.toISOString().split('T')[0];
      const secondJournal = page.waitForResponse(
        (r) => r.url().includes(JOURNAL_API) && r.request().method() === 'GET',
        { timeout: 15000 }
      );
      await dateInputs.nth(0).fill(startDate);
      await new Promise((r) => setTimeout(r, 2000));
      const res2 = await secondJournal;
      expect(res2.status()).toBe(200);
      const body2 = (await res2.json().catch(() => ({}))) as { success?: boolean; count?: number };
      expect(body2.success).toBe(true);
      expect(typeof (body2.count ?? 0)).toBe('number');

      await page.screenshot({
        path: path.join(artifactsPath, 'vm_journal_filtered.png'),
        fullPage: true,
      });

      const statsSection = page.locator('section').first();
      await statsSection.screenshot({
        path: path.join(artifactsPath, 'vm_journal_stats.png'),
      });

      appendVerification(
        'PASS',
        `trade_count=${body.count ?? '?'} | ${JOURNAL_API} | trade rows visible`
      );
    } catch (e) {
      appendVerification(
        'FAIL',
        `${JOURNAL_API} | ${e instanceof Error ? e.message : String(e)}`
      );
      throw e;
    }
  });
});
