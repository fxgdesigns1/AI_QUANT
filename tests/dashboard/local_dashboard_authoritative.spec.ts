import { test, expect } from '@playwright/test';

test.describe('OANDA Authoritative Dashboard Verification', () => {
  test('should display authoritative trade data and conform to UX standards', async ({ page }) => {
    // 1. Navigate to Dashboard (served by Python API or Vite)
    // Assuming running on 5001 per api_local.py default
    await page.goto('http://localhost:5001');

    // 2. Verify Header & Badge
    await expect(page.locator('h1')).toContainText('OANDA Trade Journal');
    await expect(page.locator('header')).toContainText('SOURCE: OANDA /trades (authoritative)');

    // 3. Verify Filters exist
    await expect(page.getByLabel('Account')).toBeVisible();
    await expect(page.getByLabel('Instrument')).toBeVisible();

    // 4. Wait for data load
    // Check if table has rows or empty state, but wait for loading to disappear
    await expect(page.getByText('Loading authoritative data...')).not.toBeVisible({ timeout: 10000 });

    // 5. Verify Data Table
    // Should have rows if data exists. Based on previous turns, we have 10017 trades.
    const rows = page.locator('tbody tr');
    const count = await rows.count();
    expect(count).toBeGreaterThan(0);
    
    // Check first row content structure
    const firstRow = rows.first();
    // Use regex to match any standard pair format (XXX_XXX)
    await expect(firstRow).toContainText(/_/, { timeout: 5000 }); 
    await expect(firstRow).toContainText('$'); // Currency

    // 6. Verify Summary Metrics
    // Check for "Trades", "Net P&L", "Win Rate" labels
    await expect(page.getByText('Trades', { exact: true })).toBeVisible();
    await expect(page.getByText('Net P&L', { exact: true })).toBeVisible();
    await expect(page.getByText('Win Rate', { exact: true })).toBeVisible();

    // 7. Test Filtering (Interaction)
    // Select an account if dropdown has options
    const accountSelect = page.getByLabel('Account');
    const options = await accountSelect.locator('option').allInnerTexts();
    
    if (options.length > 1) {
        // Select second option (first is ALL)
        const targetAccount = options[1].replace('Account ', '').trim();
        await accountSelect.selectOption({ label: options[1] });
        
        // Wait for reload
        await page.waitForTimeout(1000); // Small wait for effect
        
        // Check if rows are filtered (suffix should match)
        // Note: The UI displays suffix in first column
        await expect(firstRow).toContainText(targetAccount.split('-').pop());
    }

    // 8. Capture Proof
    await page.screenshot({ path: 'artifacts/playwright/authoritative_dashboard_full.png', fullPage: true });
    await page.locator('table').screenshot({ path: 'artifacts/playwright/authoritative_dashboard_table.png' });
  });
});
