import { test, expect } from '@playwright/test';

test.describe('Simple JavaScript Test', () => {
  test('should test basic JavaScript execution', async ({ page }) => {
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    // Test if we can execute basic JavaScript
    const basicTest = await page.evaluate(() => {
      try {
        // Test basic JavaScript
        const testVar = 'Hello World';
        console.log('Basic JS works:', testVar);
        
        // Test if we can access DOM elements
        const accountStatus = document.getElementById('account-status');
        console.log('Account status element:', accountStatus ? 'found' : 'not found');
        
        // Test if we can make a simple API call
        return { success: true, testVar, accountStatusFound: !!accountStatus };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('Basic JavaScript test:', basicTest);
    
    // Test if we can manually call the API and update the DOM
    const manualUpdate = await page.evaluate(async () => {
      try {
        // Make API call
        const response = await fetch('/api/accounts');
        const data = await response.json();
        console.log('API call successful:', Object.keys(data.accounts || {}).length, 'accounts');
        
        // Update DOM manually
        const container = document.getElementById('account-status');
        if (container && data.accounts) {
          container.innerHTML = '<div style="color: green;">✅ Manual update successful - ' + Object.keys(data.accounts).length + ' accounts loaded</div>';
          return { success: true, accountsCount: Object.keys(data.accounts).length };
        } else {
          return { success: false, error: 'Container not found or no data' };
        }
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('Manual update test:', manualUpdate);
    
    // Check if the manual update worked
    const accountStatus = await page.locator('#account-status').textContent();
    console.log('Account status after manual update:', accountStatus);
    
    // Should show the manual update message
    expect(accountStatus).toContain('Manual update successful');
  });
});

