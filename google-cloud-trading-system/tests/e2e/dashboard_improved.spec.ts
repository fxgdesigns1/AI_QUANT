import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://ai-quant-trading.uc.r.appspot.com';

test('improved dashboard loads with news feed and AI insights', async ({ page }) => {
  const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  expect(res?.status()).toBe(200);

  // Check main sections are visible
  await expect(page.getByRole('heading', { name: /AI Trading Dashboard/i })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'AI Insights & Recommendations' })).toBeVisible();
  await expect(page.locator('h3', { hasText: 'Live News Feed' })).toBeVisible();
  
  // Check connection status
  await expect(page.locator('#connectionStatus')).toBeVisible();
  
  // Check that news feed has content
  await expect(page.locator('#newsAlerts')).toBeVisible();
  
  // Check that AI insights section has content
  await expect(page.locator('#tradePhase')).toBeVisible();
  await expect(page.locator('#newsTimer')).toBeVisible();
  
  // Wait a bit for data to load
  await page.waitForTimeout(5000);
  
  // Check that some data has populated
  const newsContent = await page.locator('#newsAlerts').textContent();
  expect(newsContent).toContain('AI Trading System');
  
  const aiContent = await page.locator('#tradePhase').textContent();
  expect(aiContent).toBeTruthy();
});
