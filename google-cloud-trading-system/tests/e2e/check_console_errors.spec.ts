import { test, expect } from '@playwright/test';

test.describe('Check Console Errors', () => {
  test('should check for JavaScript console errors', async ({ page }) => {
    const consoleLogs = [];
    const consoleErrors = [];
    const pageErrors = [];
    
    // Listen to all console messages
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Listen to page errors
    page.on('pageerror', error => {
      pageErrors.push(error.message);
    });
    
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    // Wait for any JavaScript to execute
    await page.waitForTimeout(10000);
    
    console.log('Console Logs:', consoleLogs);
    console.log('Console Errors:', consoleErrors);
    console.log('Page Errors:', pageErrors);
    
    // Check if there are any errors
    if (consoleErrors.length > 0 || pageErrors.length > 0) {
      console.log('❌ JavaScript errors found!');
      console.log('Console Errors:', consoleErrors);
      console.log('Page Errors:', pageErrors);
    } else {
      console.log('✅ No JavaScript errors found');
    }
    
    // Try to evaluate a simple script to see if JavaScript works at all
    const simpleTest = await page.evaluate(() => {
      try {
        const testVar = 'Hello';
        console.log('Simple JS test:', testVar);
        return { success: true, testVar };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('Simple JS test result:', simpleTest);
  });
});

