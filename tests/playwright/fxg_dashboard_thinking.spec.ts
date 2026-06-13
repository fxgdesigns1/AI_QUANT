import { test, expect } from '@playwright/test';

test('FXG Alpha Dashboard – System Thinking visible', async ({ page }) => {
  // Navigate to the control dashboard on the live alpha site
  await page.goto('https://alpha.fxgdesigns.co.uk/', { waitUntil: 'networkidle' });

  // Dashboard loads - check for title
  await expect(page.locator('text=FXG AI TRADING')).toBeVisible();

  // System Thinking panel exists
  // If the panel header is rendered independently of data, this should pass.
  const thinkingPanel = page.locator('text=System Thinking');
  await expect(thinkingPanel).toBeVisible();

  // At least one instrument card OR explicit empty state
  // This handles the case where data is missing (404) if the UI renders an empty state message.
  const cards = page.locator('[data-testid="signal-thinking-card"]');
  // Adjust the empty state text if necessary based on actual UI implementation, 
  // but this is what was requested in the plan.
  const emptyState = page.locator('text=No signal thinking data available');
  
  // Wait for either cards or empty state
  await expect(cards.first().or(emptyState)).toBeVisible();

  // Status badges exist if cards exist
  if (await cards.count() > 0) {
    await expect(cards.first().locator('text=SCANNING').or(
      cards.first().locator('text=BLOCKED')).or(
      cards.first().locator('text=NEAR MISS')).or(
      cards.first().locator('text=READY'))).toBeVisible();
  }
});
