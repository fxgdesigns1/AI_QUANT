import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://ai-quant-trading.uc.r.appspot.com';

test('debug AI insights with console logs', async ({ page }) => {
  // Listen to console logs
  page.on('console', msg => {
    if (msg.text().includes('📊') || msg.text().includes('🔌') || msg.text().includes('🔄')) {
      console.log('Browser Console:', msg.text());
    }
  });

  const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  expect(res?.status()).toBe(200);

  // Wait for connection and initial data
  await page.waitForTimeout(15000);
  
  // Check what's actually displayed
  const tradePhaseText = await page.locator('#tradePhase').textContent();
  const newsTimerText = await page.locator('#newsTimer').textContent();
  const upcomingNewsText = await page.locator('#upcomingNews').textContent();
  
  console.log('Final Trade Phase:', tradePhaseText);
  console.log('Final News Timer:', newsTimerText);
  console.log('Final Upcoming News:', upcomingNewsText);
  
  // The test passes if we can see the elements, regardless of content
  expect(tradePhaseText).toBeTruthy();
  expect(newsTimerText).toBeTruthy();
  expect(upcomingNewsText).toBeTruthy();
});
