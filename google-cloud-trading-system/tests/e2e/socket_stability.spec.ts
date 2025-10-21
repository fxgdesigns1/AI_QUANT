import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://ai-quant-trading.uc.r.appspot.com';

test('socket connection stays stable for 30s', async ({ page }) => {
  const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  expect(res?.status()).toBe(200);

  // Wait for initial connect with longer timeout
  await page.waitForFunction(() => (window as any).socketStats?.connects >= 1, { timeout: 15000 });

  // Observe for 30 seconds
  await page.waitForTimeout(30000);

  const stats = await page.evaluate(() => (window as any).socketStats);
  expect(stats.connects, 'should have at least one connection').toBeGreaterThanOrEqual(1);
  expect(stats.disconnects, 'should not disconnect more than once during observation').toBeLessThanOrEqual(1);
});
