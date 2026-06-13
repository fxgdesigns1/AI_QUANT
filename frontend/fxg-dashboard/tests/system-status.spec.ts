import { test, expect } from '@playwright/test';

const BASE_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787';

test.describe('System Status Badge and Routing', () => {
  test('Dashboard loads at /', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    
    // Verify page loaded (check for React root or dashboard content)
    await expect(page.locator('body')).toBeVisible();
    
    // Check for no 404 errors
    const title = await page.title();
    expect(title).not.toContain('404');
  });

  test('Dashboard loads at /control', async ({ page }) => {
    await page.goto(`${BASE_URL}/control`, { waitUntil: 'networkidle' });
    
    // Verify page loaded
    await expect(page.locator('body')).toBeVisible();
    
    // Check for no 404 errors
    const title = await page.title();
    expect(title).not.toContain('404');
  });

  test('System Status badge visible on /', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    
    // Wait for badge to potentially load (it fetches /api/status)
    await page.waitForTimeout(2000);
    
    // Check for badge text containing 'SYSTEM' (more flexible pattern)
    const badgeText = await page.locator('text=/SYSTEM/i').first();
    await expect(badgeText).toBeVisible({ timeout: 5000 });
  });

  test('System Status badge visible on /control', async ({ page }) => {
    await page.goto(`${BASE_URL}/control`, { waitUntil: 'networkidle' });
    
    // Wait for badge to potentially load
    await page.waitForTimeout(2000);
    
    // Check for badge text containing 'SYSTEM' (more flexible pattern)
    const badgeText = await page.locator('text=/SYSTEM/i').first();
    await expect(badgeText).toBeVisible({ timeout: 5000 });
  });

  test('Badge text contains SYSTEM', async ({ page }) => {
    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);
    
    // Look for badge element with SYSTEM text
    const badge = page.locator('text=/SYSTEM/i').first();
    await expect(badge).toBeVisible({ timeout: 5000 });
    
    const text = await badge.textContent();
    expect(text).toMatch(/SYSTEM/i);
  });

  test('No console errors on dashboard load', async ({ page }) => {
    const consoleErrors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    page.on('pageerror', (err) => {
      consoleErrors.push(err.message);
    });

    await page.goto(`${BASE_URL}/`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(2000);

    // Filter out benign network errors
    const criticalErrors = consoleErrors.filter(
      (msg) =>
        !/NetworkError|net::ERR/i.test(msg) &&
        !/favicon\.ico/.test(msg) &&
        !/Failed to fetch/i.test(msg)
    );
    
    expect(criticalErrors).toEqual([]);
  });

  test('API endpoints return expected responses', async ({ request }) => {
    // Test /api/status
    const statusResponse = await request.get(`${BASE_URL}/api/status`);
    expect(statusResponse.status()).toBe(200);
    const statusData = await statusResponse.json();
    expect(statusData).toHaveProperty('data');
    expect(statusData.data).toHaveProperty('execution_enabled');

    // Test /api/system/why_no_trades
    const whyNoTradesResponse = await request.get(`${BASE_URL}/api/system/why_no_trades`);
    expect(whyNoTradesResponse.status()).toBe(200);
    const whyNoTradesData = await whyNoTradesResponse.json();
    expect(whyNoTradesData).toBeDefined();
  });
});
