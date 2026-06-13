import { test, expect } from '@playwright/test';

/**
 * Dashboard Full Wiring Verification
 * 
 * Verifies that all tabs are fully implemented and connected to backend data.
 * Checks for absence of "coming soon" placeholders and presence of real data structures.
 */

const DASHBOARD_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:8787';

test.describe('Dashboard Full Wiring Verification', () => {
  
  test.beforeEach(async ({ page }) => {
    await page.goto(DASHBOARD_URL, { waitUntil: 'networkidle' });
    // Wait for initial data load
    await page.waitForTimeout(1000);
  });

  test('Accounts tab shows real data table, not placeholder', async ({ page }) => {
    await page.click('button:has-text("Accounts")');
    await page.waitForTimeout(500);
    
    // Verify "coming soon" is NOT present
    const placeholder = page.locator('text=Accounts panel coming soon');
    await expect(placeholder).not.toBeVisible();
    
    // Verify "Active Accounts" header is present
    await expect(page.locator('text=Active Accounts')).toBeVisible();
    
    // Verify table headers exist
    await expect(page.locator('th:has-text("Account ID")')).toBeVisible();
    await expect(page.locator('th:has-text("Balance")')).toBeVisible();
    await expect(page.locator('th:has-text("Equity")')).toBeVisible();
    
    // Verify at least one account row exists (based on previous API checks showing 6 accounts)
    // We check for table rows in the tbody
    const rows = page.locator('tbody tr');
    await expect(rows).toHaveCount(await rows.count()); 
    // Just ensuring we can query rows. To be strict, let's assert count > 0 if we expect data.
    // Given the previous `curl` showed accounts, we expect > 0.
    const rowCount = await rows.count();
    console.log(`Found ${rowCount} account rows`);
    expect(rowCount).toBeGreaterThan(0);
  });

  test('Journal tab shows signals list, not placeholder', async ({ page }) => {
    await page.click('button:has-text("Journal")');
    await page.waitForTimeout(500);
    
    // Verify "coming soon" is NOT present
    const placeholder = page.locator('text=Journal panel coming soon');
    await expect(placeholder).not.toBeVisible();
    
    // Verify "Recent Signals" header is present
    await expect(page.locator('h3:has-text("Recent Signals")')).toBeVisible();
    
    // Verify we see either the list or the "No recent signals" empty state (which is a valid implemented state)
    // The empty state message we implemented is "No recent signals generated"
    const contentVisible = await Promise.race([
        page.locator('text=No recent signals generated').isVisible(),
        page.locator('.glass-card div:has-text("BUY")').isVisible(), // Check for a signal card
        page.locator('.glass-card div:has-text("SELL")').isVisible()
    ]);
    expect(contentVisible).toBeTruthy();
  });

  test('Intelligence tab shows news feed, not placeholder', async ({ page }) => {
    await page.click('button:has-text("Intelligence")');
    await page.waitForTimeout(500);
    
    // Verify "coming soon" is NOT present
    const placeholder = page.locator('text=Intelligence panel coming soon');
    await expect(placeholder).not.toBeVisible();
    
    // Verify "Market Intelligence" header is present
    await expect(page.locator('text=Market Intelligence')).toBeVisible();
    
    // Verify news items are present (based on previous curl showing news)
    // We look for time stamps or titles
    const newsItems = page.locator('text=/Impact/'); // We implemented an Impact badge
    const count = await newsItems.count();
    console.log(`Found ${count} news items with impact badges`);
    expect(count).toBeGreaterThan(0);
  });

  test('Settings tab shows configuration, not placeholder', async ({ page }) => {
    await page.click('button:has-text("Settings")');
    await page.waitForTimeout(500);
    
    // Verify "coming soon" is NOT present
    const placeholder = page.locator('text=Settings panel coming soon');
    await expect(placeholder).not.toBeVisible();
    
    // Verify "System Configuration" header is present
    await expect(page.locator('text=System Configuration')).toBeVisible();
    
    // Verify specific settings fields
    await expect(page.locator('text=Execution Mode')).toBeVisible();
    await expect(page.locator('text=Execution Enabled')).toBeVisible();
    await expect(page.locator('text=Active Strategy')).toBeVisible();
  });

});
