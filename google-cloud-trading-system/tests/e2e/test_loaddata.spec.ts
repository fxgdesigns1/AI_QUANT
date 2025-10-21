import { test, expect } from '@playwright/test';

test.describe('Test loadData Function', () => {
  test('should test if loadData function exists and works', async ({ page }) => {
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    // Wait for the setTimeout to execute
    await page.waitForTimeout(5000);
    
    // Check if loadData function exists
    const functionTest = await page.evaluate(() => {
      try {
        // Check if loadData function exists
        const loadDataExists = typeof loadData;
        console.log('loadData function type:', loadDataExists);
        
        // Try to call it manually
        if (typeof loadData === 'function') {
          loadData();
          console.log('loadData called successfully');
          return { success: true, loadDataExists, message: 'Function called' };
        } else {
          return { success: false, loadDataExists, message: 'Function not found' };
        }
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('Function test result:', functionTest);
    
    // Check if data was loaded
    const accountStatus = await page.locator('#account-status').textContent();
    const livePrices = await page.locator('#live-prices').textContent();
    
    console.log('Account Status:', accountStatus);
    console.log('Live Prices:', livePrices);
    
    // Check console logs
    const consoleLogs = [];
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    });
    
    await page.waitForTimeout(2000);
    console.log('Console logs:', consoleLogs);
  });
});

