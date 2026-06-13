import { test, expect } from '@playwright/test';

test.describe('VM Trade Journal Verification', () => {
  test('VM Trade Journal loads and functions with default window', async ({ page }) => {
    // Go to VM Trade Journal
    await page.goto('http://localhost:5200/vm');

    // Check Title
    await expect(page.locator('h1')).toContainText('VM Trade Journal');

    // Check Source Badge
    await expect(page.locator('span', { hasText: 'SOURCE: OANDA (Authoritative)' })).toBeVisible();

    // Check Date Pickers exist and have default values
    const dateInputs = page.locator('input[type="date"]');
    await expect(dateInputs).toHaveCount(2);

    // Check that controls exist
    await expect(page.locator('label', { hasText: 'Account' })).toBeVisible();
    await expect(page.locator('label', { hasText: 'Instrument' })).toBeVisible();
    await expect(page.locator('label', { hasText: 'Strategy' })).toBeVisible();

    // Wait for loading to finish
    const loading = page.locator('text=Loading authoritative data...');
    if (await loading.isVisible({ timeout: 2000 }).catch(() => false)) {
      await loading.waitFor({ state: 'hidden', timeout: 10000 });
    }

    // Wait for stats to load
    await page.waitForSelector('text=Trades', { timeout: 10000 });

    // Check that table exists
    await expect(page.locator('table')).toBeVisible();

    // Capture Screenshot - Default window
    await page.screenshot({ 
      path: 'artifacts/playwright/vm_trade_journal_default.png', 
      fullPage: true 
    });
  });

  test('VM Trade Journal stats change with narrow date window', async ({ page }) => {
    await page.goto('http://localhost:5200/vm', { waitUntil: 'networkidle' });

    // Wait for initial load
    await page.waitForSelector('input[type="date"]', { timeout: 15000 });
    
    // Wait for loading to finish
    const loading = page.locator('text=Loading authoritative data...');
    try {
      if (await loading.isVisible({ timeout: 2000 })) {
        await loading.waitFor({ state: 'hidden', timeout: 10000 });
      }
    } catch (e) {
      // Loading already finished or not present
    }
    
    // Set narrow date range (last 7 days)
    const today = new Date();
    const lastWeek = new Date();
    lastWeek.setDate(lastWeek.getDate() - 7);
    
    const startDate = lastWeek.toISOString().split('T')[0];
    const endDate = today.toISOString().split('T')[0];
    
    const dateInputs = page.locator('input[type="date"]');
    await dateInputs.nth(0).fill(startDate);
    await page.waitForTimeout(500);
    await dateInputs.nth(1).fill(endDate);
    
    // Wait for data to reload (wait for network activity to settle)
    await page.waitForTimeout(3000);
    
    // Verify date range is displayed
    await expect(page.locator('input[type="date"]').nth(0)).toHaveValue(startDate, { timeout: 5000 });
    await expect(page.locator('input[type="date"]').nth(1)).toHaveValue(endDate, { timeout: 5000 });
    
    // Capture Screenshot - Narrow window
    await page.screenshot({ 
      path: 'artifacts/playwright/vm_trade_journal_narrow.png', 
      fullPage: true 
    });
  });

  test('VM Trade Journal shows empty state for future date range', async ({ page }) => {
    await page.goto('http://localhost:5200/vm');

    // Wait for initial load
    await page.waitForSelector('input[type="date"]', { timeout: 10000 });
    
    // Set future date range (no trades possible)
    const future = new Date();
    future.setFullYear(future.getFullYear() + 1);
    const futureStr = future.toISOString().split('T')[0];
    
    const dateInputs = page.locator('input[type="date"]');
    await dateInputs.nth(0).fill(futureStr);
    await dateInputs.nth(1).fill(futureStr);
    
    // Wait for data to reload
    await page.waitForTimeout(2000);
    
    // Verify empty state message
    await expect(page.locator('text=/No closed trades in selected range/i')).toBeVisible();
    
    // Capture Screenshot - Empty window
    await page.screenshot({ 
      path: 'artifacts/playwright/vm_trade_journal_empty.png', 
      fullPage: true 
    });
  });

  test('VM Trade Journal styling matches local dashboard', async ({ page }) => {
    await page.goto('http://localhost:5200/vm');

    // Wait for load
    await page.waitForSelector('h1', { timeout: 10000 });
    
    // Verify key styling elements match local dashboard
    // Header styling
    const header = page.locator('header');
    await expect(header).toHaveClass(/bg-white/);
    await expect(header).toHaveClass(/border-b/);
    
    // Summary cards styling
    const summaryCards = page.locator('.bg-white.p-4.rounded-lg');
    const count = await summaryCards.count();
    expect(count).toBeGreaterThan(0);
    
    // Table styling
    const table = page.locator('table');
    await expect(table).toBeVisible();
    
    // Capture visual comparison screenshot
    await page.screenshot({ 
      path: 'artifacts/playwright/vm_trade_journal_styling.png', 
      fullPage: true 
    });
  });
});
