import { test, expect } from '@playwright/test';

test.describe('Local Dashboard Health', () => {
  const base = 'http://127.0.0.1:8080';

  test('health endpoint returns ok', async ({ request }) => {
    const res = await request.get(`${base}/api/health`);
    expect(res.status()).toBe(200);
    const json = await res.json();
    expect(json.status).toBe('ok');
  });

  test('homepage loads without server error', async ({ page }) => {
    const res = await page.goto(`${base}/`);
    expect(res?.status()).toBe(200);
    await expect(page.locator('body')).not.toContainText('Error: Server Error');
    // Cloud card should show either Online or a numerical P&L after fallbacks
    await page.waitForTimeout(500); // allow script to run
    const cloudCard = page.locator('#cloudPerformance');
    await expect(cloudCard).not.toContainText('Cloud system unavailable');
  });
});


