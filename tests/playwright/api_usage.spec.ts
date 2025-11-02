import { test, expect } from "@playwright/test";

test.describe('API Usage widget (non-OANDA only)', () => {
  test('shows Marketaux and Other gauges', async ({ page }) => {
    await page.goto('http://localhost:8080/');
    // Open Dashboard tab is default; wait for API usage section to load
    const usage = page.locator('#apiUsage');
    await expect(usage).toBeVisible();

    // Force a refresh of usage (fallback if auto-refresh not yet fired)
    await page.waitForTimeout(1000);

    // Look for Marketaux and Other labels
    await expect(usage.getByText('Marketaux', { exact: false })).toBeVisible();
    await expect(usage.getByText('Other APIs', { exact: false })).toBeVisible();

    // Ensure OANDA label is NOT present (we hid it)
    await expect(usage.getByText('OANDA', { exact: false })).toHaveCount(0);
  });
});
