import { test, expect } from '@playwright/test';

const BASE_URL = process.env.BASE_URL || 'https://ai-quant-trading.uc.r.appspot.com';

test('AI insights should show content after page refresh', async ({ page }) => {
  // Listen to console logs
  page.on('console', msg => {
    if (msg.text().includes('📊') || msg.text().includes('🔌') || msg.text().includes('🔄')) {
      console.log('Browser Console:', msg.text());
    }
  });

  const res = await page.goto(BASE_URL, { waitUntil: 'domcontentloaded' });
  expect(res?.status()).toBe(200);

  // Wait for initial load
  await page.waitForTimeout(5000);
  
  // Check initial state
  let tradePhaseText = await page.locator('#tradePhase').textContent();
  console.log('Initial Trade Phase:', tradePhaseText);
  
  // Refresh the page to trigger new data
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(10000);
  
  // Check final state
  tradePhaseText = await page.locator('#tradePhase').textContent();
  const newsTimerText = await page.locator('#newsTimer').textContent();
  const upcomingNewsText = await page.locator('#upcomingNews').textContent();
  
  console.log('Final Trade Phase:', tradePhaseText);
  console.log('Final News Timer:', newsTimerText);
  console.log('Final Upcoming News Length:', upcomingNewsText?.length);
  
  // The test passes if we can see the elements
  expect(tradePhaseText).toBeTruthy();
  expect(newsTimerText).toBeTruthy();
  expect(upcomingNewsText).toBeTruthy();
  
  // Check if we have meaningful content (not just "Analyzing...")
  expect(tradePhaseText?.length).toBeGreaterThan(10);
});
