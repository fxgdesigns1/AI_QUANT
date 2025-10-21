/**
 * Playwright Test - Dashboard Display Verification
 * Check if dashboards are rendering HTML properly or showing raw JSON
 */

import { test, expect } from '@playwright/test';

const TRADING_URL = 'https://ai-quant-trading.uc.r.appspot.com/dashboard';
const ANALYTICS_URL = 'https://analytics-dot-ai-quant-trading.uc.r.appspot.com';

test.describe('Dashboard Display Tests', () => {
  
  test('Trading Dashboard - Check if HTML renders', async ({ page }) => {
    console.log('🔍 Testing main trading dashboard...');
    
    await page.goto(TRADING_URL);
    await page.waitForLoadState('networkidle');
    
    // Get page content type
    const contentType = await page.evaluate(() => document.contentType);
    console.log(`Content-Type: ${contentType}`);
    
    // Check if showing JSON or HTML
    const bodyText = await page.textContent('body');
    const isJSON = bodyText?.startsWith('{') || bodyText?.startsWith('[');
    
    if (isJSON) {
      console.log('❌ Dashboard showing RAW JSON instead of HTML!');
      console.log('First 200 chars:', bodyText?.substring(0, 200));
      
      // Save screenshot
      await page.screenshot({ path: 'dashboard_raw_json.png', fullPage: true });
      console.log('📸 Screenshot saved: dashboard_raw_json.png');
      
      expect(isJSON).toBe(false);
    } else {
      console.log('✅ Dashboard rendering HTML');
      
      // Check for expected HTML elements
      const hasTitle = await page.locator('h1, h2, title').count() > 0;
      console.log(`Has title elements: ${hasTitle}`);
      
      await page.screenshot({ path: 'dashboard_html.png', fullPage: true });
      console.log('📸 Screenshot saved: dashboard_html.png');
    }
  });

  test('Analytics Dashboard - Check if HTML renders', async ({ page }) => {
    console.log('🔍 Testing analytics dashboard...');
    
    await page.goto(ANALYTICS_URL);
    await page.waitForLoadState('networkidle');
    
    // Get page content
    const bodyText = await page.textContent('body');
    const isJSON = bodyText?.startsWith('{') || bodyText?.startsWith('[');
    
    if (isJSON) {
      console.log('❌ Analytics showing RAW JSON instead of HTML!');
      console.log('First 200 chars:', bodyText?.substring(0, 200));
      
      await page.screenshot({ path: 'analytics_raw_json.png', fullPage: true });
      console.log('📸 Screenshot saved: analytics_raw_json.png');
      
      // Parse the JSON to see what it contains
      try {
        const jsonData = JSON.parse(bodyText || '{}');
        console.log('JSON structure:', Object.keys(jsonData));
      } catch (e) {
        console.log('Could not parse JSON');
      }
      
      expect(isJSON).toBe(false);
    } else {
      console.log('✅ Analytics rendering HTML');
      
      await page.screenshot({ path: 'analytics_html.png', fullPage: true });
      console.log('📸 Screenshot saved: analytics_html.png');
    }
  });

  test('Check what main dashboard actually returns', async ({ page }) => {
    const response = await page.goto(TRADING_URL);
    const headers = response?.headers();
    
    console.log('📋 Response Headers:');
    console.log('  Content-Type:', headers?.['content-type']);
    console.log('  Status:', response?.status());
    
    const body = await response?.text();
    console.log('\n📄 Response Preview (first 500 chars):');
    console.log(body?.substring(0, 500));
    
    // Determine if HTML or JSON
    if (headers?.['content-type']?.includes('application/json')) {
      console.log('❌ Server returning JSON instead of HTML!');
    } else if (headers?.['content-type']?.includes('text/html')) {
      console.log('✅ Server returning HTML (correct)');
    }
  });

  test('Check what analytics dashboard actually returns', async ({ page }) => {
    const response = await page.goto(ANALYTICS_URL);
    const headers = response?.headers();
    
    console.log('📋 Analytics Response Headers:');
    console.log('  Content-Type:', headers?.['content-type']);
    console.log('  Status:', response?.status());
    
    const body = await response?.text();
    console.log('\n📄 Response Preview (first 500 chars):');
    console.log(body?.substring(0, 500));
    
    if (headers?.['content-type']?.includes('application/json')) {
      console.log('❌ Analytics returning JSON instead of HTML!');
      
      // Show what the JSON contains
      try {
        const data = JSON.parse(body || '{}');
        console.log('JSON keys:', Object.keys(data));
      } catch (e) {}
    } else {
      console.log('✅ Analytics returning HTML (correct)');
    }
  });

});

