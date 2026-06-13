// Playwright tests for dashboard
// Can run against mock API or live VM

const { test, expect } = require('@playwright/test');

const BASE_URL = process.env.DASHBOARD_URL || 'http://127.0.0.1:28787';

test.describe('Dashboard Basic Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    // Wait for page to load
    await page.waitForLoadState('networkidle');
  });

  test('should load dashboard home page', async ({ page }) => {
    await expect(page).toHaveTitle(/AI_QUANT|Control Plane/i);
  });

  test('should display system status', async ({ page }) => {
    // Check for status indicators or API calls
    const statusResponse = await page.waitForResponse(response => 
      response.url().includes('/api/status') || response.url().includes('/api/truth/status')
    );
    expect(statusResponse.ok()).toBeTruthy();
    
    const statusData = await statusResponse.json();
    expect(statusData).toHaveProperty('data');
  });

  test('should load market overview', async ({ page }) => {
    const marketResponse = await page.waitForResponse(response => 
      response.url().includes('/api/market/overview')
    );
    expect(marketResponse.ok()).toBeTruthy();
    
    const marketData = await marketResponse.json();
    expect(marketData).toHaveProperty('data');
  });

  test('should display active trades', async ({ page }) => {
    const tradesResponse = await page.waitForResponse(response => 
      response.url().includes('/api/trades/active')
    );
    expect(tradesResponse.ok()).toBeTruthy();
    
    const tradesData = await tradesResponse.json();
    expect(tradesData).toHaveProperty('data');
  });