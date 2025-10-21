import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://ai-quant-trading.uc.r.appspot.com';

test('dashboard loads and shows core sections', async ({ page, request }) => {
  const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  expect(res?.status(), 'root should return 200').toBe(200);

  await expect(page.getByRole('heading', { name: /AI Trading Dashboard/i })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'Live Market Data' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'Trading Systems' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'AI Insights & Recommendations' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'Live News Feed' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'Trading Performance' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'Risk Management' })).toBeVisible();

  const [overview, risk] = await Promise.all([
    request.get(`${BASE_URL}/api/overview`),
    request.get(`${BASE_URL}/api/risk`),
  ]);
  expect(overview.status(), '/api/overview should be 200').toBe(200);
  expect(risk.status(), '/api/risk should be 200').toBe(200);
});
