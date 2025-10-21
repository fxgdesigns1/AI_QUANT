import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://ai-quant-trading.uc.r.appspot.com';

test('AI insights section displays content', async ({ page }) => {
  const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  expect(res?.status()).toBe(200);

  // Check AI insights section is visible
  await expect(page.locator('h3', { hasText: 'AI Insights & Recommendations' })).toBeVisible();
  
  // Check specific elements exist
  await expect(page.locator('#tradePhase')).toBeVisible();
  await expect(page.locator('#newsTimer')).toBeVisible();
  await expect(page.locator('#upcomingNews')).toBeVisible();
  
  // Wait longer for data to populate
  await page.waitForTimeout(10000);
  
  // Check that AI trade phase has content (not just "Analyzing...")
  const tradePhaseText = await page.locator('#tradePhase').textContent();
  console.log('Trade Phase Text:', tradePhaseText);
  expect(tradePhaseText).toBeTruthy();
  expect(tradePhaseText?.length).toBeGreaterThan(5);
  
  // Check that news timer has content
  const newsTimerText = await page.locator('#newsTimer').textContent();
  console.log('News Timer Text:', newsTimerText);
  expect(newsTimerText).toBeTruthy();
  
  // Check that upcoming news section has content
  const upcomingNewsText = await page.locator('#upcomingNews').textContent();
  console.log('Upcoming News Text:', upcomingNewsText);
  expect(upcomingNewsText).toBeTruthy();
});
