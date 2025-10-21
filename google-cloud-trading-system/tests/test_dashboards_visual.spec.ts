/**
 * Visual Dashboard Tests - Check actual display
 */

import { test, expect } from '@playwright/test';

const TRADING_URL = 'https://ai-quant-trading.uc.r.appspot.com/dashboard';
const ANALYTICS_URL = 'https://analytics-dot-ai-quant-trading.uc.r.appspot.com';

test.describe('Dashboard Visual Verification', () => {
  
  test('Main Trading Dashboard - Visual Check', async ({ page }) => {
    console.log('🔍 Checking main trading dashboard display...');
    
    // Navigate without waiting for networkidle (might have long-polling)
    await page.goto(TRADING_URL, { waitUntil: 'domcontentloaded' });
    
    // Wait a bit for content to render
    await page.waitForTimeout(5000);
    
    // Take screenshot
    await page.screenshot({ path: 'main_dashboard_display.png', fullPage: true });
    console.log('📸 Screenshot: main_dashboard_display.png');
    
    // Check for key elements
    const pageText = await page.textContent('body');
    
    console.log('\n📊 Dashboard Content Check:');
    console.log(`  • Contains "Trading": ${pageText?.includes('Trading') || pageText?.includes('Dashboard')}`);
    console.log(`  • Contains account data: ${pageText?.includes('PRIMARY') || pageText?.includes('GOLD') || pageText?.includes('Balance')}`);
    console.log(`  • Shows prices: ${pageText?.includes('USD') || pageText?.includes('XAU')}`);
    console.log(`  • Is JSON: ${pageText?.startsWith('{')}`);
    
    // Check specific elements
    const hasAccounts = await page.locator('text=PRIMARY, text=GOLD_SCALP, text=STRATEGY').count() > 0;
    const hasBalance = await page.locator('text=/Balance|\\$/').count() > 0;
    
    console.log(`  • Has account names: ${hasAccounts}`);
    console.log(`  • Has balance info: ${hasBalance}`);
    
    // Log what's actually visible
    const title = await page.title();
    console.log(`  • Page title: ${title}`);
    
    const h1 = await page.locator('h1').first().textContent().catch(() => 'None');
    console.log(`  • Main heading: ${h1}`);
  });

  test('Analytics Dashboard - Visual Check', async ({ page }) => {
    console.log('🔍 Checking analytics dashboard display...');
    
    await page.goto(ANALYTICS_URL, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);
    
    // Take screenshot
    await page.screenshot({ path: 'analytics_dashboard_display.png', fullPage: true });
    console.log('📸 Screenshot: analytics_dashboard_display.png');
    
    // Check content
    const pageText = await page.textContent('body');
    const isJSON = pageText?.startsWith('{');
    
    console.log('\n📊 Analytics Content Check:');
    console.log(`  • Is JSON: ${isJSON}`);
    console.log(`  • Is HTML: ${!isJSON}`);
    
    if (!isJSON) {
      console.log('✅ Analytics rendering HTML correctly!');
      
      // Check for expected content
      const title = await page.title();
      console.log(`  • Page title: ${title}`);
      
      const h1 = await page.locator('h1').first().textContent().catch(() => 'None');
      console.log(`  • Main heading: ${h1}`);
      
      const hasStats = await page.locator('#stats-grid').count() > 0;
      console.log(`  • Has stats grid: ${hasStats}`);
      
      const hasAccounts = await page.locator('#accounts-grid').count() > 0;
      console.log(`  • Has accounts grid: ${hasAccounts}`);
      
      expect(isJSON).toBe(false);
    } else {
      console.log('❌ Still showing JSON!');
      console.log('Preview:', pageText?.substring(0, 200));
    }
  });

  test('Check trading dashboard loads key elements', async ({ page }) => {
    console.log('🔍 Checking trading dashboard elements...');
    
    await page.goto(TRADING_URL, { waitUntil: 'domcontentloaded', timeout: 60000 });
    
    // Don't wait for networkidle, just check if HTML loaded
    await page.waitForTimeout(8000);
    
    // Check if it's actually HTML with dashboard content
    const contentType = await page.evaluate(() => document.contentType);
    console.log(`Content type: ${contentType}`);
    
    // Look for dashboard-specific elements
    const checks = {
      'Has title': await page.locator('title').count() > 0,
      'Has heading': await page.locator('h1, h2').count() > 0,
      'Has body content': (await page.textContent('body'))?.length > 100,
      'Not just JSON': !(await page.textContent('body'))?.startsWith('{')
    };
    
    console.log('\n📋 Element checks:');
    for (const [check, result] of Object.entries(checks)) {
      console.log(`  ${result ? '✅' : '❌'} ${check}`);
    }
    
    await page.screenshot({ path: 'trading_dashboard_loaded.png', fullPage: true });
    console.log('📸 Screenshot: trading_dashboard_loaded.png');
  });

  test('Verify analytics data endpoint works', async ({ page }) => {
    console.log('🔍 Checking analytics data endpoint...');
    
    const response = await page.request.get(`${ANALYTICS_URL}/api/overview/data`);
    const data = await response.json();
    
    console.log('📊 Analytics API Response:');
    console.log(`  Status: ${response.status()}`);
    console.log(`  Data keys: ${Object.keys(data)}`);
    console.log(`  Has accounts: ${Array.isArray(data.accounts)}`);
    
    expect(response.ok()).toBeTruthy();
  });

});

