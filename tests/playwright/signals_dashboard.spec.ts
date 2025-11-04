import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'http://localhost:8080';

test.describe('Signals Dashboard', () => {
  test('loads and shows counts', async ({ page }) => {
    await page.goto(`${BASE_URL}/signals`);
    await expect(page).toHaveTitle(/Signals/i);

    // Stats bar elements exist
    await expect(page.locator('[data-testid="stats-total"]')).toBeVisible();
    await expect(page.locator('[data-testid="stats-pending"]')).toBeVisible();
    await expect(page.locator('[data-testid="stats-active"]')).toBeVisible();

    // Backend API reachable
    const resp = await page.request.get(`${BASE_URL}/api/signals`);
    expect(resp.ok()).toBeTruthy();
    const json = await resp.json();
    expect(json).toHaveProperty('status');
    expect(json).toHaveProperty('count');
  });

  test('filters can be changed', async ({ page }) => {
    await page.goto(`${BASE_URL}/signals`);
    const strategySelect = page.locator('[data-testid="filter-strategy"]');
    await expect(strategySelect).toBeVisible();
    const options = await strategySelect.locator('option').all();
    expect(options.length).toBeGreaterThan(0);
    // Select first non-empty option if present
    for (const opt of options) {
      const value = await opt.getAttribute('value');
      if (value) {
        await strategySelect.selectOption(value);
        break;
      }
    }
  });
});


