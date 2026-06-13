import { test, expect } from '@playwright/test';

// Local dashboard URL
const DASHBOARD_URL = 'http://127.0.0.1:5173';

test.describe('Local OANDA Dashboard', () => {
  
  test.beforeEach(async ({ page }) => {
    // Navigate to dashboard before each test
    await page.goto(DASHBOARD_URL);
    // Wait for loading to finish
    await expect(page.getByText('Loading...')).not.toBeVisible({ timeout: 10000 });
    
    // Check for error state
    const errorMsg = page.locator('text=Error:');
    if (await errorMsg.isVisible()) {
      console.log('Dashboard reported error:', await errorMsg.textContent());
    }
  });

  test('should load dashboard title', async ({ page }) => {
    // Check h1 instead of document title as index.html title might be static
    await expect(page.getByRole('heading', { name: 'Local OANDA Trade Dashboard' })).toBeVisible();
  });

  test('should display statistics cards', async ({ page }) => {
    // Check for presence of main stat cards
    // Use first=true or specific matching to avoid ambiguity if multiple elements match
    await expect(page.locator('text=Win Rate').first()).toBeVisible();
    await expect(page.locator('text=Total P&L').first()).toBeVisible();
    await expect(page.locator('text=Total Trades').first()).toBeVisible();
  });

  test('should handle zero trades gracefully', async ({ page }) => {
    // Based on current state (0 trades), we expect:
    // 1. Closed Trades should be "0"
    const closedTradesCard = page.locator('div').filter({ hasText: /^Total Trades$/ }).locator('..');
    await expect(closedTradesCard).toContainText('0');

    // 2. Win Rate should be "N/A"
    const winRateCard = page.locator('div').filter({ hasText: /^Win Rate$/ }).locator('..');
    await expect(winRateCard).toContainText('N/A');
  });

  test('should display data confidence indicator', async ({ page }) => {
    // If confidence is HIGH (current state), no warning banner should be visible
    const warningBanner = page.locator('text=Data Incomplete');
    await expect(warningBanner).not.toBeVisible();
  });

  test('should display trade journal table', async ({ page }) => {
    await expect(page.getByRole('heading', { name: 'Trade Journal' })).toBeVisible();
    // Table headers should be visible - be specific to avoid ambiguity
    await expect(page.getByRole('columnheader', { name: 'Entry Time' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'Instrument' })).toBeVisible();
    await expect(page.getByRole('columnheader', { name: 'P&L' })).toBeVisible();
    
    // With 0 trades, we expect "No trades found" message
    await expect(page.getByText('No trades found')).toBeVisible();
  });

  test('should have correct styling applied', async ({ page }) => {
    // Check if Tailwind classes are applied effectively
    // The dashboard title has "text-3xl font-bold mb-6"
    const title = page.getByRole('heading', { name: 'Local OANDA Trade Dashboard' });
    
    // Check for font-weight: 700 (bold)
    await expect(title).toHaveCSS('font-weight', '700');
    
    // Check for font-size (text-3xl is usually 30px / 1.875rem)
    await expect(title).toHaveCSS('font-size', '30px');
    
    // Check that the grid layout is active (grid grid-cols-1 md:grid-cols-4)
    // We can check if the filter container has display: grid
    const filterContainer = page.locator('.grid').first();
    await expect(filterContainer).toHaveCSS('display', 'grid');
  });

});
