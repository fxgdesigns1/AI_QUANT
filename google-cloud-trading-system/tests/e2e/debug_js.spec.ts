import { test, expect } from '@playwright/test';

test.describe('JavaScript Debug', () => {
  test('should check JavaScript console for errors', async ({ page }) => {
    const consoleLogs = [];
    const consoleErrors = [];
    
    // Listen to all console messages
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Listen to page errors
    page.on('pageerror', error => {
      consoleErrors.push(`Page Error: ${error.message}`);
    });
    
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    // Wait for JavaScript to execute
    await page.waitForTimeout(10000);
    
    console.log('All Console Logs:', consoleLogs);
    console.log('Console Errors:', consoleErrors);
    
    // Check if there are JavaScript errors
    if (consoleErrors.length > 0) {
      console.log('JavaScript Errors Found:', consoleErrors);
    }
    
    // Try to manually call the JavaScript functions
    const result = await page.evaluate(() => {
      try {
        // Check if functions exist
        const functions = {
          loadAccountStatus: typeof loadAccountStatus,
          loadSignals: typeof loadSignals,
          loadLivePrices: typeof loadLivePrices,
          loadPerformanceMetrics: typeof loadPerformanceMetrics
        };
        
        // Try to call one function
        if (typeof loadAccountStatus === 'function') {
          loadAccountStatus();
          return { success: true, functions, message: 'Function called successfully' };
        } else {
          return { success: false, functions, message: 'Functions not found' };
        }
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('JavaScript Evaluation Result:', result);
  });
});

