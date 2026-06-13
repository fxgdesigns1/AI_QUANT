import { test, expect } from '@playwright/test';
import path from 'path';

// Local dashboard URL
const DASHBOARD_URL = 'http://localhost:5173';

test.describe('Local Dashboard VM Logs Verification', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard
    await page.goto(DASHBOARD_URL);
    
    // Wait for loading to finish (spinner gone)
    await expect(page.locator('.animate-spin')).not.toBeVisible({ timeout: 15000 });
  });

  test('should display Authoritative Data Source', async ({ page }) => {
    // Check for "SOURCE: VM LOGS" badge
    // The exact text might vary but we look for VM LOGS or similar
    const sourceBadge = page.locator('span', { hasText: /SOURCE:/ });
    await expect(sourceBadge).toBeVisible();
    
    const badgeText = await sourceBadge.textContent();
    console.log(`Detected Data Source: ${badgeText}`);
    
    // Assert it is NOT "unknown"
    expect(badgeText).not.toContain('UNKNOWN');
  });

  test('should render trades or explicit verified empty state', async ({ page }) => {
    // Check if we have trades or empty state
    // We look for the "VERIFIED: No closed trades" message
    const emptyStateText = page.getByText(/VERIFIED: No closed trades returned from/i).first();
    const tradesTable = page.locator('table');
    const statsCards = page.getByText('Net Profit & Loss');

    if (await emptyStateText.isVisible()) {
      console.log('Verified Empty State detected.');
      await expect(emptyStateText).toBeVisible();
      
      // Ensure specific stats are HIDDEN
      await expect(statsCards).not.toBeVisible();
      
      // Capture screenshot of empty state
      await page.screenshot({ path: path.join(process.cwd(), 'artifacts/playwright/vm_dashboard_empty.png') });

    } else {
      console.log('Trades detected.');
      // If not empty, we MUST see stats and the table
      await expect(statsCards).toBeVisible();
      
      // Select the Journal table (it's the one with specific headers or just the last one, or by section)
      // The breakdown tables also exist, so just 'table' is ambiguous
      const journalTable = page.locator('section').filter({ hasText: 'Trade Journal' }).locator('table');
      await expect(journalTable).toBeVisible();
      
      // Check for at least one row in the body
      const rows = journalTable.locator('tbody tr');
      await expect(rows.first()).toBeVisible();
      
      // Capture screenshot of trades
      await page.screenshot({ path: path.join(process.cwd(), 'artifacts/playwright/vm_dashboard_trades.png') });
    }
  });

  test('should verify account breakdown if trades exist', async ({ page }) => {
    if (await page.getByText('Net Profit & Loss').isVisible()) {
        await expect(page.getByText('By Account')).toBeVisible();
        await expect(page.getByText('By Instrument')).toBeVisible();
    }
  });
  
  test('should capture full page evidence', async ({ page }) => {
      await page.screenshot({ path: path.join(process.cwd(), 'artifacts/playwright/vm_dashboard_full.png'), fullPage: true });
  });

});
