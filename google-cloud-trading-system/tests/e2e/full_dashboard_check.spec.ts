import { test, expect } from '@playwright/test';

test.describe('Full Dashboard Check', () => {
  test('should check dashboard and identify data flow issues', async ({ page }) => {
    const consoleLogs = [];
    const consoleErrors = [];
    const networkRequests = [];
    
    // Listen to all console messages
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    // Listen to network requests
    page.on('request', request => {
      if (request.url().includes('/api/')) {
        networkRequests.push({
          url: request.url(),
          method: request.method(),
          status: 'pending'
        });
      }
    });
    
    page.on('response', response => {
      if (response.url().includes('/api/')) {
        const request = networkRequests.find(req => req.url === response.url());
        if (request) {
          request.status = response.status();
        }
      }
    });
    
    // Navigate to dashboard
    console.log('🌐 Navigating to dashboard...');
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    
    console.log('📄 Page loaded, checking initial state...');
    
    // Take screenshot of initial state
    await page.screenshot({ path: 'test-results/initial-dashboard.png', fullPage: true });
    
    // Check what's currently displayed
    const accountStatus = await page.locator('#account-status').textContent();
    const signalsContent = await page.locator('#signals-feed').textContent();
    const livePrices = await page.locator('#live-prices').textContent();
    const performance = await page.locator('#performance-metrics').textContent();
    
    console.log('📊 Initial Dashboard State:');
    console.log('Account Status:', accountStatus);
    console.log('Signals Content:', signalsContent);
    console.log('Live Prices:', livePrices);
    console.log('Performance:', performance);
    
    // Wait for JavaScript to potentially load
    console.log('⏳ Waiting for JavaScript execution...');
    await page.waitForTimeout(10000);
    
    // Check state after waiting
    const accountStatusAfter = await page.locator('#account-status').textContent();
    const signalsAfter = await page.locator('#signals-feed').textContent();
    const pricesAfter = await page.locator('#live-prices').textContent();
    const performanceAfter = await page.locator('#performance-metrics').textContent();
    
    console.log('📊 After 10 seconds:');
    console.log('Account Status:', accountStatusAfter);
    console.log('Signals Content:', signalsAfter);
    console.log('Live Prices:', pricesAfter);
    console.log('Performance:', performanceAfter);
    
    // Check console logs and errors
    console.log('🔍 Console Logs:', consoleLogs);
    console.log('❌ Console Errors:', consoleErrors);
    console.log('🌐 Network Requests:', networkRequests);
    
    // Test API endpoints directly
    console.log('🧪 Testing API endpoints directly...');
    
    const accountsResponse = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/accounts');
    console.log('Accounts API Status:', accountsResponse.status());
    const accountsData = await accountsResponse.json();
    console.log('Accounts Data Available:', Object.keys(accountsData.accounts || {}).length, 'accounts');
    
    const pricesResponse = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/prices');
    console.log('Prices API Status:', pricesResponse.status());
    const pricesData = await pricesResponse.json();
    console.log('Prices Data Available:', Object.keys(pricesData.prices || {}).length, 'pairs');
    
    // Try to manually trigger the functions
    console.log('🔧 Attempting to manually trigger functions...');
    
    const manualResult = await page.evaluate(() => {
      try {
        // Check if functions exist
        const functionsExist = {
          loadAccountStatus: typeof loadAccountStatus,
          loadSignals: typeof loadSignals,
          loadLivePrices: typeof loadLivePrices,
          loadPerformanceMetrics: typeof loadPerformanceMetrics,
          updateStatus: typeof updateStatus,
          startRealTimeUpdates: typeof startRealTimeUpdates
        };
        
        console.log('Functions exist:', functionsExist);
        
        // Try to call functions if they exist
        if (typeof loadAccountStatus === 'function') {
          loadAccountStatus();
          console.log('Called loadAccountStatus');
        }
        if (typeof loadLivePrices === 'function') {
          loadLivePrices();
          console.log('Called loadLivePrices');
        }
        
        return { success: true, functionsExist };
      } catch (error) {
        return { success: false, error: error.message };
      }
    });
    
    console.log('🔧 Manual function call result:', manualResult);
    
    // Wait a bit more and check final state
    await page.waitForTimeout(5000);
    
    const finalAccountStatus = await page.locator('#account-status').textContent();
    const finalPrices = await page.locator('#live-prices').textContent();
    
    console.log('📊 Final State:');
    console.log('Final Account Status:', finalAccountStatus);
    console.log('Final Prices:', finalPrices);
    
    // Take final screenshot
    await page.screenshot({ path: 'test-results/final-dashboard.png', fullPage: true });
    
    // Summary
    console.log('📋 SUMMARY:');
    console.log('- API endpoints working:', accountsResponse.status() === 200 && pricesResponse.status() === 200);
    console.log('- Data available:', Object.keys(accountsData.accounts || {}).length > 0);
    console.log('- Still showing loading:', finalAccountStatus?.includes('Loading'));
    console.log('- JavaScript errors:', consoleErrors.length);
    console.log('- Network requests made:', networkRequests.length);
  });
});

