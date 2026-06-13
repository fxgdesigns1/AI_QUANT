import { test, expect } from '@playwright/test';
import path from 'path';

// Local dashboard URL
const DASHBOARD_URL = 'http://localhost:5173';

test.describe('Local Dashboard Verification', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto(DASHBOARD_URL);
    
    // Wait for loading to finish (spinner gone)
    await expect(page.locator('.animate-spin')).not.toBeVisible({ timeout: 15000 });
  });

  test('should render main UI components correctly', async ({ page }) => {
    // 1. Check Title
    await expect(page.getByText('FXG / GCLOUD Dashboard')).toBeVisible();
    
    // Check VERIFIED/UNVERIFIED badge
    const verifiedBadge = page.locator('span', { hasText: /^VERIFIED$/ });
    const unverifiedBadge = page.locator('span', { hasText: /^UNVERIFIED$/ });
    await expect(verifiedBadge.or(unverifiedBadge)).toBeVisible();

    // 2. Check Sections
    // "Performance Overview" should be visible in both states
    await expect(page.getByText('Performance Overview')).toBeVisible();
  });

  test('should display either trades or verified empty state', async ({ page }) => {
    // Check if we have trades or empty state
    // Note: The empty state message appears in two places (Stats section and Journal table)
    // We use .first() to avoid strict mode violation if both are present
    const emptyStateText = page.getByText('VERIFIED: No closed trades returned from OANDA').first();
    const tradesTable = page.locator('table');
    const statsCards = page.getByText('Net Profit & Loss');

    if (await emptyStateText.isVisible()) {
      console.log('Verified Empty State detected.');
      await expect(emptyStateText).toBeVisible();
      
      // Ensure specific stats are HIDDEN
      await expect(statsCards).not.toBeVisible();
    } else {
      console.log('Trades detected.');
      // If not empty, we MUST see stats and the table
      await expect(statsCards).toBeVisible();
      await expect(tradesTable).toBeVisible();
      
      // Check for at least one row in the body
      const rows = page.locator('tbody tr');
      await expect(rows.first()).toBeVisible();
    }
  });

  test('should not have console errors', async ({ page }) => {
    const consoleErrors = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Reload to catch startup errors
    await page.reload();
    await expect(page.locator('.animate-spin')).not.toBeVisible();

    // Filter out known non-critical errors if any (but we want strictness)
    // For now, fail on any error
    expect(consoleErrors).toEqual([]);
  });

  test('should capture visual evidence', async ({ page }) => {
    // Ensure artifacts dir exists (handled by script usually, but good practice)
    
    // Take a full page screenshot
    const artifactPath = path.join(process.cwd(), 'artifacts/playwright/dashboard_full.png');
    await page.screenshot({ path: artifactPath, fullPage: true });
    console.log(`Full screenshot saved to ${artifactPath}`);

    // Take stats screenshot if visible
    if (await page.getByText('Performance Overview').isVisible()) {
        const statsPath = path.join(process.cwd(), 'artifacts/playwright/dashboard_stats.png');
        await page.locator('section').filter({ hasText: 'Performance Overview' }).screenshot({ path: statsPath });
    }
    
    // Take journal screenshot if visible
    if (await page.getByText('Trade Journal').isVisible()) {
        const journalPath = path.join(process.cwd(), 'artifacts/playwright/dashboard_journal.png');
        await page.locator('section').filter({ hasText: 'Trade Journal' }).screenshot({ path: journalPath });
    }
  });
});
