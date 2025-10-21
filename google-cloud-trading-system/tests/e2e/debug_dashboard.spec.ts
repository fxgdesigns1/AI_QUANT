import { test, expect } from '@playwright/test';

test.describe('Dashboard Live Data Debug', () => {
  test('should load dashboard and check API endpoints', async ({ page }) => {
    // Navigate to the dashboard
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Check if dashboard loads
    await expect(page.locator('h1')).toContainText('Enhanced Trading System Dashboard');
    
    // Test API endpoints directly
    console.log('Testing API endpoints...');
    
    // Test accounts endpoint
    const accountsResponse = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/accounts');
    console.log('Accounts API Status:', accountsResponse.status());
    const accountsData = await accountsResponse.json();
    console.log('Accounts Data:', JSON.stringify(accountsData, null, 2));
    
    // Test prices endpoint
    const pricesResponse = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/prices');
    console.log('Prices API Status:', pricesResponse.status());
    const pricesData = await pricesResponse.json();
    console.log('Prices Data:', JSON.stringify(pricesData, null, 2));
    
    // Test signals endpoint
    const signalsResponse = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/signals');
    console.log('Signals API Status:', signalsResponse.status());
    const signalsData = await signalsResponse.json();
    console.log('Signals Data:', JSON.stringify(signalsData, null, 2));
    
    // Test performance endpoint
    const performanceResponse = await page.request.get('https://ai-quant-trading.uc.r.appspot.com/api/performance');
    console.log('Performance API Status:', performanceResponse.status());
    const performanceData = await performanceResponse.json();
    console.log('Performance Data:', JSON.stringify(performanceData, null, 2));
    
    // Check if loading messages are still showing
    const accountLoading = page.locator('#account-status').textContent();
    const signalsLoading = page.locator('#signals-feed').textContent();
    
    console.log('Account Status Content:', await accountLoading);
    console.log('Signals Content:', await signalsLoading);
    
    // Wait a bit for JavaScript to load data
    await page.waitForTimeout(10000);
    
    // Check if data has loaded
    const accountStatusAfter = await page.locator('#account-status').textContent();
    const signalsAfter = await page.locator('#signals-feed').textContent();
    
    console.log('Account Status After Wait:', accountStatusAfter);
    console.log('Signals After Wait:', signalsAfter);
    
    // Check browser console for errors
    const consoleLogs = [];
    page.on('console', msg => {
      consoleLogs.push(`[${msg.type()}] ${msg.text()}`);
    });
    
    await page.waitForTimeout(5000);
    
    console.log('Browser Console Logs:', consoleLogs);
  });
  
  test('should check JavaScript errors and network requests', async ({ page }) => {
    const networkRequests = [];
    const consoleErrors = [];
    
    // Listen to network requests
    page.on('request', request => {
      networkRequests.push({
        url: request.url(),
        method: request.method(),
        status: 'pending'
      });
    });
    
    page.on('response', response => {
      const request = networkRequests.find(req => req.url === response.url());
      if (request) {
        request.status = response.status();
      }
    });
    
    // Listen to console errors
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.goto('https://ai-quant-trading.uc.r.appspot.com/');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(10000);
    
    console.log('Network Requests:', networkRequests);
    console.log('Console Errors:', consoleErrors);
    
    // Check if any API calls failed
    const failedRequests = networkRequests.filter(req => req.status >= 400);
    if (failedRequests.length > 0) {
      console.log('Failed Requests:', failedRequests);
    }
  });
});

