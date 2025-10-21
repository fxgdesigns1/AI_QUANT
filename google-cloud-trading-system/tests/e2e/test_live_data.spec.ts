import { test, expect } from '@playwright/test';

test.describe('Live Data Display Test', () => {
  test('should display live OANDA data on dashboard', async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Wait for JavaScript to load data (up to 15 seconds)
    await page.waitForTimeout(15000);
    
    // Check if account data is loaded (not showing loading message)
    const accountStatus = await page.locator('#account-status').textContent();
    console.log('Account Status:', accountStatus);
    
    // Should not contain loading message
    expect(accountStatus).not.toContain('Loading live account data');
    
    // Check if signals are loaded
    const signalsContent = await page.locator('#signals-feed').textContent();
    console.log('Signals Content:', signalsContent);
    
    // Should not contain loading message
    expect(signalsContent).not.toContain('Loading live trading signals');
    
    // Check if live prices are loaded
    const livePrices = await page.locator('#live-prices').textContent();
    console.log('Live Prices:', livePrices);
    
    // Should not contain loading message
    expect(livePrices).not.toContain('Loading live market prices');
    
    // Check if performance metrics are loaded
    const performance = await page.locator('#performance-metrics').textContent();
    console.log('Performance:', performance);
    
    // Should not contain loading message
    expect(performance).not.toContain('Loading live performance data');
    
    // Verify we have actual data
    expect(accountStatus).toContain('101-004-30719775'); // Account ID should be visible
    expect(signalsContent).toContain('EUR_USD'); // Should show trading signals
    expect(livePrices).toContain('EUR_USD'); // Should show live prices
    expect(performance).toContain('Total P&L'); // Should show performance metrics
  });
  
  test('should show real-time data updates', async ({ page }) => {
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    // Wait for initial data load
    await page.waitForTimeout(10000);
    
    // Get initial data
    const initialPrices = await page.locator('#live-prices').textContent();
    console.log('Initial Prices:', initialPrices);
    
    // Wait for next update cycle (5 seconds)
    await page.waitForTimeout(6000);
    
    // Get updated data
    const updatedPrices = await page.locator('#live-prices').textContent();
    console.log('Updated Prices:', updatedPrices);
    
    // Data should be present (not loading messages)
    expect(updatedPrices).not.toContain('Loading live market prices');
    expect(updatedPrices).toContain('EUR_USD');
  });
});

